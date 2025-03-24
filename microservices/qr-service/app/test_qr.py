"""Test script for QR code generation with our custom styling"""
import asyncio
import os
import sys
from PIL import Image 
from io import BytesIO

# Fix the Python path to include the microservices directory
current_dir = os.path.dirname(os.path.abspath(__file__))
qr_service_dir = os.path.dirname(current_dir)
microservices_dir = os.path.dirname(qr_service_dir)
sys.path.insert(0, microservices_dir)

# Now we can import from shared
from shared.models import QRDesignOptions
from app.qr_utils import generate_vcard_qr

async def test_qr_generation():
    """Test QR code generation with standard black and white styling"""
    print("Testing QR code generation...")
    
    # Sample VCard data - ensure it has a valid ID for URL generation
    vcard_data = {
        "_id": "64f2a1b3c4d5e6f7a8b9c0d1",  # Example MongoDB ObjectId format
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "mobile_number": "+1234567890",
        "title": "Software Engineer",
        "company": "Phonon",
        "website": "https://example.com",
        "notes": "Sample notes"
    }
    
    # Set environment variable for testing
    os.environ["FRONTEND_URL"] = "http://192.168.7.154:5173"
    
    # Generate QR code (now using standard black and white style)
    qr_image_bytes_io = await generate_vcard_qr(vcard_data)
    
    # Save to file using the existing test_output directory
    output_dir = os.path.join(qr_service_dir, "test", "test_output")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "styled_qr_code.png")
    
    with open(output_path, "wb") as f:
        f.write(qr_image_bytes_io.getvalue())
    
    print(f"QR code saved to {output_path}")
    print(f"QR code contains URL: http://192.168.7.154:5173/r/{vcard_data['_id']}")
    
    # Display the image if running interactively
    try:
        # Reset position to beginning of file
        qr_image_bytes_io.seek(0)
        img = Image.open(qr_image_bytes_io)
        img.show()
        print("QR code displayed")
    except Exception as e:
        print(f"Could not display image: {e}")

if __name__ == "__main__":
    asyncio.run(test_qr_generation()) 