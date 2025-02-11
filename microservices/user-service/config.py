from typing import List
import os
from dotenv import load_dotenv
import json

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

class Settings:
    # Service Info
    SERVICE_NAME: str = "User Service"
    VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Server Settings
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8001"))
    
    # MongoDB Settings
    MONGODB_URL: str = get_required_env("MONGODB_URL")
    MONGODB_DB_NAME: str = get_required_env("MONGODB_DB_NAME")
    
    # JWT Settings
    JWT_SECRET: str = get_required_env("JWT_SECRET")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    
    # Google OAuth Settings
    GOOGLE_CLIENT_ID: str = get_required_env("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: str = get_required_env("GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URIS: List[str] = get_redirect_uris()
    
    # CORS Settings
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",  # Frontend
        "http://localhost:8000"   # API Gateway
    ]
    CORS_METHODS: List[str] = ["*"]
    CORS_HEADERS: List[str] = ["*"]

settings = Settings() 