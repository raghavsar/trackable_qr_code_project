# QR Code Tracking System - Staging Environment Setup

This guide provides instructions for setting up and managing the QR Code Tracking System in the staging environment.

## Server Information

- **Server IP**: 192.168.7.60
- **SSH Port**: 2222
- **SSH User**: raghav
- **SSH Command**: `ssh -p 2222 raghav@192.168.7.60`

## Prerequisites

- Docker and Docker Compose installed on the server
- SSH access to the staging server
- Git

## Staging Environment Setup

### 1. Initial Server Setup

1. SSH into the staging server:
   ```bash
   ssh -p 2222 raghav@192.168.7.60
   ```

2. Clone the repository:
   ```bash
   git clone <repository-url>
   cd qr_code_project_office
   ```

3. Create and switch to staging branch:
   ```bash
   git checkout -b staging
   ```

### 2. Environment Configuration

#### Backend (Microservices)

1. Navigate to the microservices directory:
   ```bash
   cd microservices
   ```

2. Copy the staging environment file:
   ```bash
   cp .env.staging .env
   ```

3. Start the services:
   ```bash
   docker-compose up -d
   ```

4. Verify services are running:
   ```bash
   docker-compose ps
   ```

#### Frontend

1. Navigate to the frontend directory:
   ```bash
   cd ../frontend
   ```

2. Copy the staging environment file:
   ```bash
   cp .env.staging .env
   ```

3. Install dependencies:
   ```bash
   npm install
   ```

4. Build the application:
   ```bash
   npm run build
   ```

5. Start the production server:
   ```bash
   npm run preview
   ```

### 3. Accessing the Services

- Frontend: http://192.168.7.60:5173
- API Gateway: http://192.168.7.60:8000
- MinIO Console: http://192.168.7.60:9001
- MongoDB: 192.168.7.60:27017

### 4. Deployment Workflow

1. **Deploying Changes**
   ```bash
   # Pull latest changes
   git pull origin staging

   # Rebuild and restart services
   docker-compose down
   docker-compose build
   docker-compose up -d
   ```

2. **Frontend Deployment**
   ```bash
   cd frontend
   npm install
   npm run build
   npm run preview
   ```

### 5. Monitoring and Maintenance

1. **Viewing Logs**
   ```bash
   # All services
   docker-compose logs -f

   # Specific service
   docker-compose logs -f <service-name>
   ```

2. **Health Checks**
   - API Gateway: http://192.168.7.60:8000/health
   - Analytics Service: http://192.168.7.60:8004/health
   - Other services: Check individual service health endpoints

3. **Database Maintenance**
   ```bash
   # Backup database
   docker-compose exec mongodb mongodump --out /backup

   # Restore database
   docker-compose exec mongodb mongorestore /backup
   ```

### 6. Troubleshooting

1. **Service Issues**
   - Check service logs
   - Verify environment variables
   - Check network connectivity
   - Verify port availability

2. **Database Issues**
   - Check MongoDB logs
   - Verify connection string
   - Check disk space
   - Verify backup status

3. **Frontend Issues**
   - Check build logs
   - Verify environment variables
   - Check browser console
   - Verify API connectivity

### 7. Security Considerations

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

### 8. Backup and Recovery

1. **Database Backup**
   ```bash
   # Create backup
   docker-compose exec mongodb mongodump --out /backup

   # Restore from backup
   docker-compose exec mongodb mongorestore /backup
   ```

2. **Configuration Backup**
   ```bash
   # Backup environment files
   cp .env .env.backup
   cp frontend/.env frontend/.env.backup
   ```

3. **Recovery Procedures**
   - Document recovery steps
   - Test recovery process
   - Maintain backup schedule
   - Verify backup integrity

## Support

For staging environment issues:
1. Check service logs
2. Review monitoring alerts
3. Contact system administrator
4. Document issues and resolutions 