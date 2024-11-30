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
		m.SetBody("text/html", msg.Content)
	} else {
		m.SetBody("text/plain", msg.Content)
	}

	return emailDialer.DialAndSend(m)
}

func SendSuccessEmail(response *types.AgentResponse, user *types.User) error {
	viewEndpoint := fmt.Sprintf("%s/memories/%s", FAST_API_SERVER, response.MemoryID)
	chatEndpoint := fmt.Sprintf("%s/chat/%s", FAST_API_SERVER, response.MemoryID)

	htmlContent := fmt.Sprintf(`
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2c3e50;">Hello %s! 🎉</h2>
                
                <p>Great news! Your memory titled "<strong>%s</strong>" has been successfully added to MindKeeper.</p>
                
                <div style="margin: 25px 0;">
                    <p>You can now:</p>
                    <ul>
                        <li><a href="%s" style="color: #3498db;">View your memory</a></li>
                        <li><a href="%s" style="color: #3498db;">Chat with your memory</a></li>
                    </ul>
                </div>
                
                <p style="color: #7f8c8d;">Memory ID: %s</p>
                
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee;">
                    <p style="color: #95a5a6; font-size: 0.9em;">
                        If you have any questions or need assistance, please don't hesitate to reach out to our support team.
                    </p>
                </div>
            </div>
        </body>
        </html>
    `, user.Name, response.Title, viewEndpoint, chatEndpoint, response.MemoryID)

	msg := types.EmailMessage{
		From:    "noreply@mindkeeperai.com",
		To:      user.Email,
		Subject: "Memory Added Successfully - MindKeeper",
		Content: htmlContent,
		IsHTML:  true,
	}

	return SendEmail(msg)
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
                        Please try again later or contact our support team if the issue persists.
                    </p>
                </div>
            </div>
        </body>
        </html>
    `, user.Name, agentError.Error)

	msg := types.EmailMessage{
		From:    "noreply@mindkeeperai.com",
		To:      user.Email,
		Subject: "Error Adding Memory - MindKeeper",
		Content: htmlContent,
		IsHTML:  true,
	}

	return SendEmail(msg)
}
