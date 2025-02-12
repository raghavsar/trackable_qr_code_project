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
    """Generate platform-specific deep links with enhanced logging"""
    logger.info(f"Generating platform-specific URL. Device info: {device_info}")
    
    if device_info["is_mobile"]:
        name = f"{vcard_data['first_name']} {vcard_data['last_name']}"
        phone = vcard_data.get('mobile_number', '')
        if phone:
            phone = phone.replace(' ', '')
        email = vcard_data.get('email', '')
        
        logger.info(f"Processing mobile device. OS: {device_info['os']}, Browser: {device_info['browser']}")
        
        if "iOS" in device_info["os"]:
            logger.info("Generating iOS contact URL")
            # Use the more reliable iOS contact URL scheme
            contact_data = {
                "fn": name,
                "tel": phone,
                "email": email,
                "org": vcard_data.get('company', ''),
                "title": vcard_data.get('title', '')
            }
            # Filter out empty values and encode
            contact_data = {k: v for k, v in contact_data.items() if v}
            encoded_data = urlencode(contact_data)
            ios_url = f"contacts:add?{encoded_data}"
            logger.info(f"Generated iOS URL: {ios_url}")
            return ios_url
            
        elif "Android" in device_info["os"]:
            logger.info("Generating Android intent URL")
            
            # Use content provider URI for Android
            intent_params = [
                "action=android.intent.action.INSERT",
                "type=vnd.android.cursor.dir/contact",
                "package=com.android.contacts"
            ]
            
            # Add data parameters with proper encoding
            if name:
                intent_params.append(f"S.name={name}")
            if phone:
                intent_params.append(f"S.phone={phone}")
            if email:
                intent_params.append(f"S.email={email}")
            if vcard_data.get('company'):
                intent_params.append(f"S.company={vcard_data['company']}")
            if vcard_data.get('title'):
                intent_params.append(f"S.jobTitle={vcard_data['title']}")
            
            # Add fallback URL for devices that don't support the intent
            fallback_url = f"{os.getenv('FRONTEND_URL')}/r/{vcard_data['_id']}?format=vcf"
            intent_params.append(f"S.browser_fallback_url={fallback_url}")
            
            # Construct the final intent URL with proper encoding
            intent_params_encoded = [urlencode({'': param}).lstrip('=') for param in intent_params]
            intent_url = f"intent://contacts/#Intent;{';'.join(intent_params_encoded)};end"
            logger.info(f"Generated Android intent URL: {intent_url}")
            return intent_url
        
        else:
            logger.info(f"Unknown mobile OS: {device_info['os']}, falling back to VCF")
            return f"{os.getenv('FRONTEND_URL')}/r/{vcard_data['_id']}?format=vcf"
    
    # Web fallback with VCF download
    logger.info("Using web fallback with VCF download")
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
        # Debug logging for request details
        logger.info("\n=== Starting VCard Redirect ===")
        logger.info(f"VCard ID: {vcard_id}")
        logger.info(f"Format requested: {format}")
        logger.info(f"User Agent: {request.headers.get('user-agent')}")
        
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
        
        # If .vcf format is explicitly requested
        if format == "vcf":
            logger.info("Generating VCF file (explicit request)")
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
                    "Content-Disposition": f'attachment; filename="{filename}"',
                    "Cache-Control": "no-cache, no-store, must-revalidate"
                }
            )
        
        # For mobile devices, try platform-specific handling
        if device_info["is_mobile"]:
            # Generate mobile-specific URL
            redirect_url = get_platform_specific_url(vcard, device_info)
            logger.info(f"Generated mobile redirect URL: {redirect_url}")
            
            # Generate VCF content for fallback
            vcf_content = generate_vcard(vcard)
            filename = f"{vcard['first_name']}_{vcard['last_name']}.vcf"
            
            # Create a mobile-friendly HTML page with options
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <title>Add Contact - {vcard['first_name']} {vcard['last_name']}</title>
                <style>
                    body {{ 
                        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; 
                        padding: 20px; 
                        max-width: 500px; 
                        margin: 0 auto;
                        background: #f5f5f5;
                    }}
                    .card {{
                        background: white;
                        border-radius: 12px;
                        padding: 20px;
                        margin-bottom: 20px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }}
                    .button {{ 
                        display: block; 
                        width: 100%; 
                        padding: 15px; 
                        margin: 10px 0; 
                        border-radius: 8px; 
                        text-align: center; 
                        text-decoration: none;
                        font-weight: 500;
                        transition: all 0.2s;
                    }}
                    .primary {{ 
                        background: #0066ff; 
                        color: white;
                        box-shadow: 0 2px 4px rgba(0,102,255,0.2);
                    }}
                    .secondary {{ 
                        background: #f0f0f0; 
                        color: #333;
                    }}
                </style>
            </head>
            <body>
                <div class="card">
                    <h2>Add Contact</h2>
                    <p>{vcard['first_name']} {vcard['last_name']}</p>
                    {f'<p>{vcard["title"]}</p>' if vcard.get('title') else ''}
                    {f'<p>{vcard["company"]}</p>' if vcard.get('company') else ''}
                </div>
                <a href="{redirect_url}" class="button primary">Add to Contacts</a>
                <a href="?format=vcf" class="button secondary">Download VCard</a>
            </body>
            </html>
            """
            
            # Notify analytics about mobile redirect
            background_tasks.add_task(
                notify_analytics,
                vcard_id,
                request,
                device_info,
                "mobile_redirect"
            )
            
            return Response(
                content=html_content,
                media_type="text/html",
                headers={
                    "Content-Type": "text/html; charset=utf-8",
                    "Cache-Control": "no-cache, no-store, must-revalidate"
                }
            )
        
        # For non-mobile devices, redirect to web view
        web_url = f"{os.getenv('FRONTEND_URL')}/v/{vcard_id}"
        logger.info(f"Redirecting to web view: {web_url}")
        
        return RedirectResponse(
            url=web_url,
            status_code=302,
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
        )
        
    except Exception as e:
        logger.error(f"Error in redirect: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))