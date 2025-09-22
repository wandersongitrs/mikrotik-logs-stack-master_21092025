# Configuration file for Telegram Bridge
import os

# Telegram Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Rate Limiting Configuration
RATE_LIMIT = int(os.getenv("RATE_LIMIT", "20"))  # messages per minute
DEDUP_WINDOW = int(os.getenv("DEDUP_WINDOW", "60"))  # seconds
MIN_SEVERITY = os.getenv("MIN_SEVERITY", "info")

# Server Configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8080"))

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Anti-spam Configuration
ENABLE_ANTI_SPAM = os.getenv("ENABLE_ANTI_SPAM", "true").lower() == "true"
ENABLE_DEDUPLICATION = os.getenv("ENABLE_DEDUPLICATION", "true").lower() == "true"
