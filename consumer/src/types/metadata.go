package types

import (
	"github.com/golang-jwt/jwt/v5"
)

// Metadata represents the main metadata model that includes common fields and specific metadata
type Metadata struct {
	UserID          string      `json:"user_id"`
	MemID           string      `json:"mem_id"`
	Title           string      `json:"title"`
	Description     string      `json:"description"`
	CreatedAt       string      `json:"created_at"`
	LastUpdated     string      `json:"last_updated"`
	Tags            []string    `json:"tags"`
	Source          string      `json:"source"`
	Language        string      `json:"language"`
	Type            string      `json:"type"`
	ContentHash     *string     `json:"content_hash,omitempty"`
	SpecificDesc    interface{} `json:"specific_desc"`
	AISummary       *string     `json:"ai_summary,omitempty"`
	AIInsights      *string     `json:"ai_insights,omitempty"`
	RelatedMemories []string    `json:"related_memories,omitempty"`
}

type Claims struct {
	UserId string `json:"user_id"`
	APIKey string `json:"api_key"`
	jwt.RegisteredClaims
}

type Task struct {
	Type    string      `json:"type"`
	Data    interface{} `json:"data"`
	Retries int         `json:"retries"`
}

type AgentResponse struct {
	Transcript string      `json:"transcript"`
	Chunks     []string    `json:"chunks"`
	Metadata   interface{} `json:"metadata"`
	UserID     string      `json:"userId"`
	MemoryID   string      `json:"memoryId"`
	Title      string      `json:"title"`
}

type AgentError struct {
	Error string `json:"error"`
}

type AgentResponseWrapper struct {
	Response *AgentResponse `json:"response"`
	Error    *AgentError    `json:"error"`
}

type User struct {
	ID    string
	Name  string
	Email string
}
