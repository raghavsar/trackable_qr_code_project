from fastapi import FastAPI, HTTPException, Depends, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, Response
from motor.motor_asyncio import AsyncIOMotorClient
import httpx
import os
from urllib.parse import urlencode
from user_agents import parse
import vobject
from datetime import datetime
import logging
import traceback
import json
import uuid

from shared.models import PyObjectId
from .database import get_database

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = FastAPI(title="Redirect Service")

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
    app.http_client = httpx.AsyncClient()

@app.on_event("shutdown")
async def shutdown_db_client():
    app.mongodb_client.close()
    await app.http_client.aclose()

def get_device_info(user_agent_string: str):
    """Parse user agent string to get device information"""
    user_agent = parse(user_agent_string)
    return {
        "is_mobile": user_agent.is_mobile,
        "is_tablet": user_agent.is_tablet,
        "is_pc": user_agent.is_pc,
        "browser": user_agent.browser.family,
        "os": user_agent.os.family,
        "device": user_agent.device.family
    }

def generate_vcard(vcard_data: dict) -> bytes:
    """Generate .vcf file content using VCard 3.0 format for better compatibility"""
    vcard_lines = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        f"N:{vcard_data['last_name']};{vcard_data['first_name']};;;",
        f"FN:{vcard_data['first_name']} {vcard_data['last_name']}"
    ]
    
    # Add profile photo if exists
    if vcard_data.get('profile_picture'):
        vcard_lines.append(f"PHOTO;VALUE=URI:{vcard_data['profile_picture']}")
    
    # Add phone numbers with proper TYPE parameters
    if vcard_data.get('mobile_number'):
        vcard_lines.append(f"TEL;TYPE=CELL,VOICE:{vcard_data['mobile_number']}")
    if vcard_data.get('work_number'):
        vcard_lines.append(f"TEL;TYPE=WORK,VOICE:{vcard_data['work_number']}")
    
    # Add email with proper TYPE parameter - just "TYPE=WORK" to display as "Email"
    if vcard_data.get('email'):
        vcard_lines.append(f"EMAIL;TYPE=INTERNET:{vcard_data['email']}")
    
    # Add organization and title
    if vcard_data.get('company'):
        vcard_lines.append(f"ORG:{vcard_data['company']}")
    if vcard_data.get('title'):
        vcard_lines.append(f"TITLE:{vcard_data['title']}")
    
    # Add website as primary URL (only if provided)
    if vcard_data.get('website'):
        vcard_lines.append(f"URL:{vcard_data['website']}")
    
    # Add home address from user's form data if available
    if vcard_data.get('address'):
        addr = vcard_data['address']
        
        # Get home address components
        street = addr.get('street', '')
        city = addr.get('city', '')
        state = addr.get('state', '')
        zip_code = addr.get('zip_code', '')
        country = addr.get('country', '')
        
        # Only add if any address component exists
        if any([street, city, state, zip_code, country]):
            # Create ADR property with HOME type
            adr_parts = [
                "",  # Post office box
                "",  # Extended address
                street,
                city,
                state,
                zip_code,
                country
            ]
            vcard_lines.append(f"ADR;TYPE=WORK:{';'.join(adr_parts)}")

            # Add formatted address label
            formatted_address = ", ".join(filter(None, [street, city, state, zip_code, country]))
            vcard_lines.append(f"LABEL;TYPE=WORK:{formatted_address}")

    # Add notes without map URL
    notes_content = vcard_data.get('notes', '')
    if notes_content:
        # Escape special characters
        notes = notes_content.replace('\n', '\\n').replace('\r', '')
        vcard_lines.append(f"NOTE:{notes}")
    
    # Add revision timestamp
    vcard_lines.append(f"REV:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}")
    
    vcard_lines.append("END:VCARD")
    
    return "\r\n".join(vcard_lines).encode('utf-8')

def get_platform_specific_url(vcard_data: dict, device_info: dict) -> str:
    """Generate platform-specific deep links with enhanced logging"""
    logger.info(f"Generating platform-specific URL. Device info: {device_info}")
    
    # Get base URL with fallback
    base_url = os.getenv('FRONTEND_URL', 'http://localhost:3000').rstrip('/')
    
    # Generate VCF content first
    vcf_content = generate_vcard(vcard_data)
    
    if device_info["is_mobile"]:
        logger.info(f"Processing mobile device. OS: {device_info['os']}, Browser: {device_info['browser']}")
        
        # For both iOS and Android, we'll return the VCF content directly
        # This should trigger the native contacts import
        return Response(
            content=vcf_content,
            media_type="text/vcard",
            headers={
                "Content-Disposition": f'attachment; filename="{vcard_data["first_name"]}_{vcard_data["last_name"]}.vcf"',
                "Cache-Control": "no-cache"
            }
        )

    # Web fallback with VCF download
    logger.info("Using web fallback with VCF download")
    return f"{base_url}/r/{vcard_data['_id']}?format=vcf"

async def notify_analytics(vcard_id: str, request: Request, device_info: dict, action_type: str, db = None):
    """Notify analytics service about the scan with enhanced device info and error handling"""
    analytics_url = f"{os.getenv('ANALYTICS_SERVICE_URL')}/api/v1/analytics/scan"
    event_id = str(uuid.uuid4())
    
    try:
        # Create the event data
        event_data = {
            "event_id": event_id,
            "vcard_id": vcard_id,
            "timestamp": datetime.utcnow().isoformat(),
            "device_info": device_info,
            "action_type": action_type,
            "success": True,
            "ip_address": request.client.host if request.client else None,
            "referrer": request.headers.get("referer", None),
            "user_agent": request.headers.get("user-agent", None)
        }
        
        logger.info(f"Sending analytics event {event_id} for VCard {vcard_id}, action: {action_type}")
        
        # Store event in local database for reliability
        if db:
            try:
                await db.scan_events.insert_one(event_data)
                logger.info(f"Event {event_id} stored in local database")
            except Exception as e:
                logger.error(f"Failed to store event in local database: {e}")
        
        # Send to analytics service
        response = await app.http_client.post(
            analytics_url,
            json=event_data,
            timeout=5.0  # Add timeout to prevent hanging
        )
        
        if response.status_code == 200:
            logger.info(f"Analytics service acknowledged event {event_id}: {response.status_code}")
        else:
            logger.error(f"Analytics service returned error for event {event_id}: {response.status_code} {response.text}")
            
        return response.status_code == 200
        
    except Exception as e:
        logger.error(f"Error notifying analytics for event {event_id}: {e}")
        logger.error(traceback.format_exc())
        return False

@app.get("/r/{vcard_id}")
async def redirect_to_vcard(
    vcard_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    format: str = None,
    action: str = "scan",  # Default action is scan, but can be overridden
    db = Depends(get_database)
):
    """Redirect to VCard page and record scan event with enhanced tracking"""
    try:
        request_id = str(uuid.uuid4())
        logger.info(f"\n=== Starting VCard Redirect {request_id} ===")
        logger.info(f"VCard ID: {vcard_id}")
        logger.info(f"Format requested: {format}")
        logger.info(f"Action requested: {action}")
        logger.info(f"User Agent: {request.headers.get('user-agent')}")
        logger.info(f"Referrer: {request.headers.get('referer')}")
        logger.info(f"Client IP: {request.client.host if request.client else 'unknown'}")
        
        # Get base URL with validation
        base_url = os.getenv('FRONTEND_URL')
        if not base_url:
            logger.error("FRONTEND_URL environment variable not set")
            raise HTTPException(status_code=500, detail="Server configuration error")
        base_url = base_url.rstrip('/')
        
        # Try to get VCard by ID as ObjectId first
        vcard = None
        try:
            vcard = await db.vcards.find_one({"_id": PyObjectId(vcard_id)})
        except:
            # If conversion to ObjectId fails, try as string
            logger.info(f"Trying to find VCard with string ID: {vcard_id}")
            vcard = await db.vcards.find_one({"_id": vcard_id})
            
        if not vcard:
            logger.error(f"VCard not found: {vcard_id}")
            raise HTTPException(status_code=404, detail="VCard not found")
        
        logger.info(f"Found VCard: {vcard['first_name']} {vcard['last_name']}")
        
        # Parse user agent and get device info
        user_agent = request.headers.get("user-agent", "")
        device_info = get_device_info(user_agent)
        logger.info(f"Detected device info: {device_info}")
        
        # Validate action type
        valid_actions = ["scan", "vcf_download", "contact_add", "page_view"]
        if action not in valid_actions:
            logger.warning(f"Invalid action type: {action}, defaulting to 'scan'")
            action = "scan"
        
        # Record the initial scan event
        # We'll do this synchronously to ensure it's recorded before proceeding
        await notify_analytics(vcard_id, request, device_info, action, db)
        
        # For mobile devices or explicit VCF request, serve the VCF file directly
        if device_info["is_mobile"] or format == "vcf":
            logger.info("Serving VCard file directly")
            vcf_content = generate_vcard(vcard)
            filename = f"{vcard['first_name']}_{vcard['last_name']}.vcf"
            
            # If the action wasn't already vcf_download, record it now
            if action != "vcf_download":
                background_tasks.add_task(
                    notify_analytics,
                    vcard_id,
                    request,
                    device_info,
                    "vcf_download",
                    db
                )
            
            return Response(
                content=vcf_content,
                media_type="text/vcard",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                    "Cache-Control": "no-cache"
                }
            )
        
        # For non-mobile devices, redirect to web view
        web_url = f"{base_url}/v/{vcard_id}"
        logger.info(f"Redirecting to web view: {web_url}")
        
        return RedirectResponse(
            url=web_url,
            status_code=302,
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
        )
        
    except Exception as e:
        logger.error(f"Error in redirect: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))