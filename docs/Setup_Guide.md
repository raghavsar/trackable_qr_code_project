# QR Code Tracking System - Setup Guide

This guide provides instructions for setting up the QR Code Tracking System in both development and staging environments.

## Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for frontend)
- Python 3.11+ (for local development)
- Git

## Staging Environment Setup

The staging environment is currently running on server 192.168.7.60.

### 1. Server Access

```bash
ssh -p 2222 raghav@192.168.7.60
```

### 2. Repository Setup

```bash
cd qr_code_project_office

# Make sure you're on the staging branch
git checkout staging
```

### 3. Backend Setup

```bash
# Navigate to the microservices directory
cd microservices

# Copy the staging environment file
cp .env.staging .env

# Start the services
docker-compose up -d

# Verify services are running
docker-compose ps
```

### 4. Frontend Setup

```bash
# Navigate to the frontend directory
cd ../frontend

# Copy the staging environment file
cp .env.staging .env

# Install dependencies
npm install

# Build the application
npm run build

# Start the production server
npm run preview
```

### 5. Accessing Staging Services

- Frontend: http://192.168.7.60:5173
- API Gateway: http://192.168.7.60:8000
- MinIO Console: http://192.168.7.60:9001
- MongoDB: 192.168.7.60:27017

## Development Environment Setup

For local development, follow these steps:

### 1. Repository Setup

```bash
# Clone the repository
git clone ssh://raghav@192.168.7.60:2222/home/raghav/git_repos/qr_code_project.git qr_code_project_office
cd qr_code_project_office

# Create a development branch (if needed)
git checkout -b dev
```

### 2. Backend Setup

```bash
# Navigate to the microservices directory
cd microservices


# Start the services
docker-compose up -d

# Verify services are running
docker-compose ps
```

### 3. Frontend Setup

```bash
# Navigate to the frontend directory
cd ../frontend


# Install dependencies
npm install

# Start the development server
npm run dev
```

### 4. Accessing Development Services

- Frontend: http://localhost:5173
- API Gateway: http://localhost:8000
- MinIO Console: http://localhost:9001
- MongoDB: localhost:27017

## Environment Configuration

### Backend Environment Variables

Create a `.env` file in the microservices directory with the following variables:

```env
# MongoDB Connection
MONGODB_URL=mongodb://admin:adminpassword@mongodb:27017/qr_code_db?authSource=admin&directConnection=true

# Redis Connection
REDIS_URL=redis://redis:6379

# JWT Authentication
JWT_SECRET=your-super-secret
JWT_ALGORITHM=HS256
JWT_EXPIRATION=3600

# Frontend URL
FRONTEND_URL=http://localhost:5173  # For development
# FRONTEND_URL=http://192.168.7.60:5173  # For staging

# Service URLs (for API Gateway)
USER_SERVICE_URL=http://user-service:8001
VCARD_SERVICE_URL=http://vcard-service:8002
QR_SERVICE_URL=http://qr-service:8003
ANALYTICS_SERVICE_URL=http://analytics-service:8004
REDIRECT_SERVICE_URL=http://redirect-service:8005

# MinIO Configuration
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=qr_service_user
MINIO_SECRET_KEY=qr_service_password_123
MINIO_BUCKET_NAME=qrcodes
MINIO_USE_SSL=false
```

### Frontend Environment Variables

Create a `.env` file in the frontend directory with the following variables:

```env
# API URL
VITE_API_URL=http://localhost:8000  # For development
VITE_API_URL=http://192.168.7.60:8000  # For staging
VITE_API_URL=https://qr.phonon.io/api  # For production

# Other Configuration
VITE_APP_TITLE=QR Code Generator
```

## Common Development Tasks

### Starting Services

```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d <service-name>
```

### Viewing Logs

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f <service-name>
```

### Stopping Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### Rebuilding Services

```bash
# Rebuild all services
docker-compose build

# Rebuild specific service
docker-compose build <service-name>
```

## Development Workflow

1. **Making Changes**
   - Create feature branches from `staging` or `dev`
   - Make your changes
   - Submit pull requests to the appropriate branch

2. **Testing**
   - Run unit tests:
     ```bash
     cd microservices
     pytest
     ```
   - Run integration tests:
     ```bash
     pytest tests/integration
     ```

3. **Code Quality**
   - Follow PEP 8 style guide for Python code
   - Use ESLint and Prettier for frontend code
   - Write unit tests for new features

## Troubleshooting

### Service Not Starting

- Check logs: `docker-compose logs <service-name>`
- Verify environment variables
- Check port conflicts

### Database Issues

- Ensure MongoDB is running
- Check connection string
- Verify network connectivity

### Frontend Issues

- Clear browser cache
- Check console for errors
- Verify API endpoints
