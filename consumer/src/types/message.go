package types

type EmailMessage struct {
	To      string `json:"to"`
	From    string `json:"from"`
	Subject string `json:"subject"`
	Content string `json:"content"`
	IsHTML  bool   `json:"is_html"`
}
