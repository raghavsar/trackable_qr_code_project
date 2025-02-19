from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Body, UploadFile, File, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient
import qrcode
from qrcode.image.styledpil import StyledPilImage
import io
import base64
from datetime import datetime
import os
from typing import Dict, Optional, List, Any
from bson import ObjectId
import logging
import httpx
from PIL import Image
import requests
from io import BytesIO
import traceback

from shared.models import QRCode, QRTemplate, QRDesignOptions, PyObjectId
from .database import get_database
from .auth import get_current_user
from .storage import MinioStorage, storage_service
from .qr_utils import hex_to_rgb, get_module_drawer, process_logo, generate_vcard_content, CustomEyeDrawer

# Configure logging
logger = logging.getLogger(__name__)

app = FastAPI(
    title="QR Service",
    docs_url="/docs",
    openapi_url="/openapi.json"
)

# Initialize MinIO storage
storage = MinioStorage()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://192.168.7.154:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,  # Cache preflight requests for 1 hour
)

# Database connection
@app.on_event("startup")
async def startup_db_client():
    app.mongodb_client = AsyncIOMotorClient(os.getenv("MONGODB_URL"))
    app.mongodb = app.mongodb_client.get_database()

@app.on_event("shutdown")
async def shutdown_db_client():
    app.mongodb_client.close()

def generate_qr_code(
    data: str,
    design: Optional[QRDesignOptions] = None
) -> io.BytesIO:
    """Generate QR code with custom design options."""
    try:
        if design is None:
            design = QRDesignOptions()

        # Create QR code instance
        qr = qrcode.QRCode(
            version=1,
            error_correction=getattr(qrcode.constants, f"ERROR_CORRECT_{design.error_correction}"),
            box_size=design.box_size,
            border=design.border,
        )
        qr.add_data(data)
        qr.make(fit=True)

        # Convert colors from hex to RGB
        fg_color = hex_to_rgb(design.module_color)  # Use module_color for data patterns
        bg_color = hex_to_rgb(design.background_color)
        eye_color = hex_to_rgb(design.eye_color)

        # Create the QR code image with style
        img = qr.make_image(
            image_factory=StyledPilImage,
            module_drawer=get_module_drawer(design.pattern_style, fg_color),
            color=fg_color,
            back_color=bg_color,
            eye_drawer=CustomEyeDrawer(eye_color)
        )

        # Add logo if specified
        if design.logo_url:
            try:
                # Process logo with background and rounding options
                logo = process_logo(
                    design.logo_url,
                    design.logo_background or False,
                    design.logo_round or False
                )
                
                # Calculate logo size
                qr_width, qr_height = img.size
                logo_size = int(min(qr_width, qr_height) * design.logo_size)
                logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
                
                # Calculate position to center the logo
                box = (
                    (qr_width - logo_size) // 2,
                    (qr_height - logo_size) // 2,
                    (qr_width + logo_size) // 2,
                    (qr_height + logo_size) // 2
                )
                
                # Paste logo onto QR code
                img.paste(logo, box, logo if logo.mode == 'RGBA' else None)
            except Exception as e:
                logger.error(f"Failed to add logo to QR code: {str(e)}")
                # Continue without logo if there's an error

        # Convert to bytes
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        return img_byte_arr
    except Exception as e:
        logger.error(f"Error generating QR code: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate QR code: {str(e)}"
        )

async def notify_analytics(qr_code_id: str, event: str):
    # TODO: Implement analytics notification
    pass

@app.post("/qrcodes")
async def create_qr_code(request: Request, db = Depends(get_database)):
    try:
        logger.info("\n=== Starting QR Code Generation ===")
        # Get request data
        data = await request.json()
        user_id = request.headers.get("X-User-ID")
        logger.info(f"User ID: {user_id}")
        logger.info(f"Request data: {data}")

        if not user_id:
            raise HTTPException(status_code=401, detail="User ID is required")

        # Get vcard data either directly or from database
        vcard_data = {}
        vcard_id = data.get("vcard_id")
        logger.info(f"VCard ID from request: {vcard_id}")
        
        if vcard_id:
            # Get VCard from database
            logger.info(f"Fetching VCard from database: {vcard_id}")
            vcard = await db.vcards.find_one({"_id": PyObjectId(vcard_id)})
            if not vcard:
                logger.error(f"VCard not found: {vcard_id}")
                raise HTTPException(status_code=404, detail="VCard not found")
            vcard_data = vcard
            logger.info(f"Found VCard: {vcard_data.get('first_name')} {vcard_data.get('last_name')}")
        else:
            # Use provided vcard_data
            vcard_data = data.get("vcard_data", {})
            if not vcard_data:
                logger.error("No vcard_data provided")
                raise HTTPException(status_code=400, detail="Either vcard_id or vcard_data is required")
            logger.info("Using provided vcard_data")

        # Get style config
        default_style = {
            "box_size": 10,
            "border": 4,
            "foreground_color": "#000000",
            "background_color": "#FFFFFF",
            "eye_color": "#ff4d26",
            "module_color": "#0f50b5",
            "pattern_style": "dots",
            "error_correction": "Q",
            "logo_url": None,  # Make logo optional
            "logo_size": 0.23,
            "logo_background": True,
            "logo_round": True
        }
        # Merge with provided style config
        style_data = {**default_style, **(data.get("design", data.get("style_config", {})))}
        style_config = QRDesignOptions(**style_data)
        logger.info(f"Style config: {style_config.dict()}")

        # Handle profile photo if present
        if vcard_data.get("profile_picture"):
            logger.info("Processing profile photo")
            photo_url = await storage_service.upload_profile_photo(
                vcard_data["profile_picture"],
                user_id,
                str(vcard_data.get("_id", ""))
            )
            if photo_url:
                logger.info(f"Profile photo uploaded: {photo_url}")
                vcard_data["profile_picture"] = photo_url
            else:
                logger.warning("Failed to upload profile photo")
                del vcard_data["profile_picture"]

        # Generate QR code
        logger.info("Generating QR code")
        qr_code_bytes = await generate_vcard_qr(vcard_data, style_config)
        
        # Get the size of the generated QR code
        qr_code_bytes.seek(0, 2)  # Seek to end
        size = qr_code_bytes.tell()  # Get current position (size)
        qr_code_bytes.seek(0)  # Reset to beginning
        logger.info(f"QR code generated, size: {size} bytes")
        
        # Generate unique object name with user-centric structure
        timestamp = datetime.utcnow().timestamp()
        object_name = f"users/{user_id}/qrcodes/{str(vcard_data.get('_id', ''))}_{timestamp}.png"
        logger.info(f"Object name: {object_name}")
        
        # Upload to MinIO and get URL
        logger.info("Uploading QR code to MinIO")
        qr_image_url = await storage.upload_qr_code(qr_code_bytes, object_name)
        logger.info(f"QR code uploaded, URL: {qr_image_url}")
        
        # Create database record
        qr_code_doc = {
            "vcard_id": str(vcard_data.get("_id", "")),
            "user_id": user_id,
            "object_name": object_name,
            "qr_image_url": qr_image_url,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "total_scans": 0,
            "type": "vcard"
        }
        
        logger.info("Creating database record")
        result = await db.qrcodes.insert_one(qr_code_doc)
        logger.info(f"Database record created, ID: {result.inserted_id}")
        
        # Format response for frontend
        response_data = {
            "id": str(result.inserted_id),
            "tracking_id": str(result.inserted_id),
            "qr_image": base64.b64encode(qr_code_bytes.getvalue()).decode('utf-8'),
            "qr_image_url": qr_image_url,
            "created_at": qr_code_doc["created_at"].isoformat(),
            "type": "vcard",
            "total_scans": 0,
            "metadata": {
                "vcard_id": str(vcard_data.get("_id", "")),
                "vcard_name": f"{vcard_data.get('first_name', '')} {vcard_data.get('last_name', '')}"
            }
        }
        
        logger.info("=== QR Code Generation Complete ===")
        return JSONResponse(content=response_data)
    except Exception as e:
        logger.error("\n=== QR Code Generation Failed ===")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error("Full error details:", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate QR code: {str(e)}")

@app.get("/qrcodes")
async def list_qr_codes(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get all QR codes for the current user"""
    try:
        logger.info(f"Fetching QR codes for user: {current_user['id']}")
        
        # Get QR codes for the user
        qr_codes = await db.qrcodes.find({
            "user_id": current_user["id"]
        }).sort("created_at", -1).to_list(None)
        
        logger.info(f"Found {len(qr_codes)} QR codes")
        
        # Format response
        formatted_qr_codes = []
        for qr in qr_codes:
            # Get associated VCard details
            vcard = await db.vcards.find_one({"_id": PyObjectId(qr["vcard_id"])})
            
            formatted_qr = {
                "id": str(qr["_id"]),
                "tracking_id": str(qr["_id"]),
                "qr_image": qr.get("qr_image", ""),
                "qr_image_url": qr.get("qr_image_url", ""),
                "created_at": qr["created_at"].isoformat(),
                "type": qr.get("type", "vcard"),
                "total_scans": qr.get("total_scans", 0),
                "metadata": {
                    "vcard_id": qr.get("vcard_id"),
                    "vcard_name": f"{vcard['first_name']} {vcard['last_name']}" if vcard else None
                }
            }
            formatted_qr_codes.append(formatted_qr)
        
        return formatted_qr_codes
    except Exception as e:
        logger.error(f"Failed to fetch QR codes: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch QR codes: {str(e)}"
        )

@app.get("/qrcodes/{qr_id}")
async def get_qr_code(
    qr_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    try:
        # Get QR code and verify ownership
        qr_code = await db.qrcodes.find_one({
            "_id": PyObjectId(qr_id),
            "user_id": current_user["id"]
        })
        if not qr_code:
            raise HTTPException(status_code=404, detail="QR code not found")
        
        # Format response
        qr_code["_id"] = str(qr_code["_id"])
        return qr_code
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch QR code: {str(e)}"
        )

@app.put("/qrcodes/{qr_id}")
async def update_qr_code(
    qr_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database),
    data: Dict[str, Any] = Body(...)
):
    try:
        # Verify ownership before update
        old_qr_code = await db.qrcodes.find_one({
            "_id": PyObjectId(qr_id),
            "user_id": current_user["id"]
        })
        if not old_qr_code:
            raise HTTPException(status_code=404, detail="QR code not found")
        
        # Store old VCard ID for deletion
        old_vcard_id = old_qr_code.get("vcard_id")
        logger.info(f"Old VCard ID to be deleted: {old_vcard_id}")
        
        # Get design options
        design = None
        if "design" in data:
            design = QRDesignOptions(**data["design"])
        elif "template_id" in data:
            template = await db.templates.find_one({
                "_id": PyObjectId(data["template_id"]),
                "$or": [
                    {"user_id": current_user["id"]},
                    {"is_public": True}
                ]
            })
            if template:
                design = QRDesignOptions(**template["design"])

        # Generate new QR code with design
        vcard_url = f"{os.getenv('FRONTEND_URL')}/r/{data['vcard_id']}"
        qr_image = generate_qr_code(vcard_url, design)
        
        # Generate unique object name with user-centric structure
        timestamp = datetime.utcnow().timestamp()
        object_name = f"users/{current_user['id']}/qrcodes/{data['vcard_id']}_{timestamp}.png"
        
        # Upload to MinIO and get public URL
        qr_image_url = await storage.upload_qr_code(qr_image, object_name)
        
        # Delete old image from MinIO if exists
        if "object_name" in old_qr_code:
            try:
                await storage.delete_qr_code(old_qr_code["object_name"])
                logger.info(f"Successfully deleted old QR code image: {old_qr_code['object_name']}")
            except Exception as e:
                logger.error(f"Failed to delete old QR code from storage: {str(e)}")
        
        # Update database record
        update_data = {
            "vcard_id": data["vcard_id"],
            "qr_image_url": qr_image_url,
            "object_name": object_name,
            "updated_at": datetime.utcnow()
        }
        
        await db.qrcodes.update_one(
            {"_id": PyObjectId(qr_id)},
            {"$set": update_data}
        )
        
        # Delete old VCard if it exists and is different from the new one
        if old_vcard_id and old_vcard_id != data["vcard_id"]:
            try:
                # Delete old VCard using VCard service
                async with httpx.AsyncClient() as client:
                    headers = {"Authorization": f"Bearer {current_user.get('token')}"}
                    vcard_service_url = os.getenv("VCARD_SERVICE_URL", "http://vcard-service:8002")
                    response = await client.delete(
                        f"{vcard_service_url}/vcards/{old_vcard_id}",
                        headers=headers
                    )
                    if response.status_code == 200:
                        logger.info(f"Successfully deleted old VCard: {old_vcard_id}")
                    else:
                        logger.error(f"Failed to delete old VCard: {old_vcard_id}, status: {response.status_code}")
            except Exception as e:
                logger.error(f"Error deleting old VCard: {str(e)}")
        
        # Get updated QR code
        updated_qr = await db.qrcodes.find_one({"_id": PyObjectId(qr_id)})
        
        # Get base64 for immediate display
        qr_image.seek(0)
        base64_image = base64.b64encode(qr_image.read()).decode()
        
        # Format response
        response = {
            "id": str(updated_qr["_id"]),
            "tracking_id": str(updated_qr["_id"]),
            "qr_image": base64_image,
            "qr_image_url": qr_image_url,
            "created_at": updated_qr["created_at"].isoformat(),
            "updated_at": updated_qr["updated_at"].isoformat(),
            "type": "vcard",
            "total_scans": updated_qr.get("total_scans", 0),
            "metadata": {
                "vcard_id": data["vcard_id"]
            }
        }
        
        background_tasks.add_task(notify_analytics, qr_id, "updated")
        return response
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update QR code: {str(e)}"
        )

@app.delete("/qrcodes/{qr_id}")
async def delete_qr_code(
    qr_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    try:
        # Verify ownership before deletion
        qr_code = await db.qrcodes.find_one({
            "_id": PyObjectId(qr_id),
            "user_id": current_user["id"]
        })
        if not qr_code:
            raise HTTPException(status_code=404, detail="QR code not found")
        
        # Delete from MinIO if object_name exists
        if "object_name" in qr_code:
            try:
                await storage.delete_qr_code(qr_code["object_name"])
            except Exception as e:
                logger.error(f"Failed to delete QR code from storage: {str(e)}")
                # Continue with database deletion even if storage deletion fails
        
        # Delete from database
        await db.qrcodes.delete_one({"_id": PyObjectId(qr_id)})
        background_tasks.add_task(notify_analytics, qr_id, "deleted")
        return {"message": "QR code deleted successfully"}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete QR code: {str(e)}"
        )

@app.get("/qrcodes/preview")
async def preview_qr_code_get(
    vcard_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Generate a preview of a QR code for GET requests."""
    try:
        if not vcard_id:
            raise HTTPException(status_code=400, detail="vcard_id is required")

        # Verify VCard ownership
        vcard = await db.vcards.find_one({
            "_id": PyObjectId(vcard_id),
            "user_id": current_user["id"]
        })
        if not vcard:
            raise HTTPException(status_code=404, detail="VCard not found")

        # Generate QR code with direct vCard data
        qr_image_bytes = await generate_vcard_qr(vcard, QRDesignOptions())
        qr_image = BytesIO(qr_image_bytes)
        
        # Convert to base64
        qr_image.seek(0)
        base64_image = base64.b64encode(qr_image.read()).decode()
        
        return {
            "preview_url": f"data:image/png;base64,{base64_image}"
        }
        
    except Exception as e:
        logger.error(f"Error generating QR code preview: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate QR code preview: {str(e)}"
        )

@app.post("/qrcodes/preview")
async def preview_qr_code_post(
    data: Dict[str, Any] = Body(...),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    try:
        # Get vcard data
        vcard_data = data.get("vcard_data", {})
        if not vcard_data:
            raise HTTPException(status_code=400, detail="vcard_data is required")

        # Get style config with defaults
        default_style = {
            "box_size": 10,
            "border": 4,
            "foreground_color": "#000000",
            "background_color": "#FFFFFF",
            "eye_color": "#ff4d26",
            "module_color": "#0f50b5",
            "pattern_style": "dots",
            "error_correction": "Q",
            "logo_url": "/assets/images/phonon-favicon.png",
            "logo_size": 0.23,
            "logo_background": True,
            "logo_round": True
        }
        # Merge with provided style config
        style_data = {**default_style, **(data.get("design_options", {}))}
        style_config = QRDesignOptions(**style_data)

        # Generate QR code
        qr_code_bytes = await generate_vcard_qr(vcard_data, style_config)
        
        # Convert to base64
        base64_qr = base64.b64encode(qr_code_bytes).decode('utf-8')
        return {"qr_image_base64": f"data:image/png;base64,{base64_qr}"}

    except Exception as e:
        logger.error("\n=== QR Code Preview Failed ===")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error("Full error details:")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/qrcodes/vcard/{vcard_id}")
async def get_qr_code_by_vcard(
    vcard_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    qr_code = await db.qrcodes.find_one({
        "vcard_id": vcard_id,
        "user_id": current_user["id"]
    })
    if not qr_code:
        raise HTTPException(status_code=404, detail="QR code not found")
    qr_code["_id"] = str(qr_code["_id"])
    return qr_code

@app.post("/qrcodes/upload-logo")
async def upload_logo(
    logo: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload a logo for QR code."""
    try:
        user_id = current_user.get("id")
        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="User ID not found in token"
            )

        # Validate file size
        contents = await logo.read()
        if len(contents) > 1024 * 1024:  # 1MB limit
            raise HTTPException(
                status_code=400,
                detail="Logo file size must be less than 1MB"
            )

        # Validate file type
        if logo.content_type not in ["image/jpeg", "image/png"]:
            raise HTTPException(
                status_code=400,
                detail="Only JPEG and PNG files are allowed"
            )

        # Generate unique filename
        timestamp = datetime.utcnow().timestamp()
        filename = f"users/{user_id}/logos/{timestamp}_{logo.filename}"

        # Upload to MinIO
        logo_url = await storage.upload_file(contents, filename, logo.content_type)

        return JSONResponse({
            "logo_url": logo_url
        })

    except Exception as e:
        logger.error(f"Error uploading logo: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload logo: {str(e)}"
        )

@app.post("/qr/generate/{vcard_id}")
async def generate_qr(
    vcard_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    try:
        user_id = current_user.get("id")
        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="User ID not found in token"
            )

        # Verify VCard ownership first
        vcard = await db.vcards.find_one({
            "_id": PyObjectId(vcard_id),
            "user_id": user_id
        })
        if not vcard:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to access this VCard"
            )

        # Generate QR code with direct vCard data
        qr_image_bytes = await generate_vcard_qr(vcard, QRDesignOptions())
        qr_image = BytesIO(qr_image_bytes)

        # Generate unique object name with user-centric structure
        timestamp = datetime.utcnow().timestamp()
        object_name = f"users/{user_id}/qrcodes/{vcard_id}_{timestamp}.png"

        # Upload to MinIO and get URL
        qr_code_url = await storage.upload_qr_code(qr_image, object_name)

        # Save QR code information to database
        qr_code_doc = {
            "vcard_id": vcard_id,
            "user_id": user_id,
            "object_name": object_name,
            "url": qr_code_url,
            "created_at": datetime.utcnow(),
            "total_scans": 0,
            "type": "vcard"
        }
        
        result = await db.qrcodes.insert_one(qr_code_doc)
        
        return {
            "qr_code_url": qr_code_url,
            "vcard_id": vcard_id,
            "user_id": user_id,
            "id": str(result.inserted_id)
        }
        
    except Exception as e:
        logger.error(f"Error generating QR code: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating QR code: {str(e)}"
        )

@app.get("/qr/{vcard_id}")
async def get_qr(
    vcard_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    try:
        # Find QR code in database
        qr_code = await db.qrcodes.find_one({
            "vcard_id": vcard_id,
            "user_id": current_user["id"]
        })
        
        if not qr_code:
            raise HTTPException(status_code=404, detail="QR code not found")
            
        # Get fresh URL (in case the old one expired)
        fresh_url = await storage.get_qr_code_url(qr_code["object_name"])
        
        return {
            "qr_code_url": fresh_url,
            "vcard_id": vcard_id,
            "total_scans": qr_code.get("total_scans", 0)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving QR code: {str(e)}"
        )

@app.delete("/qr/{vcard_id}")
async def delete_qr(
    vcard_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    try:
        # Find QR code in database
        qr_code = await db.qrcodes.find_one({
            "vcard_id": vcard_id,
            "user_id": current_user["id"]
        })
        
        if not qr_code:
            raise HTTPException(status_code=404, detail="QR code not found")
            
        # Delete from MinIO
        await storage.delete_qr_code(qr_code["object_name"])
        
        # Delete from database
        await db.qrcodes.delete_one({
            "vcard_id": vcard_id,
            "user_id": current_user["id"]
        })
        
        return {"message": "QR code deleted successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting QR code: {str(e)}"
        )

# Template endpoints
@app.post("/templates")
async def create_template(
    template: QRTemplate,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Create a new QR code template."""
    try:
        template.user_id = current_user["id"]
        template_dict = template.dict(exclude={"id"})
        
        # Insert template
        result = await db.templates.insert_one(template_dict)
        
        # Get created template
        created_template = await db.templates.find_one({"_id": result.inserted_id})
        created_template["_id"] = str(created_template["_id"])
        
        return created_template
    except Exception as e:
        logger.error(f"Failed to create template: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create template: {str(e)}"
        )

@app.get("/templates")
async def list_templates(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """List available templates (user's own templates and public templates)."""
    try:
        # Get user's templates and public templates
        templates = await db.templates.find({
            "$or": [
                {"user_id": current_user["id"]},
                {"is_public": True}
            ]
        }).to_list(None)
        
        # Convert ObjectIds to strings
        for template in templates:
            template["_id"] = str(template["_id"])
        
        return templates
    except Exception as e:
        logger.error(f"Failed to fetch templates: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch templates: {str(e)}"
        )

@app.get("/templates/{template_id}")
async def get_template(
    template_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get a specific template."""
    try:
        template = await db.templates.find_one({
            "_id": PyObjectId(template_id),
            "$or": [
                {"user_id": current_user["id"]},
                {"is_public": True}
            ]
        })
        
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        template["_id"] = str(template["_id"])
        return template
    except Exception as e:
        logger.error(f"Failed to fetch template: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch template: {str(e)}"
        )

@app.put("/templates/{template_id}")
async def update_template(
    template_id: str,
    template_update: QRTemplate,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Update a template."""
    try:
        # Verify ownership
        existing_template = await db.templates.find_one({
            "_id": PyObjectId(template_id),
            "user_id": current_user["id"]
        })
        
        if not existing_template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        # Update template
        update_data = template_update.dict(exclude={"id", "user_id"})
        update_data["updated_at"] = datetime.utcnow()
        
        await db.templates.update_one(
            {"_id": PyObjectId(template_id)},
            {"$set": update_data}
        )
        
        # Get updated template
        updated_template = await db.templates.find_one({"_id": PyObjectId(template_id)})
        updated_template["_id"] = str(updated_template["_id"])
        
        return updated_template
    except Exception as e:
        logger.error(f"Failed to update template: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update template: {str(e)}"
        )

@app.delete("/templates/{template_id}")
async def delete_template(
    template_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Delete a template."""
    try:
        # Verify ownership
        result = await db.templates.delete_one({
            "_id": PyObjectId(template_id),
            "user_id": current_user["id"]
        })
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Template not found")
        
        return {"message": "Template deleted successfully"}
    except Exception as e:
        logger.error(f"Failed to delete template: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete template: {str(e)}"
        )

async def generate_vcard_qr(
    vcard_data: dict,
    design: Optional[QRDesignOptions] = None
) -> io.BytesIO:
    """Generate QR code with custom design options."""
    try:
        if design is None:
            design = QRDesignOptions()

        # Get the frontend URL from environment
        frontend_url = os.getenv('FRONTEND_URL', 'http://192.168.7.154:5173')
        
        # Create the frontend URL for redirection
        redirect_url = f"{frontend_url}/r/{str(vcard_data.get('_id', ''))}"
        logger.info(f"Generated frontend redirect URL: {redirect_url}")

        # Create QR code instance
        qr = qrcode.QRCode(
            version=1,
            error_correction=getattr(qrcode.constants, f"ERROR_CORRECT_{design.error_correction}"),
            box_size=design.box_size,
            border=design.border,
        )
        
        # Add the redirect URL to QR code
        qr.add_data(redirect_url)
        qr.make(fit=True)

        # Convert colors from hex to RGB
        fg_color = hex_to_rgb(design.module_color)  # Use module_color for data patterns
        bg_color = hex_to_rgb(design.background_color)
        eye_color = hex_to_rgb(design.eye_color)

        # Create the QR code image with style
        img = qr.make_image(
            image_factory=StyledPilImage,
            module_drawer=get_module_drawer(design.pattern_style, fg_color),
            color=fg_color,
            back_color=bg_color,
            eye_drawer=CustomEyeDrawer(eye_color)
        )

        # Add logo if specified
        if design.logo_url:
            try:
                # Process logo with background and rounding options
                logo = process_logo(
                    design.logo_url,
                    design.logo_background or False,
                    design.logo_round or False
                )
                
                # Calculate logo size
                qr_width, qr_height = img.size
                logo_size = int(min(qr_width, qr_height) * design.logo_size)
                logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
                
                # Calculate position to center the logo
                box = (
                    (qr_width - logo_size) // 2,
                    (qr_height - logo_size) // 2,
                    (qr_width + logo_size) // 2,
                    (qr_height + logo_size) // 2
                )
                
                # Paste logo onto QR code
                img.paste(logo, box, logo if logo.mode == 'RGBA' else None)
            except Exception as e:
                logger.error(f"Failed to add logo to QR code: {str(e)}")
                # Continue without logo if there's an error

        # Convert to bytes
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        return img_byte_arr
    except Exception as e:
        logger.error(f"Error generating QR code: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate QR code: {str(e)}"
        ) 