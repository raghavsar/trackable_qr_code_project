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

logger = logging.getLogger(__name__)

def hex_to_rgb(hex_color: str) -> tuple:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def get_module_drawer(style: str, eye_style: str = None) -> SquareModuleDrawer:
    """Get the appropriate module drawer based on style."""
    style_map = {
        'square': SquareModuleDrawer(),
        'rounded': RoundedModuleDrawer(),
        'dots': CircleModuleDrawer(),
        'circular': CircleModuleDrawer(),
        'special': GappedSquareModuleDrawer(),
    }
    return style_map.get(style, SquareModuleDrawer())

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