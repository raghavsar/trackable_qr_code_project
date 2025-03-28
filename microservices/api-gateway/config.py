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

def get_cors_origins() -> List[str]:
    """Parse CORS_ORIGINS from environment variable."""
    origins = os.getenv("CORS_ORIGINS")
    if origins:
        try:
            return json.loads(origins)
        except json.JSONDecodeError:
            return [origins]  # Single origin provided as string
    # Default fallback values
    return ["http://localhost:5173", "http://192.168.7.60:5173", "http://192.168.7.60:8000"]

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
    CORS_ORIGINS: List[str] = get_cors_origins()

    model_config = {
        "env_file": ".env",
        "extra": "allow"
    }

settings = Settings() 