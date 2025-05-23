package src

import (
	"fmt"
	"os"
	"strconv"

	"github.com/sohamratnaparkhi/cortex-cache-ai-backend/consumer/src/types"
	"gopkg.in/gomail.v2"
)

var emailDialer *gomail.Dialer

func InitEmailDialer() error {
	smtpPort, err := strconv.Atoi(os.Getenv("SMTP_PORT"))
	if err != nil {
		return err
	}

	emailDialer = gomail.NewDialer(
		os.Getenv("SMTP_HOST"),
		smtpPort,
		os.Getenv("SMTP_USERNAME"),
		os.Getenv("SMTP_PASSWORD"),
	)

	return nil
}

func SendEmail(msg types.EmailMessage) error {
	m := gomail.NewMessage()
	m.SetHeader("From", msg.From)
	m.SetHeader("To", msg.To)
	m.SetHeader("Subject", msg.Subject)

	if msg.IsHTML {
		content := msg.Content
		if msg.Content == "welcome" {
			content = WelcomeHtml
		}
		m.SetBody("text/html", content)
	} else {
		m.SetBody("text/plain", msg.Content)
	}
	fmt.Printf("Sending email to %s\n", msg.To)
	fmt.Printf("Email content: %s\n", msg.Content)
	fmt.Printf("Email subject: %s\n", msg.Subject)
	fmt.Printf("Email from: %s\n", msg.From)
	return emailDialer.DialAndSend(m)
}

func SendSuccessEmail(response *types.AgentResponse, user *types.User) error {
	viewEndpoint := fmt.Sprintf("%s/memories", "www.mindkeeperai.com")
	chatEndpoint := fmt.Sprintf("%s/memories/chat/%s", "www.mindkeeperai.com", response.MemoryID)

	title := response.Title

	if title != "" {
		title = fmt.Sprintf("titled <strong>%s</strong>", title)
	}

	htmlContent := fmt.Sprintf(SuccessfulMemoryHtml, user.Name, title, viewEndpoint, chatEndpoint, response.MemoryID)

	msg := types.EmailMessage{
		From:    "info@mindkeeperai.com",
		To:      user.Email,
		Subject: "Memory Added Successfully - MindKeeper AI",
		Content: htmlContent,
		IsHTML:  true,
	}

	err := SendEmail(msg)
	if err != nil {
		fmt.Printf("Failed to send success email: %s", err)
	}
	return err
}

func SendErrorEmail(agentError *types.AgentError, user *types.User) error {
	htmlContent := fmt.Sprintf(`
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #e74c3c;">Hello %s</h2>
                
                <p>We encountered an error while attempting to add your recent memory to MindKeeper.</p>
                
                <div style="background-color: #f9f9f9; padding: 15px; border-left: 4px solid #e74c3c; margin: 20px 0;">
                    <p style="margin: 0;"><strong>Error Details:</strong></p>
                    <p style="margin: 10px 0 0;">%s</p>
                </div>
                
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee;">
                    <p style="color: #95a5a6; font-size: 0.9em;">
                        Please try again later or reply back to this email if the issue persists.
                    </p>
                </div>
            </div>
        </body>
        </html>
    `, user.Name, agentError.Error)

	msg := types.EmailMessage{
		From:    "info@mindkeeperai.com",
		To:      user.Email,
		Subject: "Error Adding Memory - MindKeeper",
		Content: htmlContent,
		IsHTML:  true,
	}

	err := SendEmail(msg)
	if err != nil {
		fmt.Printf("Failed to send error email: %s", err)
	}
	return err
}
