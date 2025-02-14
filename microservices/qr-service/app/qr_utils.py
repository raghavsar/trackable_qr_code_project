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
import base64

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
    """Format phone number to E.164 format for VCard 3.0 compatibility"""
    if not phone:
        return ""
        
    # Remove any non-digit characters
    phone = ''.join(filter(str.isdigit, phone))
    
    # If number starts with 0, remove it
    if phone.startswith('0'):
        phone = phone[1:]
    
    # Handle different formats
    if phone.startswith('+'):
        phone = phone[1:]  # Remove + if exists
    
    # Add country code if missing (assuming Indian numbers)
    if not phone.startswith('91') and len(phone) == 10:
        phone = f"91{phone}"
    
    # Validate length (international format)
    if len(phone) < 11 or len(phone) > 15:
        raise ValueError("Invalid phone number length")
    
    # Format for VCard 3.0: +[country_code][number]
    return f"+{phone}"

def process_profile_photo(photo_data: str) -> tuple[str, str]:
    """Process profile photo and return vCard PHOTO type and value"""
    if photo_data.startswith('data:image'):
        # For base64 data, we'll use URL instead to keep QR code small
        logger.info("Converting base64 image to URL for QR code size optimization")
        return "URL", photo_data
    else:
        # For URLs, just pass through
        logger.info("Using direct URL for profile photo")
        return "URL", photo_data

def generate_vcard_content(vcard_data: dict) -> str:
    """Generate vCard content with tracking using VCard 3.0 format for better compatibility and smaller QR codes"""
    # Ensure required fields are not None
    first_name = vcard_data.get('first_name', '')
    last_name = vcard_data.get('last_name', '')
    
    logger.info(f"Generating vCard 3.0 content for: {first_name} {last_name}")
    
    vcard_lines = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        f"N:{last_name};{first_name};;;",
        f"FN:{first_name} {last_name}"
    ]
    
    # Add profile photo if exists - optimized for QR code size
    if vcard_data.get('profile_picture'):
        try:
            photo_type, photo_value = process_profile_photo(vcard_data['profile_picture'])
            # Always use URL format for smaller QR size
            vcard_lines.append(f"PHOTO;VALUE=URI:{photo_value}")
            logger.info("Added profile picture URL to vCard")
        except Exception as e:
            logger.error(f"Failed to process profile picture: {str(e)}")
    
    # Add phone numbers - simplified format for v3.0
    if vcard_data.get('mobile_number'):
        formatted_number = format_phone_number(vcard_data['mobile_number'])
        vcard_lines.append(f"TEL;CELL:{formatted_number}")
        logger.info(f"Added mobile number: {formatted_number}")
    if vcard_data.get('work_number'):
        formatted_number = format_phone_number(vcard_data['work_number'])
        vcard_lines.append(f"TEL;WORK:{formatted_number}")
        logger.info(f"Added work number: {formatted_number}")
    
    # Add email - simplified for v3.0
    if vcard_data.get('email'):
        vcard_lines.append(f"EMAIL:{vcard_data['email']}")
        logger.info(f"Added email: {vcard_data['email']}")
    
    # Add organization and title - simplified for v3.0
    if vcard_data.get('company'):
        vcard_lines.append(f"ORG:{vcard_data['company']}")
        logger.info(f"Added company: {vcard_data['company']}")
    if vcard_data.get('title'):
        vcard_lines.append(f"TITLE:{vcard_data['title']}")
        logger.info(f"Added title: {vcard_data['title']}")
    
    # Add website - simplified for v3.0
    if vcard_data.get('website'):
        vcard_lines.append(f"URL:{vcard_data['website']}")
        logger.info(f"Added website: {vcard_data['website']}")
    
    # Add address - simplified for v3.0
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
            vcard_lines.append(f"ADR:{';'.join(adr_parts)}")
            logger.info(f"Added address: {', '.join(filter(None, adr_parts))}")
    
    # Add user notes only
    if vcard_data.get('notes'):
        vcard_lines.append(f"NOTE:{vcard_data['notes']}")
        logger.info(f"Added user notes: {vcard_data['notes']}")
    
    vcard_lines.append("END:VCARD")
    
    vcard_content = "\r\n".join(vcard_lines)
    logger.info("Generated vCard 3.0 content")
    
    return vcard_content

async def generate_vcard_qr(vcard_data: dict, style_config: QRDesignOptions) -> bytes:
    """Generate QR code with direct vCard data"""
    logger.info("Starting QR code generation with vCard data")
    
    vcard_content = generate_vcard_content(vcard_data)
    logger.info(f"Using QR design options: {style_config.dict()}")
    
    # Try different error correction levels if data is too large
    error_levels = ['H', 'Q', 'M', 'L']
    current_level_idx = error_levels.index(style_config.error_correction)
    
    for level in error_levels[current_level_idx:]:
        try:
            qr = qrcode.QRCode(
                version=None,
                error_correction=getattr(qrcode.constants, f"ERROR_CORRECT_{level}"),
                box_size=style_config.box_size,
                border=style_config.border,
            )
            qr.add_data(vcard_content)
            qr.make(fit=True)
            
            if qr.version <= 40:  # Valid version found
                logger.info(f"Created QR code with version {qr.version} and error correction {level}")
                break
        except Exception as e:
            logger.warning(f"Failed with error correction level {level}: {str(e)}")
            continue
    else:
        raise ValueError("Data too large for QR code even with lowest error correction")
    
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