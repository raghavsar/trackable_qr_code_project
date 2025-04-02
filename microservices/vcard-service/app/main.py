from fastapi import FastAPI, HTTPException, Depends, status, Response
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from typing import List
import os
import logging
import httpx

from shared.models import VCardData, PyObjectId
from .database import get_database
from .auth import get_current_user

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="VCard Service")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection
@app.on_event("startup")
async def startup_db_client():
    app.mongodb_client = AsyncIOMotorClient(os.getenv("MONGODB_URL"))
    app.mongodb = app.mongodb_client.get_database()

@app.on_event("shutdown")
async def shutdown_db_client():
    app.mongodb_client.close()

# Health check endpoint
@app.get("/health")
async def health_check():
    try:
        await app.mongodb.command("ping")
        return {
            "status": "healthy",
            "service": "vcard-service",
            "database": "connected"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "service": "vcard-service",
            "error": str(e)
        }

# Routes
@app.post("/vcards")
async def create_vcard(
    vcard: VCardData,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    try:
        logger.info("Received create VCard request")
        logger.info(f"User ID: {current_user.get('id')}")
        logger.info(f"VCard data: {vcard.dict(exclude={'id'})}")
        
        vcard_dict = vcard.dict(exclude={'id'})
        vcard_dict["user_id"] = current_user["id"]
        vcard_dict["created_at"] = datetime.utcnow()
        vcard_dict["updated_at"] = vcard_dict["created_at"]
        
        # Initialize QR code and analytics fields
        vcard_dict["qr_code"] = None  # Will be populated by QR service
        vcard_dict["analytics"] = {
            "total_scans": 0,
            "scans": [],
            "scans_by_date": {},
            "scans_by_device": {}
        }
        
        # Validate required fields
        if not vcard_dict.get("first_name") or not vcard_dict.get("last_name"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="First name and last name are required"
            )
        
        result = await db.vcards.insert_one(vcard_dict)
        created_vcard = await db.vcards.find_one({"_id": result.inserted_id})
        
        if not created_vcard:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create VCard"
            )
            
        logger.info(f"Successfully created VCard with ID: {result.inserted_id}")
        
        # Generate QR code for the newly created VCard
        try:
            # Get QR service URL from environment
            qr_service_url = os.getenv("QR_SERVICE_URL", "http://qr-service:8000")
            
            # Prepare request to QR service
            qr_request_url = f"{qr_service_url}/qr/generate/{str(result.inserted_id)}"
            
            # Forward the user's token for authentication
            headers = {"Authorization": f"Bearer {current_user.get('token', '')}"}
            
            # Make async request to QR service
            async with httpx.AsyncClient(timeout=30.0) as client:
                qr_response = await client.post(qr_request_url, headers=headers)
                
                if qr_response.status_code == 200:
                    qr_data = qr_response.json()
                    logger.info(f"QR code generated successfully: {qr_data.get('qr_code_url')}")
                else:
                    logger.warning(f"Failed to generate QR code: {qr_response.text}")
        except Exception as qr_error:
            # Log error but don't fail the VCard creation
            logger.error(f"Error generating QR code: {str(qr_error)}")
        
        # Get the updated VCard with QR code info
        updated_vcard = await db.vcards.find_one({"_id": result.inserted_id})
        if updated_vcard:
            # Convert ObjectId to string for _id field
            updated_vcard["_id"] = str(updated_vcard["_id"])
            return updated_vcard
        else:
            # If we can't get the updated VCard, return the original one
            created_vcard["_id"] = str(created_vcard["_id"])
            return created_vcard
        
    except Exception as e:
        logger.error(f"Error creating VCard: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@app.get("/vcards")
async def list_vcards(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    try:
        vcards = await db.vcards.find(
            {"user_id": current_user["id"]}
        ).sort("created_at", -1).to_list(None)
        
        # Convert ObjectIds to strings
        for vcard in vcards:
            vcard["_id"] = str(vcard["_id"])
        
        return vcards
    except Exception as e:
        logger.error(f"Error fetching VCards: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch VCards: {str(e)}"
        )

@app.get("/vcards/{vcard_id}")
async def get_vcard(
    vcard_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    try:
        logger.info(f"Fetching VCard {vcard_id} for user: {current_user['id']}")
        
        try:
            object_id = PyObjectId(vcard_id)
            logger.info(f"Successfully converted VCard ID to ObjectId: {object_id}")
        except Exception as e:
            logger.error(f"Invalid VCard ID format: {vcard_id}, error: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail="Invalid VCard ID format"
            )
        
        vcard = await db.vcards.find_one({
            "_id": object_id,
            "user_id": current_user["id"]
        })
        
        if not vcard:
            logger.error(f"VCard not found with ID {vcard_id} for user {current_user['id']}")
            raise HTTPException(status_code=404, detail="VCard not found")
        
        logger.info(f"Found VCard: {vcard}")
        vcard["_id"] = str(vcard["_id"])
        return vcard
        
    except Exception as e:
        logger.error(f"Error fetching VCard: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch VCard: {str(e)}"
        )

@app.put("/vcards/{vcard_id}")
async def update_vcard(
    vcard_id: str,
    vcard_update: VCardData,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    try:
        logger.info(f"Updating VCard {vcard_id} for user: {current_user['id']}")
        
        try:
            object_id = PyObjectId(vcard_id)
            logger.info(f"Converted VCard ID to ObjectId: {object_id}")
        except Exception as e:
            logger.error(f"Failed to convert VCard ID to ObjectId: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid VCard ID format")
        
        # Verify ownership
        vcard = await db.vcards.find_one({
            "_id": object_id,
            "user_id": current_user["id"]
        })
        
        if not vcard:
            logger.error(f"VCard not found with ID {vcard_id} for user {current_user['id']}")
            raise HTTPException(status_code=404, detail="VCard not found")
        
        logger.info(f"Found VCard: {vcard}")
        
        # Prepare update data
        update_dict = {
            "first_name": vcard_update.first_name,
            "last_name": vcard_update.last_name,
            "email": vcard_update.email,
            "updated_at": datetime.utcnow()
        }
        
        # Add optional fields if they exist
        if vcard_update.mobile_number is not None:
            update_dict["mobile_number"] = vcard_update.mobile_number
        if vcard_update.work_number is not None:
            update_dict["work_number"] = vcard_update.work_number
        if vcard_update.profile_picture is not None:
            update_dict["profile_picture"] = vcard_update.profile_picture
        if vcard_update.company is not None:
            update_dict["company"] = vcard_update.company
        if vcard_update.title is not None:
            update_dict["title"] = vcard_update.title
        if vcard_update.website is not None:
            update_dict["website"] = vcard_update.website
        if vcard_update.notes is not None:
            update_dict["notes"] = vcard_update.notes
        if vcard_update.address:
            update_dict["address"] = vcard_update.address.dict(exclude_none=True)
        
        logger.info(f"Updating VCard with data: {update_dict}")
        
        # Update in database
        result = await db.vcards.update_one(
            {"_id": object_id},
            {"$set": update_dict}
        )
        
        if result.modified_count == 0:
            logger.warning("No changes detected in update operation")
            raise HTTPException(
                status_code=400,
                detail="VCard was not updated. No changes detected."
            )
        
        # Get updated VCard
        updated_vcard = await db.vcards.find_one({"_id": object_id})
        if not updated_vcard:
            logger.error("Failed to fetch updated VCard after successful update")
            raise HTTPException(
                status_code=500,
                detail="Failed to fetch updated VCard"
            )
        
        # Convert ObjectId to string
        updated_vcard["_id"] = str(updated_vcard["_id"])
        logger.info(f"Successfully updated VCard: {updated_vcard}")
        return updated_vcard
        
    except Exception as e:
        logger.error(f"Error updating VCard: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=500,
            detail=f"Error updating VCard: {str(e)}"
        )

@app.delete("/vcards/{vcard_id}")
async def delete_vcard(
    vcard_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    try:
        logger.info(f"Deleting VCard {vcard_id} for user: {current_user['id']}")
        vcard = await db.vcards.find_one({
            "_id": PyObjectId(vcard_id),
            "user_id": current_user["id"]
        })
        if not vcard:
            raise HTTPException(status_code=404, detail="VCard not found")
        
        await db.vcards.delete_one({"_id": PyObjectId(vcard_id)})
        logger.info(f"Successfully deleted VCard {vcard_id}")
        return {"message": "VCard deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting VCard: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting VCard: {str(e)}"
        )

@app.get("/vcards/{vcard_id}/download")
async def download_vcard(
    vcard_id: str,
    db = Depends(get_database)
):
    try:
        logger.info(f"Generating VCF download for VCard: {vcard_id}")
        
        # Get VCard data
        vcard = await db.vcards.find_one({"_id": PyObjectId(vcard_id)})
        if not vcard:
            raise HTTPException(status_code=404, detail="VCard not found")
        
        logger.info(f"Retrieved VCard data: {vcard}")
        
        # Ensure all values are strings and handle None values
        first_name = str(vcard.get('first_name', '')) if vcard.get('first_name') else ''
        last_name = str(vcard.get('last_name', '')) if vcard.get('last_name') else ''
        
        # Generate VCF content with safe string handling
        vcf_lines = [
            "BEGIN:VCARD",
            "VERSION:3.0",
            f"N:{last_name};{first_name};;;",
            f"FN:{first_name} {last_name}"
        ]
        
        # Add profile photo with proper type
        if vcard.get('profile_picture'):
            vcf_lines.append(f"PHOTO;VALUE=URI:{str(vcard['profile_picture'])}")
        
        # Add email with work type label (removed INTERNET type)
        if vcard.get('email'):
            vcf_lines.append(f"EMAIL;TYPE=INTERNET:{str(vcard['email'])}")
        
        # Add phone numbers with proper types
        if vcard.get('mobile_number'):
            vcf_lines.append(f"TEL;TYPE=CELL,VOICE:{str(vcard['mobile_number'])}")
        
        if vcard.get('work_number'):
            vcf_lines.append(f"TEL;TYPE=WORK,VOICE:{str(vcard['work_number'])}")
        
        # Add company and title
        if vcard.get('company'):
            vcf_lines.append(f"ORG:{str(vcard['company'])}")
        
        if vcard.get('title'):
            vcf_lines.append(f"TITLE:{str(vcard['title'])}")
        
        # Add website as primary URL (without TYPE=WORK)
        if vcard.get('website'):
            vcf_lines.append(f"URL:{str(vcard['website'])}")
        
        # Add home address from user form data if available
        if vcard.get('address'):
            addr = vcard['address']
            
            # Get home address components
            street = addr.get('street', '')
            city = addr.get('city', '')
            state = addr.get('state', '')
            zip_code = addr.get('zip_code', '')
            country = addr.get('country', '')
            
            # Only add if any address component exists
            if any([street, city, state, zip_code, country]):
                # Create home address with proper format
                home_adr_parts = [
                    "",  # PO Box
                    "",  # Extended Address
                    street,
                    city,
                    state,
                    zip_code,
                    country
                ]
                
                # Add home address with proper type
                vcf_lines.append(f"ADR;TYPE=HOME:{';'.join(home_adr_parts)}")
                
                # Add formatted address label for home
                home_formatted = ", ".join(filter(None, [street, city, state, zip_code, country]))
                if home_formatted:
                    vcf_lines.append(f"LABEL;TYPE=HOME:{home_formatted}")
        
        # Add work address with physical address and Google Maps URL in notes
        work_address = "106, Blue Diamond Complex, next to Indian Oil Petrol Pump, Fatehgunj, Vadodara, Gujarat 390002"
        work_map_url = "https://maps.app.goo.gl/99bjahgR1SJdWXbb7"
        
        # Add work address
        vcf_lines.append("ADR;TYPE=WORK:;;106, Blue Diamond Complex;Fatehgunj;Vadodara;390002;Gujarat, India")
        vcf_lines.append(f"LABEL;TYPE=WORK:{work_address}")
        
        # Add notes without map URL
        notes_content = vcard.get('notes', '')
        if notes_content:
            # Escape special characters according to vCard spec
            notes = str(notes_content).replace('\n', '\\n').replace('\r', '')
            vcf_lines.append(f"NOTE:{notes}")
        
        # Add revision timestamp
        vcf_lines.extend([
            f"REV:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}",
            "END:VCARD"
        ])
        
        # Join lines with proper line endings
        vcf_content = "\r\n".join(vcf_lines)
        logger.info(f"Generated VCF content: {vcf_content}")
        
        # Create response with VCF file
        filename = f"{first_name}_{last_name}.vcf".replace(' ', '_')
        return Response(
            content=vcf_content.encode('utf-8'),
            media_type="text/vcard",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Type": "text/vcard",
                "Cache-Control": "no-cache"
            }
        )
        
    except Exception as e:
        logger.error(f"Error generating VCF: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=500,
            detail=f"Error generating VCF: {str(e)}"
        )

@app.get("/vcards/public/{vcard_id}")
async def get_public_vcard(
    vcard_id: str,
    db = Depends(get_database)
):
    try:
        logger.info(f"Fetching public VCard {vcard_id}")
        
        try:
            object_id = PyObjectId(vcard_id)
            logger.info(f"Successfully converted VCard ID to ObjectId: {object_id}")
        except Exception as e:
            logger.error(f"Invalid VCard ID format: {vcard_id}, error: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail="Invalid VCard ID format"
            )
        
        vcard = await db.vcards.find_one({"_id": object_id})
        
        if not vcard:
            logger.error(f"VCard not found with ID {vcard_id}")
            raise HTTPException(status_code=404, detail="VCard not found")
        
        logger.info(f"Found VCard: {vcard}")
        vcard["_id"] = str(vcard["_id"])
        return vcard
        
    except Exception as e:
        logger.error(f"Error fetching VCard: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch VCard: {str(e)}"
        ) 