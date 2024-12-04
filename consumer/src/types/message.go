package types

import (
	"database/sql"

	"github.com/go-redis/redis/v8"
)

type EmailMessage struct {
	To      string `json:"to"`
	From    string `json:"from"`
	Subject string `json:"subject"`
	Content string `json:"content"`
	IsHTML  bool   `json:"is_html"`
}
type AppContext struct {
	DB    *sql.DB
	Redis *redis.Client
}
