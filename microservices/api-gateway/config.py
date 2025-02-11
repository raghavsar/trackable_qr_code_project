from pydantic_settings import BaseSettings
from typing import List
from dotenv import load_dotenv
import json
import os

load_dotenv()

def get_required_env(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise ValueError(f"Missing required environment variable: {key}")
    return value

def get_redirect_uris() -> List[str]:
    uris = os.getenv("GOOGLE_REDIRECT_URIS")
    if uris:
        try:
            return json.loads(uris)
        except json.JSONDecodeError:
            return [uris]  # Single URI provided as string
    return ["http://localhost:5173/auth/google/callback"]

class Settings(BaseSettings):
    # Service Info
    SERVICE_NAME: str = "QR Code Generator API Gateway"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # JWT Settings
    JWT_SECRET: str = get_required_env("JWT_SECRET")
    JWT_ALGORITHM: str = "HS256"

    # Service URLs
    USER_SERVICE_URL: str
    VCARD_SERVICE_URL: str
    QR_SERVICE_URL: str
    ANALYTICS_SERVICE_URL: str
    REDIRECT_SERVICE_URL: str
    FRONTEND_URL: str

    # CORS Settings
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",  # Dev frontend
        "http://192.168.7.154:5173",
        "http://192.168.7.154:8000"  
    ]
    CORS_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
    CORS_HEADERS: List[str] = [
        "Content-Type",
        "Authorization",
        "X-User-ID",
        "Accept",
        "Origin",
        "X-Requested-With",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers"
    ]
    CORS_MAX_AGE: int = 3600  # Cache preflight requests for 1 hour

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Parse CORS_ORIGINS from string if needed
        if isinstance(self.CORS_ORIGINS, str):
            try:
                self.CORS_ORIGINS = json.loads(self.CORS_ORIGINS)
            except json.JSONDecodeError:
                self.CORS_ORIGINS = [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    model_config = {
        "env_file": ".env",
        "extra": "allow"
    }

settings = Settings() 