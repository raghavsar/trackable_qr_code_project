from PIL import Image, ImageDraw, ImageFilter
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import (
    SquareModuleDrawer,
    RoundedModuleDrawer,
    CircleModuleDrawer,
    GappedSquareModuleDrawer,
)
from qrcode.image.styles.colormasks import SolidFillColorMask
import requests
from io import BytesIO
import logging
import os
from shared.models import QRDesignOptions
import base64
from datetime import datetime

logger = logging.getLogger(__name__)

def validate_color(color: tuple) -> bool:
    """Validate RGB color tuple"""
    return (
        isinstance(color, tuple) and
        len(color) == 3 and
        all(isinstance(c, int) and 0 <= c <= 255 for c in color)
    )

class CustomEyeDrawer(SquareModuleDrawer):
    def __init__(self, color):
        try:
            super().__init__()
            if not validate_color(color):
                raise ValueError(f"Invalid color value: {color}")
            self.eye_color = color
            self._img = Image.new('RGB', (10, 10), color)
            logger.info(f"Initialized CustomEyeDrawer with color: {color}")
        except Exception as e:
            logger.error(f"Failed to initialize CustomEyeDrawer: {str(e)}")
            raise

    def drawrect(self, box, is_eye):
        try:
            if is_eye:
                # For eye patterns, use the eye color
                self._img = Image.new('RGB', (10, 10), self.eye_color)
                super().drawrect(box, is_eye)
            else:
                # For non-eye patterns, use the parent's implementation
                super().drawrect(box, is_eye)
        except Exception as e:
            logger.error(f"Error in drawrect: {str(e)}")
            raise

def hex_to_rgb(hex_color: str) -> tuple:
    """Convert hex color to RGB tuple."""
    try:
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        if not validate_color(rgb):
            raise ValueError(f"Invalid RGB values from hex color: {hex_color}")
        return rgb
    except Exception as e:
        logger.error(f"Error converting hex to RGB: {str(e)}")
        raise ValueError(f"Invalid hex color format: {hex_color}")

def get_module_drawer(style: str, color: tuple) -> SquareModuleDrawer:
    """Get the appropriate module drawer based on style."""
    try:
        if not validate_color(color):
            raise ValueError(f"Invalid color value: {color}")

        logger.info(f"Creating module drawer for style: {style}")

        if style.lower() == 'dots':
            logger.info("Using CircleModuleDrawer for dots pattern")
            drawer = CircleModuleDrawer()
            # Make the dots slightly smaller for better appearance
            drawer.radius_ratio = 0.9
            # Set color using _img property
            drawer._img = Image.new('RGB', (10, 10), color)
            logger.info(f"CircleModuleDrawer configured with radius_ratio: {drawer.radius_ratio}")
            return drawer

        logger.info(f"Using alternative style: {style.lower()}")
        style_map = {
            'square': SquareModuleDrawer(),
            'rounded': RoundedModuleDrawer(),
            'gapped': GappedSquareModuleDrawer(),
            'vertical': SquareModuleDrawer(),
            'horizontal': SquareModuleDrawer(),
        }
        drawer = style_map.get(style.lower(), SquareModuleDrawer())
        drawer._img = Image.new('RGB', (10, 10), color)
        logger.info(f"Created drawer of type: {drawer.__class__.__name__}")
        return drawer
    except Exception as e:
        logger.error(f"Error creating module drawer: {str(e)}")
        raise

def process_logo(logo_path: str, add_background: bool = False, make_round: bool = False) -> Image:
    """Process logo image with background and rounding options."""
    try:
        # Load the logo
        if logo_path.startswith(('http://', 'https://')):
            response = requests.get(logo_path)
            response.raise_for_status()
            logo = Image.open(BytesIO(response.content))
        else:
            logo = Image.open(logo_path)

        # Convert to RGBA
        logo = logo.convert('RGBA')

        # Create a white circular background first
        background = Image.new('RGBA', logo.size, (255, 255, 255, 255))
        mask = Image.new('L', logo.size, 0)
        draw = ImageDraw.Draw(mask)

        # Draw a circle with anti-aliasing
        draw.ellipse((0, 0, logo.size[0], logo.size[1]), fill=255)
        mask = mask.filter(ImageFilter.GaussianBlur(1))

        # Apply the mask to the white background
        background.putalpha(mask)

        # Paste the logo onto the white circular background
        background.paste(logo, (0, 0), logo)

        return background

    except Exception as e:
        logger.error(f"Error processing logo: {str(e)}")
        logger.error(f"Current working directory: {os.getcwd()}")
        logger.error(f"Attempted logo path: {logo_path}")
        logger.error("Stack trace:", exc_info=True)
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

    # Add phone numbers with proper TYPE parameters
    if vcard_data.get('mobile_number'):
        formatted_number = format_phone_number(vcard_data['mobile_number'])
        vcard_lines.append(f"TEL;TYPE=CELL,VOICE:{formatted_number}")
        logger.info(f"Added mobile number: {formatted_number}")
    if vcard_data.get('work_number'):
        formatted_number = format_phone_number(vcard_data['work_number'])
        vcard_lines.append(f"TEL;TYPE=WORK,VOICE:{formatted_number}")
        logger.info(f"Added work number: {formatted_number}")

    # Add email with proper TYPE parameter - just "TYPE=WORK" to make it display as "Email"
    if vcard_data.get('email'):
        vcard_lines.append(f"EMAIL;TYPE=INTERNET:{vcard_data['email']}")
        logger.info(f"Added email: {vcard_data['email']}")

    # Add organization and title with improved formatting
    if vcard_data.get('company'):
        vcard_lines.append(f"ORG:{vcard_data['company']}")
        logger.info(f"Added company: {vcard_data['company']}")
    if vcard_data.get('title'):
        vcard_lines.append(f"TITLE:{vcard_data['title']}")
        logger.info(f"Added title: {vcard_data['title']}")

    # Add website as primary URL (only if provided)
    if vcard_data.get('website'):
        vcard_lines.append(f"URL:{vcard_data['website']}")
        logger.info(f"Added website: {vcard_data['website']}")

    # Add address if available
    if vcard_data.get('address'):
        addr = vcard_data['address']
        if any(addr.get(field) for field in ['street', 'city', 'state', 'zip_code', 'country']):
            # Format address components
            street = addr.get('street', '')
            city = addr.get('city', '')
            state = addr.get('state', '')
            zip_code = addr.get('zip_code', '')
            country = addr.get('country', '')

            # Create ADR property with WORK type (for better compatibility)
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

            logger.info(f"Added address: {formatted_address}")

    # Add notes without map URL
    notes_content = vcard_data.get('notes', '')
    if notes_content:
        # Escape special characters
        notes = notes_content.replace('\n', '\\n').replace('\r', '')
        vcard_lines.append(f"NOTE:{notes}")
        logger.info("Added user notes")

    # Add revision timestamp
    vcard_lines.append(f"REV:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}")

    vcard_lines.append("END:VCARD")

    vcard_content = "\r\n".join(vcard_lines)
    logger.info("Generated vCard 3.0 content")

    return vcard_content

def generate_google_maps_url(street='', city='', state='', zip_code='', country='') -> str:
    """Generate a Google Maps URL based on address components"""
    address_parts = []

    # Add non-empty address parts
    if street:
        address_parts.append(street)
    if city:
        address_parts.append(city)
    if state:
        address_parts.append(state)
    if zip_code:
        address_parts.append(zip_code)
    if country:
        address_parts.append(country)

    # If we have address components, generate a Google Maps URL
    if address_parts:
        # Join address parts with '+' for URL formatting
        formatted_address = "+".join([part.replace(' ', '+') for part in address_parts])
        return f"https://maps.app.goo.gl/?q={formatted_address}"

    return ""

async def generate_vcard_qr(vcard_data: dict, style_config: QRDesignOptions) -> bytes:
    """Generate QR code with direct vCard data"""
    logger.info("\n=== Starting QR Code Generation ===")
    logger.info(f"Pattern Style Requested: {style_config.pattern_style}")

    try:
        vcard_content = generate_vcard_content(vcard_data)
        logger.info(f"Design Options: {style_config.dict()}")

        # Create QR code instance
        qr = qrcode.QRCode(
            version=None,
            error_correction=getattr(qrcode.constants, f"ERROR_CORRECT_{style_config.error_correction}"),
            box_size=style_config.box_size,
            border=style_config.border,
        )
        qr.add_data(vcard_content)
        qr.make(fit=True)

        # Convert colors to RGB
        module_color = hex_to_rgb(style_config.module_color)
        eye_color = hex_to_rgb(style_config.eye_color)
        background_color = hex_to_rgb(style_config.background_color)

        logger.info(f"Colors - Module: {module_color}, Eye: {eye_color}, Background: {background_color}")

        # Initialize the appropriate module drawer with color
        module_drawer = get_module_drawer(style_config.pattern_style, module_color)
        logger.info(f"Module Drawer Type: {module_drawer.__class__.__name__}")
        logger.info(f"Module Drawer Configuration: {vars(module_drawer)}")

        # Create QR with proper color settings
        logger.info("Creating QR image with configured drawer")
        qr_image = qr.make_image(
            image_factory=StyledPilImage,
            module_drawer=module_drawer,
            fill_color=module_color,
            back_color=background_color,
            eye_drawer=CustomEyeDrawer(eye_color)
        )

        # Log image details
        if isinstance(qr_image, Image.Image):
            logger.info(f"Generated QR Image Size: {qr_image.size}, Mode: {qr_image.mode}")
        else:
            logger.info(f"Generated QR Image Type: {type(qr_image)}")
            qr_image = qr_image.get_image()
            logger.info(f"Converted to PIL Image - Size: {qr_image.size}, Mode: {qr_image.mode}")

        # Get the QR size and positions
        qr_width, qr_height = qr_image.size
        border_size = style_config.border * style_config.box_size

        # Create a drawing context
        draw = ImageDraw.Draw(qr_image)

        # Draw eye patterns with eye_color
        eye_size = 7 * style_config.box_size  # QR eyes are 7x7 modules
        eye_positions = [
            (border_size, border_size),  # Top-left
            (border_size, qr_height - border_size - eye_size),  # Bottom-left
            (qr_width - border_size - eye_size, border_size),  # Top-right
        ]

        for x, y in eye_positions:
            # Outer square (7x7)
            draw.rectangle([x, y, x + eye_size - 1, y + eye_size - 1], fill=eye_color)
            # Inner square (5x5)
            inner_pad = style_config.box_size
            draw.rectangle([
                x + inner_pad,
                y + inner_pad,
                x + eye_size - inner_pad - 1,
                y + eye_size - inner_pad - 1
            ], fill=background_color)
            # Center square (3x3)
            center_pad = 2 * style_config.box_size
            draw.rectangle([
                x + center_pad,
                y + center_pad,
                x + eye_size - center_pad - 1,
                y + eye_size - center_pad - 1
            ], fill=eye_color)

        # Process logo if provided
        if style_config.logo_url:
            logger.info(f"Processing logo from path: {style_config.logo_url}")
            try:
                # Try multiple possible locations for the logo
                possible_paths = [
                    # Direct path as provided
                    style_config.logo_url,
                    # Remove leading slash
                    style_config.logo_url.lstrip('/'),
                    # Check in the app directory
                    os.path.join(os.path.dirname(os.path.abspath(__file__)), style_config.logo_url.lstrip('/')),
                    # Check in test/test_output
                    os.path.join(os.path.dirname(os.path.abspath(__file__)), '../test/test_output/Phonon_Favicon.png'),
                    # Check in assets directory
                    '/app/assets/images/phonon-favicon.png'
                ]

                logo_path = None
                for path in possible_paths:
                    logger.info(f"Trying logo path: {path}")
                    if os.path.exists(path):
                        logo_path = path
                        logger.info(f"Found logo at: {path}")
                        break

                if not logo_path:
                    raise FileNotFoundError(f"Logo file not found in any of the possible locations: {possible_paths}")

                logo = process_logo(
                    logo_path,
                    style_config.logo_background or False,
                    style_config.logo_round or False
                )

                # Calculate logo size
                logo_size = int(qr_image.size[0] * (style_config.logo_size or 0.15))
                logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
                logger.info(f"Resized logo to {logo_size}x{logo_size} pixels")

                # Calculate position to center the logo
                position = ((qr_width - logo_size) // 2, (qr_height - logo_size) // 2)

                # Paste the logo
                qr_image.paste(logo, position, logo)
                logger.info("Successfully added logo to QR code")
            except Exception as e:
                logger.error(f"Failed to process logo: {str(e)}")
                logger.error("Stack trace:", exc_info=True)
                # Continue without logo if there's an error
        else:
            logger.info("No logo path provided - generating QR code without logo")

        # Convert to bytes
        img_byte_arr = BytesIO()
        qr_image.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()

        return img_byte_arr
    except Exception as e:
        logger.error(f"Failed to generate QR code: {str(e)}")
        logger.error("Stack trace:", exc_info=True)
        raise