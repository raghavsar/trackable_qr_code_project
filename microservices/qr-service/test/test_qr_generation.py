import pytest
import segno
from PIL import Image, ImageDraw
import io
import json
from pathlib import Path
import os
from datetime import datetime

# Test data constants
TEST_URL = "https://example.com"
TEST_TEXT = "Hello, World!"
TEST_VCARD_DATA = {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@example.com",
    "mobile_number": "+1234567890",
    "company": "Test Company",
    "title": "Software Engineer",
    "website": "https://johndoe.com"
}

@pytest.fixture
def output_directory():
    """Fixture to create and manage test output directory"""
    test_output_dir = Path("test_output")
    test_output_dir.mkdir(exist_ok=True)
    yield test_output_dir
    # Cleanup can be added here if needed

class TestQRGeneration:
    def test_basic_url_generation(self, output_directory):
        """Test basic URL QR code generation"""
        qr = segno.make(TEST_URL)
        
        # Save QR code and verify it exists
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_directory / f"test_url_{timestamp}.png"
        qr.save(str(output_path), scale=10)
        
        assert output_path.exists()
        
        # Verify the QR code is readable
        img = Image.open(output_path)
        assert img.size[0] > 0 and img.size[1] > 0

    def test_vcard_generation(self, output_directory):
        """Test VCard QR code generation"""
        # Create VCard content
        vcard_content = [
            "BEGIN:VCARD",
            "VERSION:3.0",
            f"N:{TEST_VCARD_DATA['last_name']};{TEST_VCARD_DATA['first_name']};;;",
            f"FN:{TEST_VCARD_DATA['first_name']} {TEST_VCARD_DATA['last_name']}",
            f"EMAIL:{TEST_VCARD_DATA['email']}",
            f"TEL;CELL:{TEST_VCARD_DATA['mobile_number']}",
            f"ORG:{TEST_VCARD_DATA['company']}",
            f"TITLE:{TEST_VCARD_DATA['title']}",
            f"URL:{TEST_VCARD_DATA['website']}",
            "END:VCARD"
        ]
        vcard_string = "\r\n".join(vcard_content)
        
        # Generate QR code
        qr = segno.make(vcard_string, error='H')
        
        # Save and verify
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_directory / f"test_vcard_{timestamp}.png"
        qr.save(str(output_path), scale=10)
        
        assert output_path.exists()
        
        # Verify image properties
        img = Image.open(output_path)
        assert img.size[0] > 0 and img.size[1] > 0

    def test_qr_with_different_error_levels(self, output_directory):
        """Test QR generation with different error correction levels"""
        error_levels = ['L', 'M', 'Q', 'H']
        
        for level in error_levels:
            qr = segno.make(TEST_TEXT, error=level)
            output_path = output_directory / f"test_error_{level}.png"
            qr.save(str(output_path), scale=10)
            
            assert output_path.exists()
            img = Image.open(output_path)
            assert img.size[0] > 0 and img.size[1] > 0

    def test_qr_with_custom_colors(self, output_directory):
        """Test QR code generation with custom colors"""
        qr = segno.make(TEST_URL)
        output_path = output_directory / "test_colored.png"
        
        # Save with custom colors
        qr.save(
            str(output_path),
            scale=10,
            dark='navy',
            light='lightblue'
        )
        
        assert output_path.exists()
        img = Image.open(output_path)
        assert img.size[0] > 0 and img.size[1] > 0

    def test_qr_data_capacity(self):
        """Test QR code data capacity limits"""
        # Test with increasing data sizes
        base_string = "A" * 100
        for multiplier in [1, 10, 100]:
            test_data = base_string * multiplier
            try:
                qr = segno.make(test_data)
                assert qr is not None
            except Exception as e:
                if multiplier == 100:
                    # Expected to fail with very large data
                    assert isinstance(e, (ValueError, segno.DataOverflowError))
                else:
                    raise

    def test_qr_version_selection(self):
        """Test automatic version selection based on data size"""
        # Test with different data sizes
        test_cases = [
            "Short text",
            "A" * 100,
            "A" * 500
        ]
        
        for test_data in test_cases:
            qr = segno.make(test_data)
            # Extract numeric part from version (e.g., 'M4' -> 4)
            version = int(''.join(filter(str.isdigit, str(qr.version))))
            assert 1 <= version <= 40  # Valid QR versions range from 1 to 40

    @pytest.mark.parametrize("boost_error", [True, False])
    def test_error_correction_boost(self, boost_error, output_directory):
        """Test QR generation with and without error correction boost"""
        qr = segno.make(TEST_URL, boost_error=boost_error)
        output_path = output_directory / f"test_boost_{boost_error}.png"
        qr.save(str(output_path), scale=10)
        
        assert output_path.exists()
        img = Image.open(output_path)
        assert img.size[0] > 0 and img.size[1] > 0

    def test_custom_phonon_style(self, output_directory):
        """Test QR code generation with custom dot pattern and rounded eyes"""
        # Create QR code with high error correction
        qr = segno.make(TEST_URL, error='H')
        
        # Increase scale for better quality and more precise dot placement
        scale = 40  # Increased scale for better dot definition
        width = height = (qr.version * 4 + 17) * scale
        img = Image.new('RGBA', (width, width), (255, 255, 255, 255))
        
        # Updated colors to match the image
        pattern_rgb = (24, 55, 166)    # Adjusted blue for data modules
        eye_rgb = (239, 68, 37)        # Adjusted orange for finder patterns
        
        draw = ImageDraw.Draw(img)
        matrix = qr.matrix
        size = len(matrix)
        
        def get_finder_pattern_info(row, col, size):
            finder_areas = [
                (0, 0, "top-left"),
                (0, size - 7, "top-right"),
                (size - 7, 0, "bottom-left")
            ]
            for start_row, start_col, position in finder_areas:
                if (start_row <= row < start_row + 7 and 
                    start_col <= col < start_col + 7):
                    return True, start_row, start_col, position
            return False, 0, 0, None
        
        # Draw data modules as smaller dots
        dot_size = scale * 0.65  # Reduced dot size for better spacing
        dot_offset = (scale - dot_size) / 2
        
        # Draw data modules first (dots)
        for row in range(size):
            for col in range(size):
                is_finder, _, _, _ = get_finder_pattern_info(row, col, size)
                if matrix[row][col] and not is_finder:
                    x = col * scale + dot_offset
                    y = row * scale + dot_offset
                    # Create perfect circles for data modules
                    draw.ellipse([x, y, x + dot_size - 1, y + dot_size - 1],
                               fill=pattern_rgb + (255,))
        
        # Custom function for drawing finder patterns with rounded corners
        def draw_custom_eye(start_row, start_col):
            x = start_col * scale
            y = start_row * scale
            size = 7 * scale
            
            # Increased corner radius and adjusted margin
            corner_radius = scale * 2.8
            margin = scale * 0.5
            
            # Draw rounded square finder pattern
            eye_bounds = [
                x + margin,
                y + margin,
                x + size - margin - 1,
                y + size - margin - 1
            ]
            draw.rounded_rectangle(eye_bounds, radius=corner_radius, fill=eye_rgb + (255,))
        
        # Draw finder patterns
        for row in range(size):
            for col in range(size):
                is_finder, start_row, start_col, pos = get_finder_pattern_info(row, col, size)
                if is_finder and row == start_row and col == start_col:
                    draw_custom_eye(start_row, start_col)
        
        # Add center logo
        logo_size = int(width * 0.18)  # Adjusted size to match reference
        logo_img = Image.new('RGBA', (logo_size, logo_size), (0, 0, 0, 0))
        logo_draw = ImageDraw.Draw(logo_img)
        
        # Draw logo components
        # Outer circle (blue)
        logo_draw.ellipse([0, 0, logo_size-1, logo_size-1],
                         fill=pattern_rgb + (255,))
        
        # White background circle
        inner_size = logo_size * 0.85
        inner_offset = (logo_size - inner_size) / 2
        logo_draw.ellipse([inner_offset, inner_offset,
                          inner_offset + inner_size - 1,
                          inner_offset + inner_size - 1],
                         fill=(255, 255, 255, 255))
        
        # Center orange circle
        center_size = logo_size * 0.6
        center_offset = (logo_size - center_size) / 2
        logo_draw.ellipse([center_offset, center_offset,
                          center_offset + center_size - 1,
                          center_offset + center_size - 1],
                         fill=eye_rgb + (255,))
        
        # Create white circular background for logo
        circle_size = int(logo_size * 1.4)  # Larger background circle
        circle_img = Image.new('RGBA', (circle_size, circle_size), (0, 0, 0, 0))
        circle_draw = ImageDraw.Draw(circle_img)
        circle_draw.ellipse([0, 0, circle_size-1, circle_size-1],
                           fill=(255, 255, 255, 255))
        
        # Calculate positions for logo placement
        circle_pos = ((width - circle_size) // 2, (height - circle_size) // 2)
        logo_pos = ((width - logo_size) // 2, (height - logo_size) // 2)
        
        # Paste the white circle and logo
        img.paste(circle_img, circle_pos, circle_img)
        img.paste(logo_img, logo_pos, logo_img)
        
        # Save with maximum quality
        output_path = output_directory / "phonon_styled_qr_final.png"
        img.save(str(output_path), quality=100)
        
        assert output_path.exists()
        assert img.size[0] > 0 and img.size[1] > 0

    def test_custom_eye_shapes(self, output_directory):
        """Test QR code generation with custom eye shapes matching Phonon style"""
        # Create QR code with high error correction
        qr = segno.make(TEST_URL, error='H')  # Using URL instead of VCard for simpler QR pattern
        
        # Increase scale for better quality
        scale = 30  # Increased scale for even better quality
        width = height = (qr.version * 4 + 17) * scale
        img = Image.new('RGBA', (width, width), (255, 255, 255, 255))
        
        # Define our custom colors
        pattern_rgb = (15, 80, 181)    # Blue pattern color
        eye_rgb = (255, 77, 38)        # Orange eye color
        
        draw = ImageDraw.Draw(img)
        matrix = qr.matrix
        size = len(matrix)
        
        # Function to get finder pattern info
        def get_finder_pattern_info(row, col, size):
            finder_areas = [
                (0, 0, "top-left"),                    
                (0, size - 7, "top-right"),            
                (size - 7, 0, "bottom-left")           
            ]
            for start_row, start_col, position in finder_areas:
                if (start_row <= row < start_row + 7 and 
                    start_col <= col < start_col + 7):
                    return True, start_row, start_col, position
            return False, 0, 0, None
        
        # Draw regular modules (not part of finder patterns) as dots
        dot_size = scale * 0.75  # Smaller dots to match reference
        dot_offset = (scale - dot_size) / 2
        
        # Draw data modules first
        for row in range(size):
            for col in range(size):
                is_finder, _, _, _ = get_finder_pattern_info(row, col, size)
                if matrix[row][col] and not is_finder:
                    x = col * scale + dot_offset
                    y = row * scale + dot_offset
                    # Use antialiasing for smoother circles
                    draw.ellipse([x, y, x + dot_size - 1, y + dot_size - 1], 
                               fill=pattern_rgb + (255,))
        
        # Draw custom eye patterns
        def draw_custom_eye(start_row, start_col):
            x = start_col * scale
            y = start_row * scale
            size = 7 * scale
            
            # More rounded square with larger corner radius
            corner_radius = scale * 2.5  # Increased radius for more rounded corners
            margin = scale * 0.2  # Add slight margin around eyes
            eye_bounds = [
                x + margin, 
                y + margin, 
                x + size - margin - 1, 
                y + size - margin - 1
            ]
            draw.rounded_rectangle(eye_bounds, radius=corner_radius, fill=eye_rgb + (255,))
        
        # Draw custom eyes
        for row in range(size):
            for col in range(size):
                is_finder, start_row, start_col, pos = get_finder_pattern_info(row, col, size)
                if is_finder and row == start_row and col == start_col:
                    draw_custom_eye(start_row, start_col)
        
        try:
            # Use the exact path provided
            logo_path = Path("test_output/Phonon_Favicon.png")
            if not logo_path.exists():
                # Try absolute path if relative path fails
                logo_path = Path(r"C:\Users\Asus\OneDrive\Desktop\Phonon\Projects\qr_code_project\microservices\qr-service\test\test_output\Phonon_Favicon.png")
            
            print(f"Looking for logo at: {logo_path.absolute()}")
            logo_img = Image.open(logo_path)
            if logo_img.mode != 'RGBA':
                logo_img = logo_img.convert('RGBA')
            print("Successfully loaded the logo")
        except FileNotFoundError as e:
            print(f"Logo not found at {logo_path.absolute()}, error: {e}")
            raise  # Fail the test if logo is not found
        
        # Resize logo
        logo_size = int(width * 0.2)  # 20% of QR code size to match reference
        logo_img = logo_img.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
        
        # Create white circular background
        circle_size = int(logo_size * 1.3)  # Larger background circle
        circle_img = Image.new('RGBA', (circle_size, circle_size), (0, 0, 0, 0))
        circle_draw = ImageDraw.Draw(circle_img)
        circle_draw.ellipse([0, 0, circle_size-1, circle_size-1], 
                          fill=(255, 255, 255, 255))
        
        # Calculate positions
        circle_pos = ((width - circle_size) // 2, (height - circle_size) // 2)
        logo_pos = ((width - logo_size) // 2, (height - logo_size) // 2)
        
        # Paste the white circle and logo
        img.paste(circle_img, circle_pos, circle_img)
        img.paste(logo_img, logo_pos, logo_img)
        
        # Save with high quality
        output_path = output_directory / "phonon_styled_qr_exact.png"
        img.save(str(output_path), quality=100)  # Maximum quality
        
        assert output_path.exists()
        assert img.size[0] > 0 and img.size[1] > 0 