import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

# Load .env file
load_dotenv()

def test_email():
    print("Testing Email Configuration...")
    
    smtp_server = os.getenv("EMAIL_HOST")
    smtp_port = os.getenv("EMAIL_PORT", 587)
    sender_email = os.getenv("EMAIL_USER")
    sender_password = os.getenv("EMAIL_PASSWORD")
    recipient_email = os.getenv("EMAIL_RECIPIENT") or sender_email
    
    print(f"Server: {smtp_server}:{smtp_port}")
    print(f"User: {sender_email}")
    print(f"Recipient: {recipient_email}")
    
    if not all([smtp_server, sender_email, sender_password]):
        print("❌ Error: Missing configuration in .env file.")
        return

    try:
        msg = MIMEText("This is a test email from your local Stock Analyzer environment.")
        msg['Subject'] = "Stock Analyzer - Test Email"
        msg['From'] = sender_email
        msg['To'] = recipient_email

        print("Connecting to SMTP server...")
        with smtplib.SMTP(smtp_server, int(smtp_port)) as server:
            server.set_debuglevel(1) # Show SMTP interaction
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        
        print("\n✅ Email sent successfully!")
        print("If this works, your credentials are correct.")
        print("The issue is likely that these variables are not set in Cloud Run.")
        
    except Exception as e:
        print(f"\n❌ Failed to send email: {e}")

if __name__ == "__main__":
    test_email()
