# QR Code Tracking System

A microservices-based system for generating and tracking QR codes for business cards.

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

## Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for frontend)
- Python 3.11+ (for local development)

## Environment Setup

1. Create a `.env` file in each service directory with the following template:
   ```env
   MONGODB_URL=mongodb://admin:adminpassword@mongodb:27017/qr_code_db?authSource=admin&directConnection=true
   REDIS_URL=redis://redis:6379
   JWT_SECRET=your-super-secret
   PORT=<service-specific-port>
   FRONTEND_URL=http://localhost:3000
   ```

2. For the API Gateway, add additional service URLs:
   ```env
   USER_SERVICE_URL=http://user-service:8001
   VCARD_SERVICE_URL=http://vcard-service:8002
   QR_SERVICE_URL=http://qr-service:8003
   ANALYTICS_SERVICE_URL=http://analytics-service:8004
   REDIRECT_SERVICE_URL=http://redirect-service:8005
   ```

## Running the Services

1. Start all services using Docker Compose:
   ```bash
   docker-compose up -d
   ```

2. Monitor the logs:
   ```bash
   docker-compose logs -f
   ```

3. Check service health:
   ```bash
   docker-compose ps
   ```

## Development Setup

1. Create a Python virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```

3. Run individual services (for development):
   ```bash
   cd <service-directory>
   uvicorn app.main:app --reload --port <service-port>
   ```

## API Documentation

Each service provides Swagger documentation at `/docs`:
- API Gateway: http://localhost:8000/docs
- User Service: http://localhost:8001/docs
- VCard Service: http://localhost:8002/docs
- QR Service: http://localhost:8003/docs
- Analytics Service: http://localhost:8004/docs
- Redirect Service: http://localhost:8005/docs

## Testing

1. Run unit tests:
   ```bash
   pytest
   ```

2. Run integration tests:
   ```bash
   pytest tests/integration
   ```

## Deployment

1. Update environment variables for production:
   - Set secure JWT_SECRET
   - Configure proper MONGODB_URL
   - Set production FRONTEND_URL

2. Build and push Docker images:
   ```bash
   docker-compose build
   docker-compose push
   ```

3. Deploy using Docker Compose:
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```

## Monitoring

- Each service exposes metrics at `/metrics`
- Use Prometheus and Grafana for monitoring
- Check service logs using `docker-compose logs`

## Security Notes

- Change default MongoDB credentials
- Use strong JWT_SECRET in production
- Enable HTTPS in production
- Implement rate limiting
- Regular security updates

## Troubleshooting

1. **Service not starting:**
   - Check logs: `docker-compose logs <service-name>`
   - Verify environment variables
   - Check MongoDB connection

2. **Database connection issues:**
   - Ensure MongoDB is running
   - Check connection string
   - Verify network connectivity

3. **Authentication problems:**
   - Verify JWT_SECRET is consistent
   - Check token expiration
   - Validate user credentials 