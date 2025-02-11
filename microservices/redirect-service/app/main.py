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
    """Generate .vcf file content"""
    card = vobject.vCard()
    
    # Add name
    card.add('fn')
    card.fn.value = f"{vcard_data['first_name']} {vcard_data['last_name']}"
    card.add('n')
    card.n.value = vobject.vcard.Name(
        family=vcard_data['last_name'],
        given=vcard_data['first_name']
    )
    
    # Add contact details
    if vcard_data.get('mobile_number'):
        tel = card.add('tel')
        tel.value = vcard_data['mobile_number']
        tel.type_param = 'CELL'
    
    if vcard_data.get('work_number'):
        tel = card.add('tel')
        tel.value = vcard_data['work_number']
        tel.type_param = 'WORK'
    
    if vcard_data.get('email'):
        email = card.add('email')
        email.value = vcard_data['email']
        
    if vcard_data.get('company'):
        org = card.add('org')
        org.value = [vcard_data['company']]
        
    if vcard_data.get('title'):
        title = card.add('title')
        title.value = vcard_data['title']
    
    if vcard_data.get('website'):
        url = card.add('url')
        url.value = vcard_data['website']
    
    # Add address if available
    if vcard_data.get('address'):
        adr = card.add('adr')
        adr.value = vobject.vcard.Address(
            street=vcard_data['address'].get('street', ''),
            city=vcard_data['address'].get('city', ''),
            region=vcard_data['address'].get('state', ''),
            code=vcard_data['address'].get('zip_code', ''),
            country=vcard_data['address'].get('country', '')
        )
    
    return card.serialize().encode('utf-8')

def get_platform_specific_url(vcard_data: dict, device_info: dict) -> str:
    """Generate platform-specific deep links"""
    if device_info["is_mobile"]:
        if device_info["os"] == "iOS":
            # iOS Universal Links
            contact_data = {
                "contact": {
                    "firstName": vcard_data['first_name'],
                    "lastName": vcard_data['last_name'],
                    "phoneNumbers": [{
                        "label": "mobile",
                        "number": vcard_data.get('mobile_number', '')
                    }],
                    "emailAddresses": [{
                        "label": "email",
                        "email": vcard_data.get('email', '')
                    }]
                }
            }
            return f"addressbook://contact/new?{urlencode(contact_data)}"
            
        elif device_info["os"] == "Android":
            # Android Intent
            contact_data = {
                "name": f"{vcard_data['first_name']} {vcard_data['last_name']}",
                "phone": vcard_data.get('mobile_number', ''),
                "email": vcard_data.get('email', ''),
                "company": vcard_data.get('company', ''),
                "job_title": vcard_data.get('title', '')
            }
            return f"content://com.android.contacts/contacts/lookup/{urlencode(contact_data)}"
    
    # Web fallback with VCF download
    return f"{os.getenv('FRONTEND_URL')}/r/{vcard_data['_id']}?format=vcf"

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
        # Get VCard
        vcard = await db.vcards.find_one({"_id": PyObjectId(vcard_id)})
        if not vcard:
            raise HTTPException(status_code=404, detail="VCard not found")
        
        # Parse user agent and get device info
        user_agent = request.headers.get("user-agent", "")
        device_info = get_device_info(user_agent)
        
        # If .vcf format is explicitly requested
        if format == "vcf":
            vcf_content = generate_vcard(vcard)
            filename = f"{vcard['first_name']}_{vcard['last_name']}.vcf"
            
            # Notify analytics about VCF download
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
                    "Content-Disposition": f'attachment; filename="{filename}"'
                }
            )
        
        # Get platform-specific URL
        redirect_url = get_platform_specific_url(vcard, device_info)
        
        # Notify analytics about contact add attempt
        background_tasks.add_task(
            notify_analytics,
            vcard_id,
            request,
            device_info,
            "contact_add"
        )
        
        return RedirectResponse(
            url=redirect_url,
            status_code=302
        )
        
    except Exception as e:
        logger.error(f"Error in redirect: {e}")
        return RedirectResponse(
            url=f"{os.getenv('FRONTEND_URL')}/error?id={vcard_id}",
            status_code=302
        )