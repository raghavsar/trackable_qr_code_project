# QR Code Tracking System - Development Environment Setup

This guide provides instructions for setting up and running the QR Code Tracking System in a local development environment.

## Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for frontend)
- Python 3.11+ (for local development)
- Git

## Local Development Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd qr_code_project_office
```

### 2. Create Development Branch

```bash
git checkout -b dev
```

### 3. Environment Setup

#### Backend (Microservices)

1. Navigate to the microservices directory:
   ```bash
   cd microservices
   ```

2. Copy the development environment file:
   ```bash
   cp .env.dev .env
   ```

3. Start the services using Docker Compose:
   ```bash
   docker-compose up -d
   ```

4. Verify all services are running:
   ```bash
   docker-compose ps
   ```

#### Frontend

1. Navigate to the frontend directory:
   ```bash
   cd ../frontend
   ```

2. Copy the development environment file:
   ```bash
   cp .env.dev .env
   ```

3. Install dependencies:
   ```bash
   npm install
   ```

4. Start the development server:
   ```bash
   npm run dev
   ```

### 4. Accessing the Services

- Frontend: http://localhost:5173
- API Gateway: http://localhost:8000
- MinIO Console: http://localhost:9001
- MongoDB: localhost:27017

### 5. Development Workflow

1. **Making Changes**
   - Create feature branches from `dev`
   - Make your changes
   - Submit pull requests to `dev`

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

### 6. Common Development Tasks

#### Starting Services
```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d <service-name>
```

#### Viewing Logs
```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f <service-name>
```

#### Stopping Services
```bash
# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

#### Rebuilding Services
```bash
# Rebuild all services
docker-compose build

# Rebuild specific service
docker-compose build <service-name>
```

### 7. Troubleshooting

1. **Service Not Starting**
   - Check logs: `docker-compose logs <service-name>`
   - Verify environment variables
   - Check port conflicts

2. **Database Issues**
   - Ensure MongoDB is running
   - Check connection string
   - Verify network connectivity

3. **Frontend Issues**
   - Clear browser cache
   - Check console for errors
   - Verify API endpoints

### 8. Development Best Practices

1. **Code Organization**
   - Follow the established project structure
   - Keep services modular and independent
   - Use shared libraries for common code

2. **Testing**
   - Write unit tests for new features
   - Include integration tests for API endpoints
   - Test edge cases and error scenarios

3. **Documentation**
   - Update API documentation
   - Document complex logic
   - Keep README files up to date

4. **Security**
   - Never commit sensitive data
   - Use environment variables for secrets
   - Follow security best practices

## Support

For development-related issues:
1. Check the project documentation
2. Review existing issues
3. Contact the development team 