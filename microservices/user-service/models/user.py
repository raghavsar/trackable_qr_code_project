from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from bson import ObjectId

class PyObjectId(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, handler):
        try:
            if isinstance(v, ObjectId):
                return str(v)
            return str(ObjectId(str(v)))
        except Exception:
            raise ValueError("Invalid ObjectId")

class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    is_active: bool = True
    auth_provider: str = "email"
    profile_picture: Optional[str] = None

    model_config = {
        "populate_by_name": True
    }

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

    model_config = {
        "populate_by_name": True
    }

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    password: Optional[str] = None

    model_config = {
        "populate_by_name": True
    }

class UserResponse(UserBase):
    id: PyObjectId = Field(alias="_id")
    created_at: datetime
    updated_at: datetime
    is_superuser: bool = False

    model_config = {
        "populate_by_name": True,
        "json_encoders": {
            datetime: lambda v: v.isoformat(),
            ObjectId: lambda v: str(v)
        },
        "json_schema_extra": {
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "email": "user@example.com",
                "full_name": "John Doe",
                "auth_provider": "email",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00",
                "is_active": True,
                "is_superuser": False,
                "profile_picture": None
            }
        }
    } 