package main

import (
	"context"
	"database/sql"
	"encoding/json"
	"log"
	"math"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/go-redis/redis/v8"
	"github.com/joho/godotenv"
	"github.com/sohamratnaparkhi/cortex-cache-ai-backend/consumer/src"
	"github.com/sohamratnaparkhi/cortex-cache-ai-backend/consumer/src/types"
)

const (
	FailedQueue       = "failed:queue"
	HighPriorityQueue = "high:priority:queue"
	LowPriorityQueue  = "low:priority:queue"
	EmailQueue        = "email:queue"
)

type RedisMessage struct {
	Task   types.Task `json:"task"`
	APIKey string     `json:"api_key"`
}

func initRedisClient() (*redis.Client, error) {
	redisAddr := os.Getenv("REDIS_ADDR")
	if redisAddr == "" {
		redisAddr = "localhost:6379"
	}

	opt, _ := redis.ParseURL(redisAddr)
	rdb := redis.NewClient(opt)

	ctx := context.Background()
	_, err := rdb.Ping(ctx).Result()
	if err != nil {
		return nil, err
	}

	return rdb, nil
}

func handleEmailMessage(ctx context.Context, rdb *redis.Client, message string) {
	var emailMsg types.EmailMessage
	err := json.Unmarshal([]byte(message), &emailMsg)
	if err != nil {
		log.Printf("Failed to unmarshal email message: %s", err)
		return
	}

	err = src.SendEmail(emailMsg)
	if err != nil {
		log.Printf("Failed to send email: %s", err)
		// Push to failed queue with retry logic
		retryEmailSend(ctx, rdb, emailMsg, 0)
		return
	}

	log.Printf("Successfully sent email to %s", emailMsg.To)
}

func retryEmailSend(ctx context.Context, rdb *redis.Client, msg types.EmailMessage, retryCount int) {
	if retryCount >= 3 {
		// After 3 retries, move to failed queue
		jsonData, _ := json.Marshal(msg)
		err := rdb.LPush(ctx, FailedQueue, jsonData).Err()
		if err != nil {
			log.Printf("Failed to push failed email to failed queue: %s", err)
		}
		return
	}

	// Exponential backoff
	backOffTime := math.Pow(2, float64(retryCount)) * 1000
	time.Sleep(time.Duration(backOffTime) * time.Millisecond)

	err := src.SendEmail(msg)
	if err != nil {
		log.Printf("Retry %d failed: %s", retryCount+1, err)
		retryEmailSend(ctx, rdb, msg, retryCount+1)
		return
	}

	log.Printf("Successfully sent email to %s after %d retries", msg.To, retryCount+1)
}

func handleMessage(ctx context.Context, rdb *redis.Client, queue string, message string, db *sql.DB) {
	var redisMsg RedisMessage
	err := json.Unmarshal([]byte(message), &redisMsg)
	if err != nil {
		log.Printf("Failed to unmarshal message: %s", err)
		return
	}

	resp, newTask, _, err := src.ProcessMessage(redisMsg.Task, redisMsg.APIKey, db)
	if err != nil {
		log.Printf("Failed to process message: %s", err)
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		log.Printf("Request failed with status code: %d", resp.StatusCode)
		handleRequestFailure(ctx, rdb, redisMsg, newTask, db)
		return
	}
}

func handleRequestFailure(ctx context.Context, rdb *redis.Client, msg RedisMessage, task types.Task, db *sql.DB) {
	if task.Retries > 3 {
		log.Printf("Task failed after 3 retries")
		err := pushToFailedQueue(ctx, rdb, msg)
		if err != nil {
			log.Printf("Failed to push message to failed queue: %s", err)
		} else {
			log.Printf("Task sent to failed queue")
		}
		return
	}

	backOffTime := math.Pow(2, float64(task.Retries)) * 1000
	time.Sleep(time.Duration(backOffTime) * time.Millisecond)

	resp, newTask, _, err := src.ProcessMessage(task, msg.APIKey, db)
	if err != nil {
		log.Printf("Failed to process message: %s", err)
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		log.Printf("Request failed with status code: %d", resp.StatusCode)
		msg.Task = newTask
		handleRequestFailure(ctx, rdb, msg, newTask, db)
		return
	}
}

func pushToFailedQueue(ctx context.Context, rdb *redis.Client, msg RedisMessage) error {
	jsonData, err := json.Marshal(msg)
	if err != nil {
		return err
	}

	return rdb.LPush(ctx, FailedQueue, jsonData).Err()
}

func processQueue(ctx context.Context, rdb *redis.Client, db *sql.DB, queue string) {
	for {
		select {
		case <-ctx.Done():
			return
		default:
			// Use BRPOP to block and wait for messages
			result, err := rdb.BRPop(ctx, 0, queue).Result()
			if err != nil {
				if err != redis.Nil && err != context.Canceled {
					log.Printf("Error reading from queue %s: %v", queue, err)
					time.Sleep(time.Second) // Wait before retrying
				}
				continue
			}

			// result[0] is the queue name, result[1] is the message
			handleMessage(ctx, rdb, queue, result[1], db)
		}
	}
}

func main() {
	err := godotenv.Load()
	if err != nil {
		log.Printf("Failed to load .env file: %s", err)
	}

	err = src.InitEmailDialer()
	if err != nil {
		log.Fatalf("Failed to initialize email dialer: %s", err)
	}

	db, err := src.InitDB()
	if err != nil {
		log.Fatalf("Failed to initialize database: %s", err)
	}

	rdb, err := initRedisClient()

	if err != nil {
		log.Fatalf("Failed to initialize Redis client: %s", err)
	}
	defer rdb.Close()

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// Start goroutines for each queue
	go processQueue(ctx, rdb, db, HighPriorityQueue)
	go processQueue(ctx, rdb, db, LowPriorityQueue)
	go processEmailQueue(ctx, rdb)

	log.Println("Redis consumer started. Waiting for messages...")

	// Handle graceful shutdown
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
	<-sigChan

	log.Println("Received termination signal. Shutting down...")
	cancel()
	time.Sleep(time.Second) // Give goroutines time to clean up
}

func processEmailQueue(ctx context.Context, rdb *redis.Client) {
	for {
		select {
		case <-ctx.Done():
			return
		default:
			result, err := rdb.BRPop(ctx, 0, EmailQueue).Result()
			if err != nil {
				if err != redis.Nil && err != context.Canceled {
					log.Printf("Error reading from email queue: %v", err)
					time.Sleep(time.Second)
				}
				continue
			}

			handleEmailMessage(ctx, rdb, result[1])
		}
	}
}
