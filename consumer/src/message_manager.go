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
	_, err := os.Stat(".env")

	if err == nil || os.IsNotExist(err) {
		_ = godotenv.Load()
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
	_, err := os.Stat(".env")

	if err == nil || os.IsNotExist(err) {
		_ = godotenv.Load()
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

func ProcessMessage(task types.Task, apiKey string, db *sql.DB) (*http.Response, types.Task, string, error) {
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
	fmt.Printf("DB: %v\n", db)

	// Handle the error from handleAPIResponse
	if err := handleAPIResponse(resp, db); err != nil {
		log.Printf("Error handling API response: %v", err)
		return resp, task, apiKey, err
	}

	return resp, task, apiKey, nil
}

func InitDB() (*sql.DB, error) {

	database_url := os.Getenv(("DATABASE_URL"))

	if database_url == "" {
		return nil, fmt.Errorf("DATABASE_URL is not set")
	}

	var db *sql.DB

	// Open database connection
	var err error
	db, err = sql.Open("postgres", database_url)
	if err != nil {
		return nil, fmt.Errorf("error connecting to database: %w", err)
	}

	// Test the connection
	err = db.Ping()
	if err != nil {
		return nil, fmt.Errorf("error pinging database: %w", err)
	}

	fmt.Printf("Connected to database\n")

	if db == nil {
		return nil, fmt.Errorf("db is nil")
	}

	return db, nil
}

func getUserByID(userID string, db *sql.DB) (*types.User, error) {
	// Input validation
	if userID == "" {
		return nil, fmt.Errorf("userID cannot be empty")
	} else {
		log.Printf("Getting user with ID: %s", userID)
	}

	// Early db connection check
	if db == nil {
		return nil, fmt.Errorf("database connection not initialized")
	} else {
		log.Printf("Database connection initialized")
	}

	query := `
		SELECT id, name, email
		FROM "User"
		WHERE id = $1`

	// Prepare the statement to verify query syntax
	stmt, err := db.Prepare(query)
	if err != nil {
		return nil, fmt.Errorf("failed to prepare query: %w", err)
	}
	defer stmt.Close()

	// Initialize user struct
	user := &types.User{}

	// Execute query and scan results
	err = stmt.QueryRow(userID).Scan(
		&user.ID,
		&user.Name,
		&user.Email,
	)

	// Handle specific error cases
	switch {
	case err == sql.ErrNoRows:
		return nil, fmt.Errorf("user not found with ID: %s", userID)
	case err != nil:
		return nil, fmt.Errorf("error querying user: %w", err)
	}

	// Log successful query (optional, for debugging)
	log.Printf("Successfully retrieved user with ID: %s", userID)

	return user, nil
}

func handleAPIResponse(resp *http.Response, db *sql.DB) error {
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
		user, err := getUserByID(wrapper.Response.UserID, db)
		if err != nil {
			return fmt.Errorf("failed to get user: %w", err)
		}

		if user != nil {
			fmt.Println("User Email:", user.Email)
			return SendSuccessEmail(wrapper.Response, user)
		}
		return fmt.Errorf("user not found")

	} else if wrapper.Error != nil {
		// For error case, we need to get the userID from the error wrapper
		if wrapper.Response.UserID == "" {
			return fmt.Errorf("no userID provided in error response")
		}

		user, err := getUserByID(wrapper.Response.UserID, db)
		if err != nil {
			return fmt.Errorf("failed to get user: %w", err)
		}

		if user != nil {
			return SendErrorEmail(wrapper.Error, user)
		}
		return fmt.Errorf("user not found")
	}

	return fmt.Errorf("invalid response format")
}
