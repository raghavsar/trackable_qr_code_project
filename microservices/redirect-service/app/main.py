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
    
    # Add phone numbers with simplified typing
    if vcard_data.get('mobile_number'):
        vcard_lines.append(f"TEL;CELL:{vcard_data['mobile_number']}")
    if vcard_data.get('work_number'):
        vcard_lines.append(f"TEL;WORK:{vcard_data['work_number']}")
    
    # Add email with simplified typing
    if vcard_data.get('email'):
        vcard_lines.append(f"EMAIL:{vcard_data['email']}")
    
    # Add organization and title
    if vcard_data.get('company'):
        vcard_lines.append(f"ORG:{vcard_data['company']}")
    if vcard_data.get('title'):
        vcard_lines.append(f"TITLE:{vcard_data['title']}")
    
    # Add website
    if vcard_data.get('website'):
        vcard_lines.append(f"URL:{vcard_data['website']}")
    
    # Add address if available
    if vcard_data.get('address'):
        addr = vcard_data['address']
        adr_parts = [
            "",  # Post office box
            "",  # Extended address
            addr.get('street', ''),
            addr.get('city', ''),
            addr.get('state', ''),
            addr.get('zip_code', ''),
            addr.get('country', '')
        ]
        vcard_lines.append(f"ADR:{';'.join(adr_parts)}")
    
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

async def notify_analytics(vcard_id: str, request: Request, device_info: dict, action_type: str):
    """Notify analytics service about the scan with enhanced device info"""
    analytics_url = f"{os.getenv('ANALYTICS_SERVICE_URL')}/api/v1/analytics/scan"
    try:
        await app.http_client.post(
            analytics_url,
            json={
                "vcard_id": vcard_id,
                "timestamp": datetime.utcnow().isoformat(),
                "device_info": device_info,
                "action_type": action_type,
                "success": True,
                "ip_address": request.client.host if request.client else None,
                "headers": dict(request.headers)
            }
        )
    except Exception as e:
        logger.error(f"Error notifying analytics: {e}")

@app.get("/r/{vcard_id}")
async def redirect_to_vcard(
    vcard_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    format: str = None,
    db = Depends(get_database)
):
    try:
        logger.info("\n=== Starting VCard Redirect ===")
        logger.info(f"VCard ID: {vcard_id}")
        logger.info(f"Format requested: {format}")
        logger.info(f"User Agent: {request.headers.get('user-agent')}")
        
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
        
        # Notify analytics about the scan
        background_tasks.add_task(
            notify_analytics,
            vcard_id,
            request,
            device_info,
            "scan"
        )

        # For mobile devices or explicit VCF request, serve the VCF file directly
        if device_info["is_mobile"] or format == "vcf":
            logger.info("Serving VCard file directly")
            vcf_content = generate_vcard(vcard)
            filename = f"{vcard['first_name']}_{vcard['last_name']}.vcf"
            
            # Notify analytics
            background_tasks.add_task(
                notify_analytics,
                vcard_id,
                request,
                device_info,
                "vcf_download"
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
        raise HTTPException(status_code=500, detail=str(e))