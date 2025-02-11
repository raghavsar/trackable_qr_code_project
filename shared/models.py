from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime
from bson import ObjectId

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")

class QRDesignOptions(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "foreground_color": "#000000",
                "background_color": "#FFFFFF",
                "pattern_style": "square",
                "eye_style": "square",
                "error_correction": "M",
                "box_size": 10,
                "border": 4,
                "logo_url": None,
                "logo_size": 0.2,
                "logo_background": False,
                "logo_round": False
            }
        }
    )

    foreground_color: str = Field(default="#000000", description="Hex color code for QR code foreground")
    background_color: str = Field(default="#FFFFFF", description="Hex color code for QR code background")
    pattern_style: str = Field(default="square", description="Pattern style: square, rounded, dots, circular, diamond, or special")
    eye_style: str = Field(default="square", description="Eye style: square, circle, rounded, or flower")
    error_correction: str = Field(default="M", description="Error correction level: L, M, Q, or H")
    box_size: int = Field(default=10, description="Size of each QR code box in pixels", ge=1, le=100)
    border: int = Field(default=4, description="Border size in boxes", ge=0, le=10)
    logo_url: Optional[str] = Field(default=None, description="URL of the logo to embed in QR code")
    logo_size: Optional[float] = Field(default=0.2, description="Logo size as fraction of QR code size", ge=0.1, le=0.3)
    logo_background: Optional[bool] = Field(default=False, description="Whether to add white background to logo")
    logo_round: Optional[bool] = Field(default=False, description="Whether to make logo circular")

class QRTemplate(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "name": "Professional Dark",
                "description": "Dark theme with rounded corners",
                "design": {
                    "foreground_color": "#FFFFFF",
                    "background_color": "#000000",
                    "corner_style": "rounded",
                    "error_correction": "H",
                    "box_size": 10,
                    "border": 4
                },
                "category": "vcard",
                "is_public": True,
                "user_id": "user123"
            }
        }
    )

    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    name: str = Field(..., description="Template name")
    description: Optional[str] = Field(default=None, description="Template description")
    design: QRDesignOptions = Field(..., description="QR code design options")
    category: str = Field(default="vcard", description="Template category: vcard, url, text, etc.")
    is_public: bool = Field(default=False, description="Whether the template is public")
    user_id: str = Field(..., description="ID of the user who created the template")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class QRCode(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        populate_by_name=True
    )

    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    user_id: str
    vcard_id: str
    qr_image_url: str
    object_name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    total_scans: int = Field(default=0)
    type: str = Field(default="vcard")
    design: Optional[QRDesignOptions] = None
    template_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict) 