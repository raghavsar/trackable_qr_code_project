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

class Settings:
    # Service Info
    SERVICE_NAME: str = "Analytics Service"
    VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Server Settings
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8004"))
    
    # MongoDB Settings
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://admin:adminpassword@mongodb:27017/qr_code_db?authSource=admin&directConnection=true")
    
    # Redis Settings (if used)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    
    # JWT Settings
    JWT_SECRET: str = os.getenv("JWT_SECRET", "")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRATION: int = int(os.getenv("JWT_EXPIRATION", "3600"))
    
    # CORS Settings
    CORS_ORIGINS: List[str] = []
    
    def __init__(self):
        # Parse CORS_ORIGINS from string if provided
        cors_origins = os.getenv("CORS_ORIGINS")
        if cors_origins:
            try:
                self.CORS_ORIGINS = json.loads(cors_origins)
            except json.JSONDecodeError:
                self.CORS_ORIGINS = [origin.strip() for origin in cors_origins.split(",")]
        
        # Default origins if none provided
        if not self.CORS_ORIGINS:
            self.CORS_ORIGINS = [
                "http://localhost:5173",
                "http://192.168.7.154:5173"
            ]

settings = Settings() 