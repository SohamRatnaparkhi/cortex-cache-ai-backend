package src

import (
	"bytes"
	"encoding/json"
	"errors"
	"io"
	"log"
	"net/http"
	"os"
	"time"

	"github.com/IBM/sarama"
	"github.com/golang-jwt/jwt/v5"
	"github.com/joho/godotenv"
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
	log.Printf("Making request to %s", endpoint)
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
		// Handle the error appropriately
	}
	return resp, nil
}

func ProcessMessage(task types.Task, message *sarama.ConsumerMessage) (*http.Response, types.Task, string, error) {
	// TODO: get endpoint based on type
	apiKey, err := GetApikeyFromHeaders(message)
	if err != nil {
		log.Printf("Failed to get api key from headers: %s", err)
		return nil, task, apiKey, err
	}
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
	return resp, task, apiKey, nil
}
