from fastapi import FastAPI, HTTPException, Depends, status, Response
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from typing import List
import os
import logging

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
        
        # Convert ObjectId to string for _id field
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
        
        # Generate VCF content
        vcf_lines = [
            "BEGIN:VCARD",
            "VERSION:3.0",
            f"N:{vcard['last_name']};{vcard['first_name']};;;",
            f"FN:{vcard['first_name']} {vcard['last_name']}"
        ]
        
        # Add optional fields
        if vcard.get('email'):
            vcf_lines.append(f"EMAIL:{vcard['email']}")
        
        if vcard.get('mobile_number'):
            vcf_lines.append(f"TEL;TYPE=CELL:{vcard['mobile_number']}")
        
        if vcard.get('work_number'):
            vcf_lines.append(f"TEL;TYPE=WORK:{vcard['work_number']}")
        
        if vcard.get('company'):
            vcf_lines.append(f"ORG:{vcard['company']}")
        
        if vcard.get('title'):
            vcf_lines.append(f"TITLE:{vcard['title']}")
        
        if vcard.get('website'):
            vcf_lines.append(f"URL:{vcard['website']}")
        
        if vcard.get('profile_picture'):
            vcf_lines.append(f"PHOTO;VALUE=URI:{vcard['profile_picture']}")
        
        # Add address if available
        if vcard.get('address'):
            addr = vcard['address']
            adr_parts = [
                "",  # PO Box
                "",  # Extended Address
                addr.get('street', ''),
                addr.get('city', ''),
                addr.get('state', ''),
                addr.get('zip_code', ''),
                addr.get('country', '')
            ]
            vcf_lines.append(f"ADR;TYPE=WORK:{';'.join(adr_parts)}")
        
        # Add notes if available
        if vcard.get('notes'):
            vcf_lines.append(f"NOTE:{vcard['notes']}")
        
        vcf_lines.append("END:VCARD")
        
        # Join lines with proper line endings
        vcf_content = "\r\n".join(vcf_lines)
        
        # Create response with VCF file
        return Response(
            content=vcf_content,
            media_type="text/vcard",
            headers={
                "Content-Disposition": f'attachment; filename="{vcard["first_name"]}_{vcard["last_name"]}.vcf"',
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