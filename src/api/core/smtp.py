import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from src.config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM


def send_email(to_email: str, subject: str, body: str):
    msg = MIMEMultipart()
    msg["From"] = SMTP_FROM
    msg["To"] = to_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "html"))

    print(f"✅ Email sent to {to_email}")

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"❌ Email sending failed: {e}")
        return False
