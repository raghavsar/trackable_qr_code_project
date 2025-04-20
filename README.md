# QR Code Tracking System

A microservices-based system for generating and tracking QR codes for business cards with Phonon branding.

## Overview

The QR Code Tracking System allows users to create, customize, and track digital business cards using QR codes. The system is built using a microservices architecture, with each service responsible for a specific domain of functionality.

## Current Environment: Staging

This repository is currently configured for the **staging environment**. The staging server is accessible at:

- **Server IP**: 192.168.7.60
- **Frontend URL**: http://192.168.7.60:5173
- **API Gateway**: http://192.168.7.60:8000
- **Production Domain**: https://qr.phonon.io (via Caddy reverse proxy)

## Services

1. **API Gateway** (Port 8000)
   - Main entry point for the frontend
   - Handles request routing and authentication

2. **User Service** (Port 8001)
   - Manages user authentication and accounts
   - Handles JWT token generation and validation

3. **VCard Service** (Port 8002)
   - Manages business card creation and editing
   - Provides template management

4. **QR Service** (Port 8003)
   - Generates QR codes for business cards
   - Links QR codes to analytics

5. **Analytics Service** (Port 8004)
   - Tracks QR code scans
   - Provides scan statistics and insights

6. **Redirect Service** (Port 8005)
   - Handles QR code redirects
   - Tracks redirect events

7. **Caddy Reverse Proxy**
   - Handles HTTPS termination
   - Routes requests to appropriate services
   - Manages TLS certificates
   - Serves as the public-facing entry point at qr.phonon.io

## Key Features

- **Branded QR Codes**: Custom QR codes with Phonon branding (blue dots, orange finder patterns)
- **Digital Business Cards**: Create and manage digital business cards
- **Analytics**: Track QR code scans and user interactions
- **Customization**: Customize QR code appearance with different styles and colors
- **Mobile Compatibility**: Optimized for mobile device scanning

## Documentation

### User Documentation
- [User Manual](docs/User_Manual.md) - How to use the QR code system
- [Technical Documentation](docs/Technical_Documentation.md) - System architecture and technical details

### Developer Documentation
- [Setup Guide](docs/Setup_Guide.md) - Instructions for setting up development and staging environments
- [Deployment Guide](docs/Deployment_Guide.md) - Instructions for deploying the application
- [API Documentation](docs/API_Documentation.md) - API endpoints and usage
- [Code Documentation Review](docs/Code_Documentation_Review.md) - Code documentation status and recommendations

### Component Documentation
- [UI Design System](frontend/README-UI-DESIGN-SYSTEM.md) - UI components and design guidelines
- [QR Service](microservices/qr-service/README.md) - QR code generation and styling
- [Caddy Configuration](docs/Caddy_Configuration.md) - Reverse proxy configuration

## Architecture

The system follows a microservices architecture with the following components:

```
┌─────────────────┐     ┌─────────────────┐
│  User Browser   │     │ Device Scanning │
│                 │     │    QR Code      │
└────────┬────────┘     └────────┬────────┘
         │                       │
         ▼                       ▼
┌─────────────────────────────────────────┐
│           Caddy Reverse Proxy           │
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
   └───────┴───────┼───────┴───────────────┘
                   │       
         ┌─────────┴─────┐ 
         │   MongoDB     │ 
         └───────────────┘ 
                  ┌─────────────┐
                  │    MinIO    │
                  └─────────────┘
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for frontend)
- Python 3.11+ (for local development)
- Git

### Starting the Services (Staging)

```bash

# Clone the repository from the internal server (if not already done)
git clone ssh://raghav@192.168.7.60:2222/home/raghav/git_repos/qr_code_project_office.git qr_code_project_office
cd qr_code_project_office

# Make sure you're on the staging branch
git checkout staging

# Start the backend services
cd microservices
docker-compose up -d

# Start the frontend
cd ../frontend
npm install
npm run build
npm run preview

```

## Accessing the Services

- Frontend: http://192.168.7.60:5173
- API Gateway: http://192.168.7.60:8000
- API Documentation: http://192.168.7.60:8000/docs
- MinIO Console: http://192.168.7.60:9001
- Production URL: https://qr.phonon.io (via Caddy)

## Troubleshooting

For common issues and solutions, see the [Troubleshooting Guide](docs/Troubleshooting.md).

## Security Notes

- Change default MongoDB credentials
- Use strong JWT_SECRET in production
- HTTPS is enabled in production via Caddy
- Implement rate limiting
- Regular security updates
