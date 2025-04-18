from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, EmailStr, validator
from bson import ObjectId
import uuid
import re

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
        populate_by_name = True
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

    @classmethod
    def get_default_address(cls):
        """Returns the default address for Phonon HQ"""
        return cls(
            street="106, Blue Diamond Complex",
            city="Fatehgunj, Vadodara",
            state="Gujarat",
            zip_code="390002",
            country="India"
        )

# QR Code Design Options
class QRDesignOptions(BaseModel):
    box_size: int = Field(10, gt=0, description="Box size must be positive")
    border: int = Field(4, ge=0, description="Border must be non-negative")
    foreground_color: str = Field("#000000", description="Foreground color in hex format (#RRGGBB)")
    background_color: str = Field("#FFFFFF", description="Background color in hex format (#RRGGBB)")
    eye_color: str = Field("#ff4d26", description="Color for eye patterns in hex format (#RRGGBB)")
    module_color: str = Field("#0f50b5", description="Color for data modules in hex format (#RRGGBB)")
    pattern_style: str = Field("dots", description="Pattern style for QR code")
    eye_style: str = Field("dots", description="Pattern style for eye patterns")
    error_correction: str = Field("Q", description="Error correction level (L, M, Q, H)")
    logo_url: Optional[str] = None  # Make logo optional by default
    logo_size: Optional[float] = Field(0.23, gt=0, lt=1, description="Logo size as a fraction of QR code size (0-1)")
    logo_background: Optional[bool] = True
    logo_round: Optional[bool] = True

    @validator('pattern_style', 'eye_style')
    def validate_pattern_style(cls, v):
        valid_patterns = ['square', 'rounded', 'dots', 'gapped', 'vertical', 'horizontal']
        if v.lower() not in valid_patterns:
            raise ValueError(f"Invalid pattern style. Must be one of: {', '.join(valid_patterns)}")
        return v.lower()

    @validator('error_correction')
    def validate_error_correction(cls, v):
        valid_levels = ['L', 'M', 'Q', 'H']
        if v not in valid_levels:
            raise ValueError(f"Error correction must be one of: {', '.join(valid_levels)}")
        return v

    @validator('foreground_color', 'background_color', 'eye_color', 'module_color')
    def validate_color(cls, v):
        if not re.match(r'^#[0-9A-Fa-f]{6}$', v):
            raise ValueError("Colors must be in hex format (#RRGGBB)")
        return v

    class Config:
        populate_by_name = True

# New QR Code Info class for embedding in VCard
class QRCodeInfo(BaseModel):
    image_url: Optional[str] = None
    design_options: QRDesignOptions = Field(default_factory=QRDesignOptions)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

# Enhanced Analytics structure
class VCardAnalytics(BaseModel):
    total_scans: int = 0
    last_scan: Optional[datetime] = None
    scans: List[Dict] = Field(default_factory=list)
    scans_by_date: Dict[str, int] = Field(default_factory=dict)
    scans_by_device: Dict[str, int] = Field(default_factory=dict)

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

class VCardData(BaseModel):
    """VCard data model aligned with VCard 3.0 format"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    first_name: str
    last_name: str
    email: str
    mobile_number: Optional[str] = None
    work_number: Optional[str] = None
    profile_picture: Optional[str] = None  # URL or Base64
    company: Optional[str] = None
    title: Optional[str] = None
    website: Optional[str] = None
    address: Optional[AddressData] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    user_id: Optional[str] = None

    # New fields for unified structure
    qr_code: Optional[QRCodeInfo] = None
    analytics: VCardAnalytics = Field(default_factory=VCardAnalytics)

    @validator('mobile_number', 'work_number')
    def validate_phone(cls, v):
        if v is None:
            return v
        # Remove any non-digit characters for validation
        digits = ''.join(filter(str.isdigit, v))
        if len(digits) < 10 or len(digits) > 15:
            raise ValueError('Phone number must be between 10 and 15 digits')
        return v

    @validator('website')
    def validate_website(cls, v):
        if v is None:
            return v
        if not v.startswith(('http://', 'https://')):
            v = 'https://' + v
        return v

    @validator('email')
    def validate_email(cls, v):
        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", v):
            raise ValueError('Invalid email format')
        return v

    @validator('profile_picture')
    def validate_profile_picture(cls, v):
        if v is None:
            return v
        if not (v.startswith(('http://', 'https://', 'data:image/'))):
            raise ValueError('Profile picture must be a URL or base64 image data')
        return v

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda dt: dt.isoformat(),
        }

class ScanTrackingEvent(BaseModel):
    vcard_id: str  # Only need vcard_id now
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    success: bool = True
    device_info: Optional[Dict] = None
    headers: Optional[Dict] = None
    action_type: str = "scan"  # Default action type

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

# QR Template for saved designs
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
        populate_by_name = True
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