from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, List
from bson import ObjectId
import re

class PyObjectId(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return str(v)

class QRDesignOptions(BaseModel):
    box_size: int = Field(10, gt=0, description="Box size must be positive")
    border: int = Field(4, ge=0, description="Border must be non-negative")
    foreground_color: str = Field("#000000", description="Foreground color in hex format (#RRGGBB)")
    background_color: str = Field("#FFFFFF", description="Background color in hex format (#RRGGBB)")
    eye_color: str = Field("#ff4d26", description="Color for eye patterns in hex format (#RRGGBB)")
    module_color: str = Field("#0f50b5", description="Color for data modules in hex format (#RRGGBB)")
    pattern_style: str = Field("dots", description="Pattern style for QR code")
    error_correction: str = Field("Q", description="Error correction level (L, M, Q, H)")
    logo_url: Optional[str] = None
    logo_size: Optional[float] = Field(0.23, gt=0, lt=1, description="Logo size as a fraction of QR code size (0-1)")
    logo_background: Optional[bool] = True
    logo_round: Optional[bool] = True

    @validator('pattern_style')
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

class QRTemplate(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id")
    user_id: str
    name: str
    description: Optional[str] = None
    design: QRDesignOptions
    created_at: str
    updated_at: str

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class QRCode(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id")
    user_id: str
    vcard_id: Optional[str] = None
    object_name: str
    qr_image_url: str
    created_at: str
    updated_at: str
    total_scans: int = 0
    type: str = "vcard"

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str} 