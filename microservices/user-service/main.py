from fastapi import FastAPI, HTTPException, Depends, status, Request, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta
import jwt
from google.oauth2 import id_token
from google.auth.transport import requests
import bcrypt
import logging
import uvicorn
from typing import Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field, validator, ConfigDict
import json
from bson import ObjectId
import asyncio
from config import settings
import aiohttp
from oauthlib.oauth2 import WebApplicationClient
import secrets
from google_auth_oauthlib.flow import Flow
from models.user import UserResponse, UserBase, UserCreate, UserLogin

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.SERVICE_NAME,
    version=settings.VERSION,
    docs_url="/api/v1/docs",
    openapi_url="/api/v1/openapi.json"
)

# Create a sub-application for API v1
api_v1 = FastAPI(title=f"{settings.SERVICE_NAME} API v1")

# Add CORS middleware to the main app
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=settings.CORS_METHODS,
    allow_headers=settings.CORS_HEADERS,
)

# Database connection
db = None

# Models
class GoogleAuthRequest(BaseModel):
    redirect_uri: str
    state: Optional[str] = None

class GoogleCallbackRequest(BaseModel):
    credential: str
    redirect_uri: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

# Database initialization
@app.on_event("startup")
async def startup_db_client():
    global db
    try:
        # Connect to MongoDB with retry logic
        for i in range(5):
            try:
                client = AsyncIOMotorClient(
                    settings.MONGODB_URL,
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=5000
                )
                await client.admin.command('ping')
                db = client[settings.MONGODB_DB_NAME]
                
                # Ensure indexes
                await db.users.create_index("email", unique=True)
                await db.users.create_index("auth_provider")
                
                logger.info(f"Connected to MongoDB at {settings.MONGODB_URL}")
                break
            except Exception as e:
                if i == 4:
                    logger.error(f"Failed to connect to MongoDB after 5 attempts: {str(e)}")
                    raise
                logger.warning(f"Failed to connect to MongoDB (attempt {i+1}): {str(e)}")
                await asyncio.sleep(2)
                
    except Exception as e:
        logger.error(f"Failed to initialize MongoDB connection: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_db_client():
    global db
    try:
        if db is not None and hasattr(db, 'client'):
            await db.client.close()
            logger.info("Closed MongoDB connection")
        else:
            logger.warning("No active MongoDB connection to close")
    except Exception as e:
        logger.error(f"Error closing MongoDB connection: {str(e)}")

# Helper functions
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    return await db.users.find_one({"email": email})

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check MongoDB connection
        if db is None:
            return {
                "status": "unhealthy",
                "error": "MongoDB client not initialized",
                "timestamp": datetime.utcnow().isoformat(),
                "version": settings.VERSION
            }
            
        await db.client.admin.command("ping")
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": settings.VERSION
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
            "version": settings.VERSION
        }

# Authentication endpoints
@api_v1.post("/auth/register", response_model=TokenResponse)
async def register(user: UserCreate):
    try:
        logging.info(f"Registration attempt for email: {user.email}")
        
        # Check if email exists
        existing_user = await get_user_by_email(user.email)
        if existing_user:
            logging.warning(f"Registration failed: Email already exists - {user.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        logging.info("Creating password hash...")
        # Hash password
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(user.password.encode(), salt)
        
        current_time = datetime.utcnow()
        
        # Create user
        user_dict = {
            "email": user.email,
            "full_name": user.full_name,
            "password_hash": hashed_password.decode(),
            "auth_provider": "email",
            "created_at": current_time,
            "updated_at": current_time,
            "is_active": True,
            "is_superuser": False,
            "profile_picture": None
        }
        
        logging.info("Inserting new user into database...")
        result = await db.users.insert_one(user_dict)
        
        # Add the _id to the user dict
        user_dict["_id"] = str(result.inserted_id)
        
        logging.info(f"User created successfully with ID: {result.inserted_id}")
        
        # Generate token
        access_token = create_access_token(
            data={"sub": str(result.inserted_id), "email": user.email},
            expires_delta=timedelta(days=1)
        )
        
        # Create response
        response = TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse(**user_dict)
        )
        
        logging.info("Registration completed successfully")
        return response
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Registration error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing registration: {str(e)}"
        )

@api_v1.post("/auth/login", response_model=TokenResponse)
async def login(user_data: UserLogin):
    try:
        logging.info(f"Login attempt for email: {user_data.email}")
        
        # Get user
        user = await get_user_by_email(user_data.email)
        if not user:
            logging.warning(f"Login failed: User not found - {user_data.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        logging.info("User found, verifying password...")
        
        # Verify password
        is_valid = bcrypt.checkpw(user_data.password.encode(), user["password_hash"].encode())
        
        logging.info(f"Password verification result: {is_valid}")
        
        if not is_valid:
            logging.warning("Login failed: Invalid password")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        logging.info("Password verified, generating token...")
        # Generate token
        access_token = create_access_token(
            data={"sub": str(user["_id"]), "email": user["email"]},
            expires_delta=timedelta(days=1)
        )

        logging.info("Login successful")
        # Convert ObjectId to string before creating UserResponse
        user["_id"] = str(user["_id"])
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse(**user)
        )
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing login: {str(e)}"
        )

@api_v1.get("/auth/google/authorize")
async def init_google_login(redirect_uri: str = Query(..., description="The URI to redirect to after authorization")):
    try:
        logging.info(f"Received Google login initialization request with redirect_uri: {redirect_uri}")
        
        # Create the flow using the client secrets
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=[
                "openid",
                "https://www.googleapis.com/auth/userinfo.email",
                "https://www.googleapis.com/auth/userinfo.profile"
            ],
            redirect_uri=redirect_uri
        )
        
        # Generate the authorization URL
        auth_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        logging.info(f"Generated authorization URL with state: {state}")
        
        return {"auth_url": auth_url, "state": state}
        
    except Exception as e:
        logging.error(f"Error in Google login initialization: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_v1.post("/auth/google/callback")
async def google_callback(request: GoogleCallbackRequest):
    try:
        logging.info("Received Google callback request with credential")
        
        if not request.credential:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Credential is required"
            )
            
        try:
            # Verify the Google ID token
            token_request = requests.Request()
            
            try:
                logging.info("Verifying Google ID token...")
                id_info = id_token.verify_oauth2_token(
                    request.credential,
                    token_request,
                    settings.GOOGLE_CLIENT_ID,
                    clock_skew_in_seconds=10
                )
                
                logging.info(f"Token verification result: {id_info}")
                
                # Verify issuer
                if id_info['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                    raise ValueError('Wrong issuer.')
                
                # Get user info from token
                email = id_info.get('email')
                if not email:
                    raise ValueError('Email not found in token.')
                
                name = id_info.get('name', '')
                picture = id_info.get('picture', '')
                
                logging.info(f"Successfully verified Google ID token for email: {email}")
                
                # Check if user exists
                user = await db.users.find_one({"email": email})
                logging.info(f"Database lookup result for user: {'Found' if user else 'Not found'}")
                
                current_time = datetime.utcnow()
                
                if not user:
                    # Create new user
                    user = {
                        "email": email,
                        "full_name": name,
                        "profile_picture": picture,
                        "created_at": current_time,
                        "updated_at": current_time,
                        "auth_provider": "google",
                        "is_active": True,
                        "is_superuser": False,
                        "password_hash": None
                    }
                    result = await db.users.insert_one(user)
                    user["_id"] = result.inserted_id
                    logging.info(f"Created new user with email: {email}")
                else:
                    # Update existing user
                    update_data = {
                        "full_name": name or user.get("full_name", ""),
                        "profile_picture": picture or user.get("profile_picture", ""),
                        "updated_at": current_time,
                        "last_login": current_time,
                        "auth_provider": "google"
                    }
                    await db.users.update_one(
                        {"email": email},
                        {"$set": update_data}
                    )
                    user.update(update_data)
                    logging.info(f"Updated existing user with email: {email}")
                
                # Generate access token
                access_token = create_access_token(
                    data={"sub": str(user["_id"]), "email": email}
                )
                
                # Convert ObjectId to string for response
                user["_id"] = str(user["_id"])
                
                return TokenResponse(
                    access_token=access_token,
                    token_type="bearer",
                    user=UserResponse(**user)
                )
                
            except ValueError as ve:
                logging.error(f"Token verification error: {str(ve)}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid token: {str(ve)}"
                )
            
        except Exception as e:
            logging.error(f"Error processing Google token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"Error in Google callback: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

async def get_current_user(authorization: Optional[str] = Header(None)):
    try:
        if not authorization or not authorization.startswith('Bearer '):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid authorization header"
            )
            
        token = authorization.split(' ')[1]
        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
            user_id = payload.get('sub')
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload"
                )
        except jwt.PyJWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
            
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
            
        return UserResponse(**user)
            
    except Exception as e:
        logger.error(f"Error getting current user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@api_v1.get("/auth/me", response_model=UserResponse)
async def get_profile(current_user: UserResponse = Depends(get_current_user)):
    return current_user

# Mount the v1 API under /api/v1
app.mount("/api/v1", api_v1)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    ) 