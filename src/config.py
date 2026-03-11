import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY")
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv(
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        30,
    )
)
ACCESS_TOKEN_EXPIRE = int(
    os.getenv(
        "ACCESS_TOKEN_EXPIRE",
        30,
    )
)
DOMAIN = os.getenv("DOMAIN")


# Email
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "youremail@gmail.com")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "yourpassword")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)
RESET_URL = os.getenv("RESET_URL", f"{DOMAIN}/reset-password")


AUTH_PASSWORD = os.getenv("AUTH_PASSWORD")
