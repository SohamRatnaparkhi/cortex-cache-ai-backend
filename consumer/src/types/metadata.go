package types

import (
	"time"

	"github.com/golang-jwt/jwt/v5"
)

// YouTubeSpecificMd represents specific metadata for YouTube content
type YouTubeSpecificMd struct {
	VideoID     string `json:"video_id"`
	ChannelName string `json:"channel_name"`
	AuthorName  string `json:"author_name"`
	ChunkID     string `json:"chunk_id"`
}

// GitSpecificMd represents specific metadata for Git content
type GitSpecificMd struct {
	RepoName            string `json:"repo_name"`
	RepoCreatorName     string `json:"repo_creator_name"`
	FileName            string `json:"file_name"`
	ProgrammingLanguage string `json:"programming_language"`
	ChunkType           string `json:"chunk_type"`
	ChunkID             string `json:"chunk_id"`
}

// MediaSpecificMd represents specific metadata for media content
type MediaSpecificMd struct {
	Type    string `json:"type"`
	ChunkID string `json:"chunk_id"`
}

// ImageSpecificMd represents specific metadata for image content
type ImageSpecificMd struct {
	Width   int    `json:"width"`
	Height  int    `json:"height"`
	Format  string `json:"format"`
	ChunkID string `json:"chunk_id"`
}

// TextSpecificMd represents specific metadata for text content
type TextSpecificMd struct {
	WordCount   int      `json:"word_count"`
	ReadingTime float64  `json:"reading_time"`
	Tags        []string `json:"tags"`
	ChunkID     string   `json:"chunk_id"`
}

// MindMapSpecificMd represents specific metadata for mind map content
type MindMapSpecificMd struct {
	MemoryCount  int      `json:"memory_count"`
	CentralTopic string   `json:"central_topic"`
	Subtopics    []string `json:"subtopics"`
	ChunkID      string   `json:"chunk_id"`
}

// Metadata represents the main metadata model that includes common fields and specific metadata
type Metadata struct {
	UserID          string      `json:"user_id"`
	MemID           string      `json:"mem_id"`
	Title           string      `json:"title"`
	Description     string      `json:"description"`
	CreatedAt       time.Time   `json:"created_at"`
	LastUpdated     time.Time   `json:"last_updated"`
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
