# QR Code Styling in Phonon QR Service

This service provides QR code generation with custom styling specifically for Phonon's brand identity.

## Key Features

- **Data Modules**: Uses circular dots pattern in Phonon blue (#0f50b5)
- **Finder Patterns**: Rounded corners in Phonon orange (#ff4d26) 
- **Logo Integration**: Automatically embeds the Phonon favicon in the center of the QR code

## Setting Up

1. **Ensure Favicon Is Available**:
   - The Phonon favicon should be located at `/app/assets/Phonon_Favicon.png` in the Docker container
   - Run the download script to get the latest favicon:
     ```
     cd microservices/qr-service/app/assets
     ./download-favicon.bat
     ```

2. **Default Style Configuration**:
   - The default QR style is configured in the generation endpoints with:
     - Data modules: Blue dots (#0f50b5)
     - Finder patterns: Orange-red rounded corners (#ff4d26)
     - White background (#FFFFFF)
     - Logo size: 15% of QR code size

## Testing

To test the QR code generation with the custom styling:

1. Place the Phonon favicon in the `app/assets` directory
2. Run the test script:
   ```
   cd microservices/qr-service
   python -m app.test_qr
   ```
3. Check the generated QR code in the `test_output` directory

## Implementation Details

- `CustomEyeDrawer` class: Handles the rounded finder patterns
- `generate_vcard_qr` function: Applies Phonon branding to QR codes
- QR code endpoints: Automatically apply Phonon branding to all generated QR codes 