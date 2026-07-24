from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # App
    APP_NAME: str = "TradeMind AI"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "changeme"
    CORS_ORIGINS: str = "https://trademind-ai12.vercel.app,http://localhost:3000"
    FRONTEND_URL: str = "https://trademind-ai12.vercel.app"
    BACKEND_URL: str = "https://trademind-ai-l4qe.onrender.com"

    def get_cors_origins(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    # Database — always loaded from .env; this default is a fallback only
    DATABASE_URL: str = "postgresql+asyncpg://trademinddb_user:5LbNKHGmlvwF3uQoDhqX34SsqucDFpG1@dpg-d99l9v7aqgkc738c3mgg-a.singapore-postgres.render.com/trademinddb"
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET: str = "changeme_min_32_chars_long_secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # External APIs
    ALPHA_VANTAGE_KEY: str = ""
    ALPACA_API_KEY: str = ""
    ALPACA_SECRET: str = ""
    ALPACA_BASE_URL: str = "https://paper-api.alpaca.markets"
    XAI_API_KEY: str = ""
    XAI_MODEL: str = "grok-3-mini"
    NEWS_API_KEY: str = ""

    # AWS
    AWS_ACCESS_KEY: str = ""
    AWS_SECRET: str = ""
    AWS_REGION: str = "us-east-1"
    AWS_S3_BUCKET: str = "trademind-ai-assets"

    # Email (SendGrid)
    SENDGRID_API_KEY: str = ""
    SENDGRID_FROM_EMAIL: str = "noreply@trademind.ai"
    SENDGRID_FROM_NAME: str = "TradeMind AI"

    # Gmail SMTP
    GMAIL_USER: str = ""
    GMAIL_APP_PASSWORD: str = ""

    # SMS
    TWILIO_API_KEY: str = ""
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # OpenAI
    OPENAI_API_KEY: str = ""

    # Groq (free, fast — Llama 3 / Mixtral)
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # Hugging Face Inference API
    HF_API_KEY: str = ""
    HF_MODEL: str = "mistralai/Mistral-7B-Instruct-v0.3"
    HF_MODEL_REPO: str = ""  # e.g. your-username/trademind-lstm

    # Admin bootstrap (hashed password only — never plain text)
    ADMIN_EMAIL: str = "ch.karthikeya868769@gmail.com"
    ADMIN_PASSWORD_HASH: str = ""  # Set via env: bcrypt hash of admin password

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
