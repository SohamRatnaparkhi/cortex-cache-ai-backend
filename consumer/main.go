package main

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"math"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gin-gonic/gin"
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

type StatusResponse struct {
	Status    string `json:"status"`
	Redis     string `json:"redis"`
	Database  string `json:"database"`
	Timestamp string `json:"timestamp"`
	Uptime    string `json:"uptime"`
}

var (
	startTime time.Time
	rdb       *redis.Client
	db        *sql.DB
)

func statusHandler(c *gin.Context) {
	status := StatusResponse{
		Status:    "healthy",
		Timestamp: time.Now().UTC().Format(time.RFC3339),
		Uptime:    time.Since(startTime).Round(time.Second).String(),
	}

	// Check Redis connection
	if _, err := rdb.Ping(c).Result(); err != nil {
		status.Status = "degraded"
		status.Redis = "unavailable"
	} else {
		status.Redis = "connected"
	}

	// Check Database connection
	if err := db.PingContext(c); err != nil {
		status.Status = "degraded"
		status.Database = "unavailable"
	} else {
		status.Database = "connected"
	}

	if status.Status != "healthy" {
		c.JSON(http.StatusServiceUnavailable, status)
		return
	}

	c.JSON(http.StatusOK, status)
}

func setupRouter() *gin.Engine {
	// Set Gin to release mode in production
	if os.Getenv("GIN_MODE") != "debug" {
		gin.SetMode(gin.ReleaseMode)
	}

	r := gin.Default()

	// Add basic middleware
	r.Use(gin.Recovery())
	r.Use(gin.Logger())

	// Health check endpoint
	r.GET("/health", statusHandler)

	return r
}

func startHTTPServer(ctx context.Context) *http.Server {
	router := setupRouter()

	// check if .env file exists
	_, err := os.Stat(".env")

	if err == nil || os.IsNotExist(err) {
		_ = godotenv.Load()
	}

	PORT := os.Getenv("PORT")
	if PORT == "" {
		PORT = "8080"
	}

	server := &http.Server{
		Addr:    ":" + PORT,
		Handler: router,
	}

	go func() {
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Printf("HTTP server error: %v", err)
		}
	}()

	return server
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
	// Create a worker pool
	workers := 4 // number of parallel workers
	sem := make(chan struct{}, workers)

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
					time.Sleep(time.Second)
				}
				continue
			}

			// Acquire semaphore
			sem <- struct{}{}

			// Process message in goroutine
			go func(message string) {
				defer func() { <-sem }() // Release semaphore when done
				handleMessage(ctx, rdb, queue, message, db)
			}(result[1])
		}
	}
}

func main() {
	startTime = time.Now()

	_, err := os.Stat(".env")
	fmt.Print(err)
	if err == nil || os.IsNotExist(err) {
		fmt.Print("Loading env")
		_ = godotenv.Load()
	}

	err = src.InitEmailDialer()
	if err != nil {
		log.Fatalf("Failed to initialize email dialer: %s", err)
	}

	db, err = src.InitDB()
	if err != nil {
		log.Fatalf("Failed to initialize database: %s", err)
	}

	rdb, err = initRedisClient()
	if err != nil {
		log.Fatalf("Failed to initialize Redis client: %s", err)
	}
	defer rdb.Close()

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// Start HTTP server
	server := startHTTPServer(ctx)

	// Start queue processing goroutines
	go processQueue(ctx, rdb, db, HighPriorityQueue)
	go processQueue(ctx, rdb, db, LowPriorityQueue)
	go processEmailQueue(ctx, rdb)

	log.Printf("Redis consumer started. HTTP server listening on %s", server.Addr)

	// Handle graceful shutdown
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
	<-sigChan

	log.Println("Received termination signal. Shutting down...")

	// Shutdown HTTP server
	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer shutdownCancel()

	if err := server.Shutdown(shutdownCtx); err != nil {
		log.Printf("HTTP server shutdown error: %v", err)
	}

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
