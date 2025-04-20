# QR Code Tracking System - API Documentation

This document provides an overview of the API endpoints available in the QR Code Tracking System.

## Base URLs

- **Development**: http://localhost:8000
- **Staging**: http://192.168.7.60:8000
- **Production**: https://qr.phonon.io/api

## Authentication

Most API endpoints require authentication using JWT tokens.

### Authentication Headers

```
Authorization: Bearer <token>
```

### Getting a Token

```
POST /api/v1/auth/login
```

Request body:
```json
{
  "email": "user@example.com",
  "password": "your-password"
}
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "60d21b4667d0d8992e610c85",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe"
  }
}
```

## API Gateway Endpoints

The API Gateway serves as the entry point for all client requests and routes them to the appropriate microservices.

### Health Check

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "services": {
    "user-service": "healthy",
    "vcard-service": "healthy",
    "qr-service": "healthy",
    "analytics-service": "healthy",
    "redirect-service": "healthy"
  }
}
```

## User Service Endpoints

### Register User

```
POST /api/v1/auth/register
```

Request body:
```json
{
  "email": "user@example.com",
  "password": "your-password",
  "first_name": "John",
  "last_name": "Doe"
}
```

### Login

```
POST /api/v1/auth/login
```

Request body:
```json
{
  "email": "user@example.com",
  "password": "your-password"
}
```

### Get Current User

```
GET /api/v1/auth/me
```

Response:
```json
{
  "id": "60d21b4667d0d8992e610c85",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe"
}
```

## VCard Service Endpoints

### Create VCard

```
POST /api/v1/vcards
```

Request body:
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "email": "john.doe@example.com",
  "mobile_number": "+1234567890",
  "work_number": "+1987654321",
  "company": "Phonon",
  "title": "Software Engineer",
  "website": "https://example.com",
  "address": {
    "street": "123 Main St",
    "city": "Anytown",
    "state": "CA",
    "zip_code": "12345",
    "country": "USA"
  },
  "notes": "Some notes about this contact"
}
```

### List VCards

```
GET /api/v1/vcards
```

Response:
```json
[
  {
    "_id": "60d21b4667d0d8992e610c85",
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@example.com",
    "mobile_number": "+1234567890",
    "company": "Phonon",
    "qr_code": {
      "image_url": "https://qr.phonon.io/api/v1/storage/qrcodes/users/123/qrcodes/60d21b4667d0d8992e610c85_1624352582.png"
    },
    "created_at": "2023-06-22T10:36:22.123Z",
    "updated_at": "2023-06-22T10:36:22.123Z"
  },
  // More VCards...
]
```

### Get VCard

```
GET /api/v1/vcards/{vcard_id}
```

Response:
```json
{
  "_id": "60d21b4667d0d8992e610c85",
  "first_name": "John",
  "last_name": "Doe",
  "email": "john.doe@example.com",
  "mobile_number": "+1234567890",
  "work_number": "+1987654321",
  "company": "Phonon",
  "title": "Software Engineer",
  "website": "https://example.com",
  "address": {
    "street": "123 Main St",
    "city": "Anytown",
    "state": "CA",
    "zip_code": "12345",
    "country": "USA"
  },
  "notes": "Some notes about this contact",
  "qr_code": {
    "image_url": "https://qr.phonon.io/api/v1/storage/qrcodes/users/123/qrcodes/60d21b4667d0d8992e610c85_1624352582.png"
  },
  "created_at": "2023-06-22T10:36:22.123Z",
  "updated_at": "2023-06-22T10:36:22.123Z"
}
```

### Update VCard

```
PUT /api/v1/vcards/{vcard_id}
```

Request body: Same as create VCard

### Delete VCard

```
DELETE /api/v1/vcards/{vcard_id}
```

### Download VCard as VCF

```
GET /api/v1/vcards/{vcard_id}/download
```

Response: VCF file download

### Get Public VCard

```
GET /api/v1/vcards/public/{vcard_id}
```

## QR Service Endpoints

### Generate QR Code

```
POST /api/v1/qrcodes
```

Request body:
```json
{
  "vcard_id": "60d21b4667d0d8992e610c85",
  "design": {
    "pattern_style": "dots",
    "module_color": "#0f50b5",
    "eye_color": "#ff4d26",
    "background_color": "#FFFFFF",
    "error_correction": "Q",
    "logo_url": "https://example.com/logo.png",
    "logo_size": 0.15
  }
}
```

Response:
```json
{
  "id": "60d21b4667d0d8992e610c86",
  "vcard_id": "60d21b4667d0d8992e610c85",
  "qr_image_url": "https://qr.phonon.io/api/v1/storage/qrcodes/users/123/qrcodes/60d21b4667d0d8992e610c85_1624352582.png",
  "created_at": "2023-06-22T10:36:22.123Z"
}
```

### List QR Codes

```
GET /api/v1/qrcodes
```

### Get QR Code

```
GET /api/v1/qrcodes/{qr_id}
```

### Update QR Code

```
PUT /api/v1/qrcodes/{qr_id}
```

### Delete QR Code

```
DELETE /api/v1/qrcodes/{qr_id}
```

### Preview QR Code

```
POST /api/v1/qrcodes/preview
```

Request body: Same as generate QR code

Response:
```json
{
  "qr_image_base64": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."
}
```

### List QR Templates

```
GET /api/v1/templates
```

### Create QR Template

```
POST /api/v1/templates
```

Request body:
```json
{
  "name": "Phonon Blue",
  "description": "Phonon branded QR code with blue dots",
  "design": {
    "pattern_style": "dots",
    "module_color": "#0f50b5",
    "eye_color": "#ff4d26",
    "background_color": "#FFFFFF",
    "error_correction": "Q",
    "logo_url": "https://example.com/logo.png",
    "logo_size": 0.15
  },
  "is_public": true
}
```

## Analytics Service Endpoints

### Get Dashboard Analytics

```
GET /api/v1/analytics/dashboard
```

Response:
```json
{
  "total_scans": 1234,
  "contact_adds": 567,
  "vcf_downloads": 890,
  "mobile_scans": 987,
  "desktop_scans": 247,
  "recent_scans": [
    {
      "vcard_id": "60d21b4667d0d8992e610c85",
      "timestamp": "2023-06-22T10:36:22.123Z",
      "action_type": "scan",
      "device_info": {
        "is_mobile": true,
        "browser": "Chrome",
        "os": "Android"
      }
    },
    // More scans...
  ],
  "timestamp": "2023-06-22T10:36:22.123Z"
}
```

### Get VCard Analytics

```
GET /api/v1/analytics/vcard/{vcard_id}
```

Response:
```json
{
  "vcard_id": "60d21b4667d0d8992e610c85",
  "total_scans": 123,
  "contact_adds": 45,
  "vcf_downloads": 67,
  "mobile_scans": 89,
  "desktop_scans": 34,
  "recent_scans": [
    // Scan events...
  ],
  "hourly_distribution": {
    "0": 5,
    "1": 2,
    // Hours 0-23...
  },
  "daily_distribution": {
    "2023-06-01": 12,
    "2023-06-02": 15,
    // Dates...
  },
  "interaction_breakdown": {
    "direct_scans": 123,
    "vcf_downloads": 67,
    "contact_adds": 45
  },
  "timestamp": "2023-06-22T10:36:22.123Z"
}
```

### Record Scan Event

```
POST /api/v1/analytics/scan
```

Request body:
```json
{
  "vcard_id": "60d21b4667d0d8992e610c85",
  "timestamp": "2023-06-22T10:36:22.123Z",
  "device_info": {
    "is_mobile": true,
    "device": "iPhone",
    "os": "iOS",
    "browser": "Safari"
  },
  "action_type": "scan",
  "success": true
}
```

### Get Real-time Events (SSE)

```
GET /api/v1/analytics/events
```

Response: Server-Sent Events stream

## Redirect Service Endpoints

### Handle QR Code Scan

```
GET /r/{vcard_id}
```

Response: Redirects to appropriate page based on device type

### Download VCF Directly

```
GET /r/{vcard_id}?format=vcf
```

Response: VCF file download

## Error Responses

All API endpoints return standard error responses:

```json
{
  "detail": "Error message describing the issue"
}
```

Common HTTP status codes:

- `200 OK`: Request succeeded
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid input data
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

## API Documentation

Each service provides Swagger documentation at `/docs`:

- API Gateway: http://192.168.7.60:8000/docs
- User Service: http://192.168.7.60:8001/docs
- VCard Service: http://192.168.7.60:8002/docs
- QR Service: http://192.168.7.60:8003/docs
- Analytics Service: http://192.168.7.60:8004/docs
- Redirect Service: http://192.168.7.60:8005/docs
