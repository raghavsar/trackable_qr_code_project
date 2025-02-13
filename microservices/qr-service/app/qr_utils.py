from PIL import Image, ImageDraw
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import (
    SquareModuleDrawer,
    RoundedModuleDrawer,
    CircleModuleDrawer,
    GappedSquareModuleDrawer,
)
import requests
from io import BytesIO
import logging
import os
from shared.models import QRDesignOptions

logger = logging.getLogger(__name__)

def hex_to_rgb(hex_color: str) -> tuple:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def get_module_drawer(style: str) -> SquareModuleDrawer:
    """Get the appropriate module drawer based on style."""
    style_map = {
        'square': SquareModuleDrawer(),
        'rounded': RoundedModuleDrawer(),
        'dots': CircleModuleDrawer(),
        'gapped': GappedSquareModuleDrawer(),
        'vertical': SquareModuleDrawer(),  # TODO: Implement vertical style
        'horizontal': SquareModuleDrawer(),  # TODO: Implement horizontal style
    }
    return style_map.get(style.lower(), SquareModuleDrawer())

def process_logo(logo_url: str, add_background: bool = False, make_round: bool = False) -> Image:
    """Process logo image with background and rounding options."""
    try:
        # Download logo
        response = requests.get(logo_url)
        response.raise_for_status()
        logo = Image.open(BytesIO(response.content))

        # Convert to RGBA if not already
        if logo.mode != 'RGBA':
            logo = logo.convert('RGBA')

        if make_round:
            # Create a circular mask
            mask = Image.new('L', logo.size, 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0) + logo.size, fill=255)
            
            # Create new image with transparent background
            output = Image.new('RGBA', logo.size, (0, 0, 0, 0))
            output.paste(logo, (0, 0))
            output.putalpha(mask)
            logo = output

        if add_background:
            # Create white background
            background = Image.new('RGBA', logo.size, (255, 255, 255, 255))
            # Paste logo onto background
            background.paste(logo, (0, 0), logo)
            logo = background

        return logo
    except Exception as e:
        logger.error(f"Error processing logo: {str(e)}")
        raise 

def format_phone_number(phone: str) -> str:
    """Format phone number to E.164 format with Indian prefix"""
    # Remove any non-digit characters
    phone = ''.join(filter(str.isdigit, phone))
    
    # If number starts with 0, remove it
    if phone.startswith('0'):
        phone = phone[1:]
    
    # If number doesn't have country code, add +91
    if not phone.startswith('91'):
        phone = f"91{phone}"
    
    # Add + prefix
    if not phone.startswith('+'):
        phone = f"+{phone}"
    
    return phone

def process_profile_photo(photo_data: str) -> tuple[str, str]:
    """Process profile photo and return vCard PHOTO type and value"""
    if photo_data.startswith('data:image'):
        # Handle base64 encoded image
        mime_type = photo_data.split(';')[0].split(':')[1]
        base64_data = photo_data.split(',')[1]
        return mime_type, base64_data
    else:
        # Handle URL
        return "URL", photo_data

def generate_vcard_content(vcard_data: dict) -> str:
    """Generate vCard content with tracking"""
    # Ensure required fields are not None
    first_name = vcard_data.get('first_name', '')
    last_name = vcard_data.get('last_name', '')
    
    logger.info(f"Generating vCard content for: {first_name} {last_name}")
    
    vcard_lines = [
        "BEGIN:VCARD",
        "VERSION:4.0",
        "KIND:INDIVIDUAL",
        f"N:{last_name};{first_name};;;",
        f"FN:{first_name} {last_name}",
    ]
    
    # Add profile photo if exists
    if vcard_data.get('profile_picture'):
        try:
            photo_type, photo_value = process_profile_photo(vcard_data['profile_picture'])
            if photo_type == "URL":
                vcard_lines.append(f"PHOTO:{photo_value}")
            else:
                vcard_lines.append(f"PHOTO;ENCODING=b;TYPE={photo_type}:{photo_value}")
            logger.info("Added profile picture to vCard")
        except Exception as e:
            logger.error(f"Failed to process profile picture: {str(e)}")
    
    # Add phone numbers if they exist and are not None
    if vcard_data.get('mobile_number'):
        formatted_number = format_phone_number(vcard_data['mobile_number'])
        vcard_lines.append(f"TEL;TYPE=CELL,VOICE:{formatted_number}")
        logger.info(f"Added mobile number: {formatted_number}")
    if vcard_data.get('work_number'):
        formatted_number = format_phone_number(vcard_data['work_number'])
        vcard_lines.append(f"TEL;TYPE=WORK,VOICE:{formatted_number}")
        logger.info(f"Added work number: {formatted_number}")
    
    # Add email if it exists and is not None
    if vcard_data.get('email'):
        vcard_lines.append(f"EMAIL;TYPE=WORK,INTERNET:{vcard_data['email']}")
        logger.info(f"Added email: {vcard_data['email']}")
    
    # Add organization and title if they exist and are not None
    if vcard_data.get('company'):
        vcard_lines.append(f"ORG:{vcard_data['company']}")
        logger.info(f"Added company: {vcard_data['company']}")
    if vcard_data.get('title'):
        vcard_lines.append(f"TITLE:{vcard_data['title']}")
        vcard_lines.append(f"ROLE:{vcard_data['title']}")
        logger.info(f"Added title: {vcard_data['title']}")
    
    # Add website if it exists and is not None
    if vcard_data.get('website'):
        vcard_lines.append(f"URL:{vcard_data['website']}")
        logger.info(f"Added website: {vcard_data['website']}")
    
    # Add address if it exists and has any non-None values
    if vcard_data.get('address'):
        addr = vcard_data['address']
        if any(addr.get(field) for field in ['street', 'city', 'state', 'zip_code', 'country']):
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
            logger.info(f"Added address: {', '.join(filter(None, adr_parts))}")
    
    # Add tracking if tracking_id exists
    if vcard_data.get('tracking_id'):
        api_gateway_url = os.getenv('API_GATEWAY_URL', 'http://localhost:8000')
        tracking_url = f"{api_gateway_url}/t/{vcard_data['tracking_id']}"
        vcard_lines.extend([
            f"X-TRACKING-ID:{vcard_data['tracking_id']}",
            f"NOTE:Contact created via QR Code. View profile: {tracking_url}"
        ])
        logger.info(f"Added tracking URL: {tracking_url}")
    
    vcard_lines.append("END:VCARD")
    
    vcard_content = "\r\n".join(vcard_lines)
    logger.info("Generated vCard content:")
    logger.info(vcard_content)
    
    return vcard_content

async def generate_vcard_qr(vcard_data: dict, style_config: QRDesignOptions) -> bytes:
    """Generate QR code with direct vCard data"""
    logger.info("Starting QR code generation with vCard data")
    
    vcard_content = generate_vcard_content(vcard_data)
    logger.info(f"Using QR design options: {style_config.dict()}")
    
    qr = qrcode.QRCode(
        version=None,
        error_correction=getattr(qrcode.constants, f"ERROR_CORRECT_{style_config.error_correction}"),
        box_size=style_config.box_size,
        border=style_config.border,
    )
    qr.add_data(vcard_content)
    qr.make(fit=True)
    logger.info(f"Created QR code with version {qr.version} and error correction {style_config.error_correction}")
    
    # Get module drawer based on style
    module_drawer = get_module_drawer(style_config.pattern_style)
    logger.info(f"Using module drawer for style: {style_config.pattern_style}")
    
    # Create QR image with style
    qr_image = qr.make_image(
        image_factory=StyledPilImage,
        module_drawer=module_drawer,
        eye_drawer=module_drawer,
        color=hex_to_rgb(style_config.foreground_color),
        back_color=hex_to_rgb(style_config.background_color)
    )
    logger.info("Created styled QR image")
    
    # Process logo if provided
    if style_config.logo_url:
        logger.info(f"Processing logo from URL: {style_config.logo_url}")
        logo = process_logo(
            style_config.logo_url,
            style_config.logo_background or False,
            style_config.logo_round or False
        )
        
        # Calculate logo size
        logo_size = int(qr_image.size[0] * (style_config.logo_size or 0.2))
        logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
        logger.info(f"Resized logo to {logo_size}x{logo_size} pixels")
        
        # Calculate position to center the logo
        pos = ((qr_image.size[0] - logo_size) // 2, (qr_image.size[1] - logo_size) // 2)
        
        # Create a copy of the QR code image
        qr_with_logo = qr_image.copy()
        qr_with_logo.paste(logo, pos, logo)
        qr_image = qr_with_logo
        logger.info("Added logo to QR code")
    
    # Convert to bytes
    img_byte_arr = BytesIO()
    qr_image.save(img_byte_arr, format='PNG')
    logger.info("Converted QR code to PNG format")
    
    return img_byte_arr.getvalue() 