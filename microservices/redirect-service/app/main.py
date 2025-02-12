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
        f"FN:{vcard_data['first_name']} {vcard_data['last_name']}",
    ]
    
    # Add phone numbers with proper typing for better system dialog support
    if vcard_data.get('mobile_number'):
        vcard_lines.append(f"TEL;TYPE=CELL,VOICE:{vcard_data['mobile_number']}")
    if vcard_data.get('work_number'):
        vcard_lines.append(f"TEL;TYPE=WORK,VOICE:{vcard_data['work_number']}")
    
    # Add email with proper typing
    if vcard_data.get('email'):
        vcard_lines.append(f"EMAIL;TYPE=WORK,INTERNET:{vcard_data['email']}")
    
    # Add organization and title
    if vcard_data.get('company'):
        vcard_lines.append(f"ORG:{vcard_data['company']}")
    if vcard_data.get('title'):
        vcard_lines.append(f"TITLE:{vcard_data['title']}")
    
    # Add website
    if vcard_data.get('website'):
        vcard_lines.append(f"URL;TYPE=WORK:{vcard_data['website']}")
    
    # Add address if available with proper typing
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
        vcard_lines.append(f"ADR;TYPE=WORK:{';'.join(adr_parts)}")
    
    # Add required end
    vcard_lines.append("END:VCARD")
    
    # Join with proper line endings and encode
    return "\r\n".join(vcard_lines).encode('utf-8')

def get_platform_specific_url(vcard_data: dict, device_info: dict) -> str:
    """Generate platform-specific deep links with enhanced logging"""
    logger.info(f"Generating platform-specific URL. Device info: {device_info}")
    
    # Get base URL with fallback
    base_url = os.getenv('FRONTEND_URL', 'http://localhost:3000').rstrip('/')
    
    if device_info["is_mobile"]:
        name = f"{vcard_data['first_name']} {vcard_data['last_name']}"
        phone = vcard_data.get('mobile_number', '')
        if phone:
            phone = phone.replace(' ', '')
        email = vcard_data.get('email', '')
        
        logger.info(f"Processing mobile device. OS: {device_info['os']}, Browser: {device_info['browser']}")
        
        if "iOS" in device_info["os"]:
            logger.info("Generating iOS contact URL")
            # Use tel: scheme for iOS to trigger system dialog
            if phone:
                return f"tel:{phone}"
            # Fallback to contacts scheme if no phone
            contact_data = {
                "fn": name,
                "email": email,
                "org": vcard_data.get('company', ''),
                "title": vcard_data.get('title', '')
            }
            contact_data = {k: v for k, v in contact_data.items() if v}
            encoded_data = urlencode(contact_data)
            return f"contacts:add?{encoded_data}"
            
        elif "Android" in device_info["os"]:
            logger.info("Generating Android intent URL")
            
            if phone:
                # Use tel: scheme for Android to trigger system dialog
                return f"tel:{phone}"
            
            # Fallback to contacts intent if no phone
            intent_params = [
                "action=android.intent.action.INSERT",
                "type=vnd.android.cursor.dir/contact",
            ]
            
            # Add contact data
            contact_data = {
                "name": name,
                "email": email,
                "company": vcard_data.get('company', ''),
                "title": vcard_data.get('title', '')
            }
            contact_data = {k: v for k, v in contact_data.items() if v}
            
            for key, value in contact_data.items():
                intent_params.append(f"{key}={value}")
            
            # Add fallback URL
            fallback_url = f"{base_url}/r/{vcard_data['_id']}?format=vcf"
            intent_params.append(f"S.browser_fallback_url={urlencode({'': fallback_url}).lstrip('=')}")
            
            return f"intent://contacts/#Intent;{';'.join(intent_params)};end"
        
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
        # Debug logging for request details
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
        
        # Get VCard
        vcard = await db.vcards.find_one({"_id": PyObjectId(vcard_id)})
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

        # If explicitly requesting VCF format, serve the file
        if format == "vcf":
            logger.info("Serving VCard file as requested")
            vcf_content = generate_vcard(vcard)
            filename = f"{vcard['first_name']}_{vcard['last_name']}.vcf"
            
            return Response(
                content=vcf_content,
                media_type="text/vcard",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                    "Cache-Control": "no-cache"
                }
            )
        
        # For mobile devices, use platform-specific deep links
        if device_info["is_mobile"]:
            platform_url = get_platform_specific_url(vcard, device_info)
            logger.info(f"Redirecting to platform-specific URL: {platform_url}")
            
            # Notify analytics
            background_tasks.add_task(
                notify_analytics,
                vcard_id,
                request,
                device_info,
                "platform_redirect"
            )
            
            return RedirectResponse(
                url=platform_url,
                status_code=302,
                headers={"Cache-Control": "no-cache"}
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