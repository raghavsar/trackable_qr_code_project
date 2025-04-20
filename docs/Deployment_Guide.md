# QR Code Tracking System - Deployment Guide

This guide provides instructions for deploying the QR Code Tracking System to different environments.

## Current Environment: Staging

The system is currently deployed to the staging environment at 192.168.7.60.

## Deployment Workflow

### Staging Deployment

1. **Prepare for Deployment**

   ```bash
   # SSH into the staging server
   ssh -p 2222 raghav@192.168.7.60
   
   # Navigate to the project directory
   cd qr_code_project_office
   
   # Make sure you're on the staging branch
   git checkout staging
   
   # Pull the latest changes
   git pull origin staging
   ```

2. **Deploy Backend Services**

   ```bash
   # Navigate to the microservices directory
   cd microservices
   
   # Stop the current services
   docker-compose down
   
   # Rebuild the services
   docker-compose build
   
   # Start the services
   docker-compose up -d
   
   # Verify services are running
   docker-compose ps
   ```

3. **Deploy Frontend**

   ```bash
   # Navigate to the frontend directory
   cd ../frontend
   
   # Install dependencies
   npm install
   
   # Build the application
   npm run build
   
   # Start the production server
   npm run preview
   ```

4. **Verify Deployment**

   - Check that all services are running: `docker-compose ps`
   - Access the frontend: http://192.168.7.60:5173
   - Test API endpoints: http://192.168.7.60:8000/health

### Production Deployment (Future)

For future production deployment, follow these steps:

1. **Prepare Production Environment**

   - Set up a production server with Docker and Docker Compose
   - Configure domain names and SSL certificates
   - Set up a reverse proxy (Nginx or Caddy)

2. **Configure Production Environment Variables**

   ```bash
   # Create production environment files
   cp .env.prod .env
   cd frontend
   cp .env.prod .env
   ```

   Update the environment variables with production values:
   - Set secure JWT_SECRET
   - Configure proper MONGODB_URL
   - Set production FRONTEND_URL
   - Enable SSL for services

3. **Deploy to Production**

   ```bash
   # Deploy backend services
   cd microservices
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   
   # Deploy frontend
   cd ../frontend
   npm install
   npm run build
   
   # Copy build files to web server directory
   cp -r dist/* /var/www/html/
   ```

## Deployment Configuration

### Docker Compose Production Overrides

Create a `docker-compose.prod.yml` file with production-specific configurations:

```yaml
version: '3.8'

services:
  api-gateway:
    restart: always
    environment:
      - NODE_ENV=production
      - JWT_SECRET=${JWT_SECRET}
      - FRONTEND_URL=${FRONTEND_URL}
    
  user-service:
    restart: always
    environment:
      - NODE_ENV=production
      - JWT_SECRET=${JWT_SECRET}
    
  vcard-service:
    restart: always
    environment:
      - NODE_ENV=production
    
  qr-service:
    restart: always
    environment:
      - NODE_ENV=production
    
  analytics-service:
    restart: always
    environment:
      - NODE_ENV=production
    
  redirect-service:
    restart: always
    environment:
      - NODE_ENV=production
    
  mongodb:
    restart: always
    volumes:
      - mongodb_data_prod:/data/db
    
  redis:
    restart: always
    volumes:
      - redis_data_prod:/data
    
  minio:
    restart: always
    volumes:
      - minio_data_prod:/data

volumes:
  mongodb_data_prod:
  redis_data_prod:
  minio_data_prod:
```

### Nginx Configuration (Production)

For production, you might want to use Nginx as a reverse proxy:

```nginx
server {
    listen 80;
    server_name qr.phonon.io;
    
    # Redirect HTTP to HTTPS
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name qr.phonon.io;
    
    ssl_certificate /etc/letsencrypt/live/qr.phonon.io/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/qr.phonon.io/privkey.pem;
    
    # Frontend
    location / {
        proxy_pass http://localhost:5173;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # API Gateway
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # MinIO
    location /minio {
        proxy_pass http://localhost:9001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Monitoring and Maintenance

### Viewing Logs

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f <service-name>
```

### Health Checks

- API Gateway: http://192.168.7.60:8000/health
- Analytics Service: http://192.168.7.60:8004/health
- Other services: Check individual service health endpoints

### Database Maintenance

```bash
# Backup database
docker-compose exec mongodb mongodump --out /backup

# Restore database
docker-compose exec mongodb mongorestore /backup
```

### Updating Services

```bash
# Pull latest changes
git pull origin staging

# Rebuild and restart services
docker-compose down
docker-compose build
docker-compose up -d
```

## Rollback Procedure

If a deployment fails, follow these steps to rollback:

1. **Identify the Issue**

   Check the logs to identify the problem:
   ```bash
   docker-compose logs -f
   ```

2. **Rollback to Previous Version**

   ```bash
   # Checkout the previous working commit
   git checkout <previous-commit-hash>
   
   # Rebuild and restart services
   cd microservices
   docker-compose down
   docker-compose build
   docker-compose up -d
   
   # Rebuild frontend
   cd ../frontend
   npm install
   npm run build
   npm run preview
   ```

3. **Verify Rollback**

   - Check that all services are running
   - Test key functionality
   - Monitor logs for errors

## Security Considerations

1. **Access Control**
   - Use strong passwords
   - Implement IP whitelisting
   - Regular security updates
   - Monitor access logs

2. **Data Protection**
   - Regular backups
   - Encrypted communication
   - Secure environment variables
   - Access logging

3. **Monitoring**
   - Set up alerts
   - Monitor resource usage
   - Track error rates
   - Log analysis
