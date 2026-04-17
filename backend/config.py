"""Config — all secrets from env vars."""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

# DeepSeek
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"

# FastAPI
HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", "8080"))

# Conversations
MAX_CONVERSATIONS = 100
MAX_MESSAGES_PER_CONVERSATION = 200

# Vbee TTS
VBEE_TOKEN = os.getenv("VBEE_TOKEN", "")
VBEE_APP_ID = os.getenv("VBEE_APP_ID", "")
VBEE_VOICE_CODE = "70fbfd7a-486b-4804-b113-b33b4d0c56bd"

# Stripe
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")

# JWT
JWT_SECRET = os.getenv("JWT_SECRET", "gptweb-secret-change-in-production-2026")

# Domain
DOMAIN = os.getenv("DOMAIN", "localhost:8080")
