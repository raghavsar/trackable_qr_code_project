# QR Code Tracking System - Technical Documentation

## 1. System Architecture Overview

The QR Code Tracking System is a comprehensive microservices-based application designed to generate, manage, and track QR codes for business cards. The system follows a modern microservices architecture pattern, with each service responsible for a specific domain of functionality.

### 1.1 High-Level Architecture

The system consists of the following main components:

- **Frontend**: React-based single-page application (SPA) built with Vite and TypeScript
- **API Gateway**: Central entry point for all client requests
- **Microservices**: Specialized services for specific business domains
- **Data Storage**: MongoDB for document storage, Redis for caching, and MinIO for object storage

### 1.2 Architecture Diagram

```
┌─────────────────┐     ┌─────────────────┐
│  User Browser   │     │ Device Scanning │
│                 │     │    QR Code      │
└────────┬────────┘     └────────┬────────┘
         │                       │
         ▼                       ▼
┌─────────────────────────────────────────┐
│           React SPA Frontend            │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│               API Gateway               │
└───┬─────┬─────┬─────┬─────┬─────┬───────┘
    │     │     │     │     │     │
    ▼     ▼     ▼     ▼     ▼     ▼
┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐
│User │ │VCard│ │ QR  │ │Redir│ │Analy│ │Other│
│Serv.│ │Serv.│ │Serv.│ │Serv.│ │Serv.│ │Serv.│
└──┬──┘ └──┬──┘ └──┬──┘ └──┬──┘ └──┬──┘ └──┬──┘
   │       │       │       │       │       │
   └───────┴───────┼───────┴───────┴───────┘
                   │       
         ┌─────────┴─────┐ 
         │   MongoDB     │ 
         └───────────────┘ 
                  ┌─────────────┐
                  │    MinIO    │
                  └─────────────┘
```

## 2. Microservices Description

### 2.1 API Gateway (Port 8000)

The API Gateway serves as the entry point for all client requests and handles:

- Request routing to appropriate microservices
- Authentication and authorization
- CORS configuration
- Rate limiting
- Request/response logging
- Circuit breaking for fault tolerance

**Key Technologies:**
- FastAPI
- JWT authentication
- Circuit breaker pattern

### 2.2 User Service (Port 8001)

The User Service manages all user-related operations:

- User registration and authentication
- Profile management
- JWT token generation and validation
- User permissions and roles

**Key Technologies:**
- FastAPI
- PyJWT
- MongoDB for user data storage
- Bcrypt for password hashing

### 2.3 VCard Service (Port 8002)

The VCard Service handles business card data:

- Creation and management of digital business cards
- Storage of contact information
- VCF file generation
- Integration with QR Service for QR code generation

**Key Technologies:**
- FastAPI
- vobject for VCF generation
- MongoDB for VCard data storage
- MinIO for profile picture storage

### 2.4 QR Service (Port 8003)

The QR Service is responsible for QR code generation:

- QR code creation with custom styling
- Storage of QR code images
- QR code template management
- Integration with VCard Service

**Key Technologies:**
- FastAPI
- qrcode library with custom styling
- PIL/Pillow for image processing
- MinIO for QR code image storage

### 2.5 Analytics Service (Port 8004)

The Analytics Service tracks and analyzes QR code usage:

- Recording scan events
- Aggregating analytics data
- Providing real-time updates via Server-Sent Events (SSE)
- Generating reports and insights

**Key Technologies:**
- FastAPI
- Redis for real-time counters and caching
- MongoDB for aggregated analytics
- SSE for real-time updates

### 2.6 Redirect Service (Port 8005)

The Redirect Service handles QR code scans:

- Processing incoming QR code scans
- Redirecting to appropriate content
- Triggering analytics events
- Handling platform-specific behavior (mobile vs. desktop)

**Key Technologies:**
- FastAPI
- User-agent parsing
- VCF generation for direct contact saving

## 3. QR Code Generation Process

### 3.1 QR Code Generation Flow

1. **Request Initiation**: The frontend sends a request to generate a QR code for a specific VCard
2. **Data Validation**: The API Gateway validates the request and forwards it to the QR Service
3. **QR Code Creation**: The QR Service generates a QR code with the specified design options
4. **Storage**: The generated QR code image is stored in MinIO
5. **Database Update**: The QR code metadata is stored in MongoDB
6. **Response**: The URL to the generated QR code is returned to the client

### 3.2 QR Code Styling

The system supports custom styling of QR codes with the following options:

- **Module Style**: Square, rounded, dots, gapped, vertical, or horizontal
- **Eye Style**: Square or rounded
- **Colors**: Customizable foreground, background, module, and eye colors
- **Logo**: Optional logo embedding with customizable size and background
- **Error Correction**: L, M, Q, or H levels
- **Size**: Customizable box size and border width

### 3.3 QR Code Content

The QR codes contain a URL that points to the Redirect Service, which handles the redirection based on the device type:

- For mobile devices: Offers direct VCF download or contact saving
- For desktop devices: Redirects to a web view of the business card

## 4. Data Flow and Storage

### 4.1 Data Storage Components

- **MongoDB**: Primary database for structured data
  - Collections: users, vcards, qrcodes, scan_events, templates
  - Stores user accounts, VCard data, QR code metadata, and analytics

- **Redis**: In-memory data store for caching and real-time data
  - Caches scan events
  - Maintains real-time counters
  - Supports SSE for live updates

- **MinIO**: S3-compatible object storage
  - Stores QR code images
  - Stores profile pictures
  - Provides public URLs for accessing stored objects

### 4.2 Data Flow Diagram

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Frontend   │────▶│ API Gateway │────▶│ User Service│
└─────────────┘     └─────────────┘     └──────┬──────┘
                           │                    │
                           │                    ▼
                           │             ┌─────────────┐
                           │             │  MongoDB    │
                           │             │ (User Data) │
                           │             └─────────────┘
                           │
                           │            ┌─────────────┐
                           ├───────────▶│VCard Service│
                           │            └──────┬──────┘
                           │                   │
                           │                   ▼
                           │            ┌─────────────┐
                           │            │  MongoDB    │
                           │            │(VCard Data) │
                           │            └─────────────┘
                           │
                           │            ┌─────────────┐
                           ├───────────▶│ QR Service  │
                           │            └──────┬──────┘
                           │                   │
                           │                   ▼
                           │            ┌─────────────┐
                           │            │   MinIO     │
                           │            │ (QR Images) │
                           │            └─────────────┘
                           │
┌─────────────┐           │            ┌─────────────┐
│ QR Scanner  │───────────┼───────────▶│  Redirect   │
└─────────────┘           │            │   Service   │
                          │            └──────┬──────┘
                          │                   │
                          │                   ▼
                          │            ┌─────────────┐
                          └───────────▶│  Analytics  │
                                       │   Service   │
                                       └──────┬──────┘
                                              │
                                              ▼
                                       ┌─────────────┐
                                       │   MongoDB   │
                                       │ (Analytics) │
                                       └─────────────┘
```

## 5. API Endpoints

### 5.1 API Gateway Endpoints

- `GET /api/v1/health`: Health check endpoint
- `POST /api/v1/auth/login`: User login
- `POST /api/v1/auth/register`: User registration
- `GET /api/v1/auth/me`: Get current user info
- `*`: All other endpoints are proxied to the appropriate microservice

### 5.2 User Service Endpoints

- `POST /register`: Register a new user
- `POST /login`: Authenticate a user
- `GET /me`: Get current user profile
- `PUT /me`: Update user profile
- `POST /refresh`: Refresh JWT token

### 5.3 VCard Service Endpoints

- `POST /vcards`: Create a new VCard
- `GET /vcards`: List all VCards for the current user
- `GET /vcards/{vcard_id}`: Get a specific VCard
- `PUT /vcards/{vcard_id}`: Update a VCard
- `DELETE /vcards/{vcard_id}`: Delete a VCard
- `GET /vcards/{vcard_id}/download`: Download VCard as VCF
- `GET /vcards/public/{vcard_id}`: Get public VCard data

### 5.4 QR Service Endpoints

- `POST /api/v1/qrcodes`: Generate a new QR code
- `GET /api/v1/qrcodes`: List QR codes for the current user
- `GET /api/v1/qrcodes/{qr_id}`: Get a specific QR code
- `PUT /api/v1/qrcodes/{qr_id}`: Update a QR code
- `DELETE /api/v1/qrcodes/{qr_id}`: Delete a QR code
- `POST /api/v1/qrcodes/preview`: Preview a QR code without saving
- `GET /api/v1/templates`: List QR code templates
- `POST /api/v1/templates`: Create a new template

### 5.5 Analytics Service Endpoints

- `GET /api/v1/analytics/dashboard`: Get dashboard analytics
- `GET /api/v1/analytics/vcard/{vcard_id}`: Get analytics for a specific VCard
- `POST /api/v1/analytics/scan`: Record a scan event
- `GET /api/v1/analytics/events`: SSE endpoint for real-time events

### 5.6 Redirect Service Endpoints

- `GET /r/{vcard_id}`: Handle QR code scan and redirect
- `GET /r/{vcard_id}?format=vcf`: Download VCF directly

## 6. Security Considerations

### 6.1 Authentication and Authorization

- JWT-based authentication
- Token expiration and refresh mechanism
- Role-based access control
- Secure password storage with bcrypt

### 6.2 Data Protection

- HTTPS for all communications
- Sanitization of user inputs
- Validation of request parameters
- Protection against common web vulnerabilities (XSS, CSRF, etc.)

### 6.3 API Security

- Rate limiting to prevent abuse
- CORS configuration to restrict access
- Input validation and sanitization
- Error handling that doesn't expose sensitive information

### 6.4 Infrastructure Security

- Containerization with Docker
- Network isolation between services
- Principle of least privilege for service accounts
- Regular security updates and patches

## 7. Deployment Guide

### 7.1 Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for frontend development)
- Python 3.11+ (for backend development)
- Git

### 7.2 Development Environment Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd qr_code_project_office
   ```

2. Set up environment variables:
   ```bash
   cd microservices
   cp .env.dev .env
   ```

3. Start the services:
   ```bash
   docker-compose up -d
   ```

4. Set up the frontend:
   ```bash
   cd ../frontend
   cp .env.dev .env
   npm install
   npm run dev
   ```

### 7.3 Production Deployment

1. Configure production environment variables:
   ```bash
   cd microservices
   cp .env.prod .env
   # Edit .env with production values
   ```

2. Build and start the services:
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```

3. Build the frontend for production:
   ```bash
   cd ../frontend
   cp .env.prod .env
   npm install
   npm run build
   ```

4. Serve the frontend using a web server like Nginx or Caddy

### 7.4 Monitoring and Maintenance

- Each service exposes metrics at `/metrics`
- Use Prometheus and Grafana for monitoring
- Check service logs using `docker-compose logs`
- Implement regular database backups
- Set up alerts for service failures

## 8. Troubleshooting

### 8.1 Common Issues

- **Service not starting**: Check logs with `docker-compose logs <service-name>`
- **Database connection issues**: Verify MongoDB connection string and credentials
- **QR code generation failures**: Check MinIO configuration and permissions
- **API Gateway routing errors**: Verify service URLs in the gateway configuration

### 8.2 Debugging Tools

- Service logs: `docker-compose logs -f <service-name>`
- API documentation: Available at `http://localhost:<port>/docs` for each service
- Database inspection: Use MongoDB Compass to inspect the database
- MinIO browser: Access at `http://localhost:9001` to manage objects

### 8.3 Support Resources

- GitHub repository: Available at internal server with user raghav@192.168.7.60
- Documentation: Available in the `docs` directory

