package main

import (
	"context"
	"encoding/json"
	"log"
	"math"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"github.com/IBM/sarama"
	"github.com/joho/godotenv"
	"github.com/sohamratnaparkhi/cortex-cache-ai-backend/consumer/src"
	"github.com/sohamratnaparkhi/cortex-cache-ai-backend/consumer/src/types"
)

const (
	FailedQueue       = "failed-queue"
	HighPriorityQueue = "high-priority-queue"
	LowPriorityQueue  = "low-priority-queue"
)

func handleMessages(message *sarama.ConsumerMessage) {
	task := types.Task{}
	err := json.Unmarshal(message.Value, &task)
	if err != nil {
		log.Printf("Failed to unmarshal task: %s", err)
		return
	}
	resp, newTask, apiKey, err := src.ProcessMessage(task, message)
	if err != nil {
		log.Printf("Failed to process message: %s", err)
		return
	}
	defer resp.Body.Close()

	// TODO: handle request failure by exponential backoff
	if resp.StatusCode != http.StatusOK {
		log.Printf("Request failed with status code: %d", resp.StatusCode)

		handleRequestFailure(message, newTask, apiKey)

		return
	}
}

func handleRequestFailure(message *sarama.ConsumerMessage, task types.Task, apiKey string) {
	if task.Retries > 3 {
		log.Printf("Task failed after 3 retries")
		err := produceToFailedQueue(task, apiKey)
		if err != nil {
			log.Printf("Failed to produce message to failed queue: %s", err)
		} else {
			log.Printf("Task sent to failed queue")
		}
		return
	}
	backOffTime := math.Pow(2, float64(task.Retries)) * 1000
	time.Sleep(time.Duration(backOffTime) * time.Millisecond)
	resp, newTask, apiKey, err := src.ProcessMessage(task, message)
	if err != nil {
		log.Printf("Failed to process message: %s", err)
		return
	}
	defer resp.Body.Close()

	// TODO: handle request failure by exponential backoff
	if resp.StatusCode != http.StatusOK {
		log.Printf("Request failed with status code: %d", resp.StatusCode)
		handleRequestFailure(message, newTask, apiKey)
		return
	}
}

func produceToFailedQueue(task types.Task, apiKey string) error {
	config := sarama.NewConfig()
	config.Producer.Return.Successes = true

	producer, err := sarama.NewSyncProducer(strings.Split(os.Getenv("KAFKA_BROKERS"), ","), config)
	if err != nil {
		return err
	}
	defer producer.Close()

	taskJSON, err := json.Marshal(task)
	if err != nil {
		return err
	}

	msg := &sarama.ProducerMessage{
		Topic: FailedQueue,
		Value: sarama.StringEncoder(taskJSON),
		Headers: []sarama.RecordHeader{
			{
				Key:   []byte("x-api-key"),
				Value: []byte(apiKey),
			},
		},
	}

	_, _, err = producer.SendMessage(msg)
	return err
}

func main() {
	err := godotenv.Load()
	if err != nil {
		log.Fatalf("Failed to load .env file: %s", err)
	}

	brokers := strings.Split(os.Getenv("KAFKA_BROKERS"), ",")
	if len(brokers) == 0 {
		log.Fatalf("KAFKA_BROKERS is not set or empty")
	}

	config := sarama.NewConfig()
	config.Consumer.Return.Errors = true
	config.Consumer.Offsets.Initial = sarama.OffsetNewest

	consumer, err := sarama.NewConsumerGroup(brokers, "cortex-cache-consumer-group", config)
	if err != nil {
		log.Fatalf("Failed to create consumer group: %s", err)
	}
	defer consumer.Close()

	topics := []string{HighPriorityQueue, LowPriorityQueue}

	// Start a goroutine to handle consumer group sessions
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	go func() {
		for {
			if err := consumer.Consume(ctx, topics, &ConsumerGroupHandler{}); err != nil {
				log.Printf("Error from consumer: %v", err)
			}
			if ctx.Err() != nil {
				return
			}
		}
	}()

	log.Println("Kafka consumer started. Waiting for messages...")

	// Handle graceful shutdown
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
	<-sigChan

	log.Println("Received termination signal. Closing consumer...")
}

// ConsumerGroupHandler represents the consumer group handler
type ConsumerGroupHandler struct{}

// Setup is run at the beginning of a new session, before ConsumeClaim
func (ConsumerGroupHandler) Setup(_ sarama.ConsumerGroupSession) error { return nil }

// Cleanup is run at the end of a session, once all ConsumeClaim goroutines have exited
func (ConsumerGroupHandler) Cleanup(_ sarama.ConsumerGroupSession) error { return nil }

// ConsumeClaim is run for each consumer in the group
func (h ConsumerGroupHandler) ConsumeClaim(sess sarama.ConsumerGroupSession, claim sarama.ConsumerGroupClaim) error {
	for msg := range claim.Messages() {
		log.Printf("Message received from topic %s", msg.Topic)
		handleMessages(msg)
		sess.MarkMessage(msg, "")
	}
	return nil
}
