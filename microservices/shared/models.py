from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, EmailStr
from bson import ObjectId

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, info=None):  # Added info parameter with default None
        if v is None:
            return None
        if isinstance(v, ObjectId):
            return v
        if isinstance(v, str):
            try:
                return ObjectId(v)
            except Exception:
                return None
        return None

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler):
        json_schema = handler(core_schema)
        json_schema.update(type="string")
        return json_schema

    def __repr__(self):
        return f"PyObjectId({super().__repr__()})"

# User Models
class UserBase(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str

class UserCreate(UserBase):
    password: str

class UserInDB(UserBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    hashed_password: str
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda dt: dt.isoformat()
        }

# VCard Models
class AddressData(BaseModel):
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None

class VCardData(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    first_name: str
    last_name: str
    email: str
    mobile_number: Optional[str] = None
    work_number: Optional[str] = None
    profile_picture: Optional[str] = None  # Base64 encoded image or URL
    company: Optional[str] = None
    title: Optional[str] = None
    website: Optional[str] = None
    address: Optional[AddressData] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    user_id: Optional[str] = None

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda dt: dt.isoformat()
        }

# QR Code Models
class QRCode(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    vcard_id: str
    user_id: str
    image: str
    created_at: datetime
    updated_at: datetime
    total_scans: int = 0

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda dt: dt.isoformat()
        }

class QRDesignOptions(BaseModel):
    pattern_style: str = "square"  # square, rounded, dots, gapped, vertical, horizontal
    eye_style: str = "square"  # square, rounded, dots
    foreground_color: str = "#000000"
    background_color: str = "#FFFFFF"
    error_correction: str = "H"  # L, M, Q, H
    box_size: int = 10
    border: int = 4
    logo_url: Optional[str] = None
    logo_size: float = 0.2  # Size relative to QR code (0.1 to 0.3)
    logo_background: Optional[bool] = False
    logo_round: Optional[bool] = False

    class Config:
        populate_by_name = True

class QRTemplate(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    name: str
    description: Optional[str] = None
    design: QRDesignOptions
    user_id: Optional[str] = None  # None for public templates
    is_public: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda dt: dt.isoformat()
        }

# Analytics Models
class ScanEvent(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    vcard_id: str
    user_id: str
    device_type: str
    browser: str
    os: str
    location: Optional[str] = None
    referrer: Optional[str] = None
    user_agent: str
    timestamp: datetime

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda dt: dt.isoformat()
        }

class AnalyticsSummary(BaseModel):
    total_scans: int
    scans_by_date: Dict[str, int]
    scans_by_device: Dict[str, int]
    scans_by_location: Dict[str, int]

# Message Models
class KafkaMessage(BaseModel):
    event_type: str
    payload: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        } 