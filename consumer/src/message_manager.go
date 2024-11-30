package src

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"time"

	"github.com/IBM/sarama"
	"github.com/golang-jwt/jwt/v5"
	"github.com/joho/godotenv"
	_ "github.com/lib/pq"
	"github.com/sohamratnaparkhi/cortex-cache-ai-backend/consumer/src/types"
)

const BASE = "/api/v1"

var ENDPOINT_MAP = map[string]string{
	"git":     BASE + "/link/process/git",
	"youtube": BASE + "/link/process/youtube",
	"web":     BASE + "/link/process/web",
	"file":    BASE + "/file/process/pdf",
	"audio":   BASE + "/file/process/audio",
	"video":   BASE + "/file/process/video",
	"image":   BASE + "/file/process/image",
}

var FAST_API_SERVER = ""

func GetApikeyFromHeaders(message *sarama.ConsumerMessage) (string, error) {
	tknStr := ""
	for _, header := range message.Headers {
		if string(header.Key) == "x-api-key" {
			tknStr = string(header.Value)
			break
		}
	}
	err := godotenv.Load()
	if err != nil {
		log.Fatalf("Failed to load .env file: %s", err)
	}

	fastApiServer := os.Getenv("FAST_API_SERVER")
	if fastApiServer == "" {
		log.Fatalf("FAST_API_SERVER is not set")
	}
	FAST_API_SERVER = fastApiServer
	jwtSecretKey := os.Getenv("JWT_SECRET_KEY")
	if jwtSecretKey == "" {
		log.Fatalf("JWT_SECRET_KEY is not set")
	}
	claims := &types.Claims{}

	tkn, err := jwt.ParseWithClaims(tknStr, claims, func(token *jwt.Token) (interface{}, error) {
		return []byte(jwtSecretKey), nil
	})
	if err != nil {
		if err == jwt.ErrSignatureInvalid {
			return "", err
		}

		return "", err
	}
	if !tkn.Valid {
		return "", err
	}

	return claims.APIKey, nil

}

func MakeRequest(endpoint string, data []byte, apiKey string) (*http.Response, error) {
	err := godotenv.Load()
	if err != nil {
		log.Fatalf("Failed to load .env file: %s", err)
	}

	fastApiServer := os.Getenv("FAST_API_SERVER")
	if fastApiServer == "" {
		log.Fatalf("FAST_API_SERVER is not set")
	}
	FAST_API_SERVER = fastApiServer
	log.Printf("Making request to %s", FAST_API_SERVER+endpoint)
	log.Printf("Data: %s", string(data))
	client := &http.Client{
		Timeout: 30 * time.Hour,
	}
	req, err := http.NewRequest("POST", FAST_API_SERVER+endpoint, bytes.NewBuffer(data))
	if err != nil {
		log.Printf("Failed to create request: %s", err)
		return nil, err
	}
	req.Header.Set("x-api-key", apiKey)
	req.Header.Set("Content-Type", "application/json")
	resp, err := client.Do(req)
	if err != nil {
		log.Printf("Failed to send request: %s", err)
		return nil, err
	}

	if resp.StatusCode == 422 {
		body, _ := io.ReadAll(resp.Body)
		log.Printf("Received 422 error. Response body: %s", string(body))
		return nil, errors.New("422 error")
	}

	return resp, nil
}

func ProcessMessage(task types.Task, apiKey string) (*http.Response, types.Task, string, error) {
	task.Retries += 1
	endpoint := ENDPOINT_MAP[task.Type]
	if endpoint == "" {
		log.Printf("No endpoint found for type: %s", task.Type)
		return nil, task, apiKey, errors.New("no endpoint found for type: " + task.Type)
	}

	jsonData, err := json.Marshal(task.Data)
	if err != nil {
		log.Printf("Failed to marshal data: %s", err)
		return nil, task, apiKey, err
	}

	resp, err := MakeRequest(endpoint, jsonData, apiKey)
	if err != nil {
		log.Printf("Failed to create request: %s", err)
		return nil, task, apiKey, err
	}

	fmt.Println("Response Status:", resp.Status)
	return resp, task, apiKey, nil
}

var db *sql.DB

func InitDB() error {
	// Load database configuration from environment variables
	dbHost := os.Getenv("DB_HOST")
	dbPort := os.Getenv("DB_PORT")
	dbUser := os.Getenv("DB_USER")
	dbPassword := os.Getenv("DB_PASSWORD")
	dbName := os.Getenv("DB_NAME")

	// Create connection string
	connStr := fmt.Sprintf(
		"host=%s port=%s user=%s password=%s dbname=%s sslmode=disable",
		dbHost, dbPort, dbUser, dbPassword, dbName,
	)

	// Open database connection
	var err error
	db, err = sql.Open("postgres", connStr)
	if err != nil {
		return fmt.Errorf("error connecting to database: %w", err)
	}

	// Test the connection
	err = db.Ping()
	if err != nil {
		return fmt.Errorf("error pinging database: %w", err)
	}

	return nil
}

func getUserByID(userID string) (*types.User, error) {
	query := `
        SELECT id, name, email, created_at, updated_at, account_type, current_balance, total_used_tokens
        FROM "User"
        WHERE id = $1
    `

	var user types.User
	err := db.QueryRow(query, userID).Scan(
		&user.ID,
		&user.Name,
		&user.Email,
		&user.CreatedAt,
		&user.UpdatedAt,
		&user.AccountType,
		&user.CurrentBalance,
		&user.TotalUsedTokens,
	)

	if err == sql.ErrNoRows {
		return nil, fmt.Errorf("user not found with ID: %s", userID)
	}
	if err != nil {
		return nil, fmt.Errorf("error querying user: %w", err)
	}

	return &user, nil
}

func handleAPIResponse(resp *http.Response) error {
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return fmt.Errorf("failed to read response body: %w", err)
	}

	var wrapper types.AgentResponseWrapper
	if err := json.Unmarshal(body, &wrapper); err != nil {
		return fmt.Errorf("failed to unmarshal response: %w", err)
	}

	if wrapper.Response != nil {
		// Get user from database using the userID from the response
		user, err := getUserByID(wrapper.Response.UserID)
		if err != nil {
			return fmt.Errorf("failed to get user: %w", err)
		}
		return SendSuccessEmail(wrapper.Response, user)
	} else if wrapper.Error != nil {
		// For error case, we'll need the userID from somewhere else
		// You might want to pass it as a parameter to handleAPIResponse
		// For now, assuming it's available in the error response
		user, err := getUserByID(wrapper.Response.UserID)
		if err != nil {
			return fmt.Errorf("failed to get user: %w", err)
		}
		return SendErrorEmail(wrapper.Error, user)
	}

	return fmt.Errorf("invalid response format")
}
