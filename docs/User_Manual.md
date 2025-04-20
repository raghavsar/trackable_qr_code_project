# QR Code Tracking System - User Manual

## 1. Introduction

The QR Code Tracking System allows you to create, customize, and track digital business cards using QR codes. This user manual provides step-by-step instructions on how to use the system effectively.

## 2. Getting Started

### 2.1 Accessing the System

1. Open your web browser and navigate to the application URL (e.g., `https://qr.phonon.io` or `http://192.168.7.60:5173` for the staging environment)
2. Log in with your credentials or register a new account if you don't have one (Google/OAuth ain't working yet)
3. After logging in, you'll be directed to the dashboard where you can manage your QR codes

### 2.2 Dashboard Overview

The dashboard provides an overview of your QR codes and analytics:

- **QR Codes Tab**: Create and manage your QR codes
- **Landing Pages Tab**: (Coming soon) Create custom landing pages
- **Analytics**: View scan statistics and insights

## 3. Creating a Digital Business Card

### 3.1 Creating a New VCard

1. From the dashboard, click on the "QR Codes" tab
2. Click "Create New QR Code" or fill out the form at the top of the page
3. Enter the required information:
   - First Name (required)
   - Last Name (required)
   - Email (required)
   - Mobile Number (optional)
   - Work Number (optional)
   - Company (optional)
   - Title (optional)
   - Website (optional)
   - Address (optional - defaults to Phonon HQ if not provided)
   - Notes (optional)
4. Click "Generate QR Code" to create your digital business card

### 3.2 Uploading a Profile Picture

1. While creating or editing a VCard, click on the profile picture placeholder
2. Select an image file from your device (recommended size: 400x400 pixels)
3. The image will be uploaded and displayed as your profile picture
4. Click "Generate QR Code" to save your changes

## 4. Managing QR Codes

### 4.1 Viewing Your QR Codes

1. Navigate to the "QR Codes" tab on the dashboard
2. Scroll down to see a list of all your QR codes
3. Each QR code card displays:
   - QR code image
   - Contact name
   - Creation date
   - Total scans
   - Action buttons

### 4.2 Editing a QR Code

1. Find the QR code you want to edit in the list
2. Click the "Edit" button (pencil icon)
3. Update the information as needed
4. Click "Save Changes" to update your QR code

### 4.3 Deleting a QR Code

1. Find the QR code you want to delete in the list
2. Click the "Delete" button (trash icon)
3. Confirm the deletion in the popup dialog
4. The QR code will be permanently removed

### 4.4 Downloading a QR Code

1. Find the QR code you want to download in the list
2. Click the "Download" button (download icon)
3. The QR code image will be downloaded to your device
4. You can print this image or use it in your marketing materials

### 4.5 Sharing a QR Code

1. Find the QR code you want to share in the list
2. Click the "Share" button (share icon)
3. Choose from the available sharing options:
   - Copy link
   - Download image
   - Share via email
   - Share via social media

## 5. Tracking and Analytics

### 5.1 Viewing Scan Analytics

1. From the dashboard, find the QR code you want to analyze
2. Click the "Analytics" button (chart icon)
3. The analytics page will display:
   - Total scans
   - Scans over time (daily/weekly/monthly)
   - Device breakdown (mobile vs. desktop)
   - Geographic distribution (if available)
   - Recent scan activity

### 5.2 Understanding Analytics Metrics

- **Total Scans**: The total number of times your QR code has been scanned
- **Contact Adds**: The number of times someone has added your contact to their device
- **VCF Downloads**: The number of times your VCF file has been downloaded
- **Mobile Scans**: The number of scans from mobile devices
- **Desktop Scans**: The number of scans from desktop devices
- **Hourly Distribution**: Shows scan activity by hour of the day
- **Daily Distribution**: Shows scan activity by day of the week

### 5.3 Real-time Updates

The analytics dashboard provides real-time updates when someone scans your QR code:
1. Keep the analytics page open
2. When someone scans your QR code, you'll see the scan appear in the Recent Activity section
3. The metrics will update automatically without refreshing the page

## 6. How QR Codes Work

### 6.1 QR Code Technology

QR codes (Quick Response codes) are two-dimensional barcodes that can be scanned using a smartphone camera or QR code reader app. They can store various types of data, including:

- Text
- URLs
- Contact information (vCard)
- Phone numbers
- Email addresses
- Wi-Fi credentials
- And more

### 6.2 Our QR Code Implementation

In our system, QR codes are used to share digital business cards:

1. **QR Code Generation**: When you create a VCard, a QR code is generated that contains a unique URL
2. **QR Code Scanning**: When someone scans your QR code with their smartphone camera, they are directed to this URL
3. **Redirection**: The system detects the device type and provides the appropriate experience:
   - Mobile devices: Offers to save the contact directly to the phone's contacts
   - Desktop devices: Shows a web page with your contact information and download options
4. **Tracking**: Each scan is recorded in the analytics system, allowing you to track usage

### 6.3 QR Code Best Practices

For optimal results with your QR codes:

- **Size**: Print QR codes at least 2 x 2 cm (0.8 x 0.8 inches) in size
- **Quiet Zone**: Ensure there's a white border around the QR code (the system adds this automatically)
- **Contrast**: Maintain high contrast between the QR code and its background
- **Testing**: Always test your QR code before distributing it widely
- **Context**: Provide instructions or context near the QR code to encourage scanning
- **Error Correction**: Use higher error correction levels (Q or H) if you add a logo or if the code might get damaged

## 7. Printing and Sharing QR Codes

### 7.1 Printing Recommendations

For best results when printing QR codes:

1. **Resolution**: Use high-resolution images (the system provides these by default)
2. **Size**: Print QR codes at least 2 x 2 cm (0.7 x 0.7 inches) in size
3. **Paper Quality**: Use smooth, non-glossy paper for better scanning
4. **Ink**: Ensure good print quality with clear contrast
5. **Testing**: Always test the printed QR code with multiple devices before mass production

### 7.2 Digital Sharing

To share your QR code digitally:

1. Download the QR code image from the system
2. Include it in:
   - Email signatures
   - Digital business cards
   - Social media profiles
   - Websites
   - Digital presentations
   - Marketing materials

### 7.3 Physical Applications

QR codes can be applied to various physical items:

- Business cards
- Brochures and flyers
- Product packaging
- Posters and banners
- Name badges
- Trade show materials
- Office signage

## 8. Troubleshooting

### 8.1 QR Code Not Scanning

If your QR code isn't scanning properly:

1. **Size**: Ensure the QR code is large enough (at least 2 x 2 cm)
2. **Lighting**: Try scanning in better lighting conditions
3. **Distance**: Hold the camera at an appropriate distance (not too close or too far)
4. **Damage**: Check if the QR code is damaged or distorted
5. **Contrast**: Ensure there's sufficient contrast between the QR code and background
6. **Camera**: Make sure your camera lens is clean and focused
7. **App**: Try using a dedicated QR code scanner app if the built-in camera app doesn't work

### 8.2 Contact Not Saving

If the contact isn't saving to a mobile device:

1. **Permissions**: Ensure the device has granted permission to save contacts
2. **Format**: Try downloading the VCF file manually and importing it
3. **Device Compatibility**: Some older devices may have limited vCard compatibility
4. **Required Fields**: Make sure all required fields (first name, last name, email) are filled in your VCard

### 8.3 Analytics Issues

If analytics aren't showing up correctly:

1. **Delay**: There might be a slight delay in processing scan events
2. **Refresh**: Try refreshing the analytics page
3. **Filters**: Check if any filters are applied that might be hiding data
4. **Browser**: Try using a different browser or clearing your cache

