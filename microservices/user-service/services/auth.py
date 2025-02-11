from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from motor.motor_asyncio import AsyncIOMotorDatabase
from models.user import User, UserCreate, UserResponse, UserUpdate
from config import settings
import httpx
from bson import ObjectId
from google.oauth2 import id_token
from google.auth.transport import requests

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

class AuthService:
    def __init__(
        self,
        db: AsyncIOMotorDatabase = Depends(lambda: settings.mongodb)  # type: ignore
    ):
        self.db = db
        self.users_collection = db.users

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        return pwd_context.hash(password)

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        return encoded_jwt

    async def get_user_by_email(self, email: str) -> Optional[User]:
        user_dict = await self.users_collection.find_one({"email": email})
        if user_dict:
            return User(**user_dict)
        return None

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        user_dict = await self.users_collection.find_one({"_id": ObjectId(user_id)})
        if user_dict:
            return User(**user_dict)
        return None

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        user = await self.get_user_by_email(email)
        if not user:
            return None
            
        if user.auth_provider == "google":
            raise ValueError("This email is registered with Google. Please use 'Continue with Google' to log in.")
            
        if not user.hashed_password or not self.verify_password(password, user.hashed_password):
            return None
        return user

    async def create_user(self, user_create: UserCreate) -> User:
        # Check if user already exists
        existing_user = await self.get_user_by_email(user_create.email)
        if existing_user:
            raise ValueError("Email already registered")

        # Create new user
        user_dict = user_create.dict()
        user_dict["hashed_password"] = self.get_password_hash(user_create.password)
        user_dict["created_at"] = datetime.utcnow()
        user_dict["updated_at"] = datetime.utcnow()
        user_dict["auth_provider"] = "email"
        del user_dict["password"]

        result = await self.users_collection.insert_one(user_dict)
        user_dict["_id"] = result.inserted_id
        
        return User(**user_dict)

    async def verify_google_token(self, token: str) -> User:
        try:
            # Verify the token with Google
            idinfo = id_token.verify_oauth2_token(
                token, 
                requests.Request(), 
                settings.GOOGLE_CLIENT_ID
            )

            # Get user info from the token
            email = idinfo['email']
            name = idinfo.get('name', '')
            picture = idinfo.get('picture')

            # Check if user exists
            user = await self.get_user_by_email(email)
            
            if user:
                # Update existing user
                update_data = {
                    "updated_at": datetime.utcnow(),
                    "profile_picture": picture
                }
                
                # Only update name if it was originally a Google user
                if user.auth_provider == "google":
                    update_data["full_name"] = name
                
                await self.users_collection.update_one(
                    {"_id": ObjectId(user.id)},
                    {"$set": update_data}
                )
                
                return await self.get_user_by_id(user.id)
            
            # Create new user
            user_data = {
                "email": email,
                "full_name": name,
                "profile_picture": picture,
                "is_active": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "auth_provider": "google",
                "hashed_password": None
            }
            
            result = await self.users_collection.insert_one(user_data)
            user_data["_id"] = result.inserted_id
            
            return User(**user_data)

        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid Google token: {str(e)}"
            )

    @staticmethod
    async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserResponse:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            user_id: str = payload.get("sub")
            if user_id is None:
                raise credentials_exception
        except JWTError:
            raise credentials_exception

        user = await AuthService().get_user_by_id(user_id)
        if user is None:
            raise credentials_exception
            
        return UserResponse.from_orm(user)

    async def update_user_profile(self, user_id: str, update_data: UserUpdate) -> User:
        update_dict = update_data.dict(exclude_unset=True)
        if not update_dict:
            raise ValueError("No fields to update")

        update_dict["updated_at"] = datetime.utcnow()

        result = await self.users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_dict}
        )

        if result.modified_count == 0:
            raise ValueError("User not found or no changes made")

        return await self.get_user_by_id(user_id)

    async def update_user_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str
    ) -> None:
        user = await self.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        if not self.verify_password(current_password, user.hashed_password):
            raise ValueError("Current password is incorrect")

        hashed_password = self.get_password_hash(new_password)
        await self.users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "hashed_password": hashed_password,
                    "updated_at": datetime.utcnow()
                }
            }
        )

    async def delete_user(self, user_id: str) -> None:
        result = await self.users_collection.delete_one({"_id": ObjectId(user_id)})
        if result.deleted_count == 0:
            raise ValueError("User not found") 