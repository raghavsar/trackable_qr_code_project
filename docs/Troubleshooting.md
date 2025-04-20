# QR Code Tracking System - Troubleshooting Guide

This guide provides solutions for common issues you might encounter when working with the QR Code Tracking System.

## Backend Services

### Service Not Starting

**Symptoms:**
- Docker container fails to start
- Service is not accessible at expected port

**Solutions:**

1. **Check Docker Logs**
   ```bash
   docker-compose logs <service-name>
   ```

2. **Verify Environment Variables**
   - Ensure `.env` file exists and contains all required variables
   - Check for typos or incorrect values

3. **Check Port Conflicts**
   ```bash
   # Check if port is already in use
   netstat -tuln | grep <port-number>
   
   # On Windows
   netstat -ano | findstr <port-number>
   ```

4. **Restart Docker Service**
   ```bash
   # Restart all services
   docker-compose down
   docker-compose up -d
   ```

### Database Connection Issues

**Symptoms:**
- Service logs show database connection errors
- API returns 500 errors

**Solutions:**

1. **Verify MongoDB is Running**
   ```bash
   docker-compose ps mongodb
   ```

2. **Check Connection String**
   - Ensure MONGODB_URL in `.env` is correct
   - Verify username and password

3. **Check Network Connectivity**
   ```bash
   # Test connection to MongoDB
   docker-compose exec api-gateway ping mongodb
   ```

4. **Reset MongoDB Container**
   ```bash
   docker-compose down
   docker volume rm qr_code_project_office_mongodb_data
   docker-compose up -d
   ```

### JWT Authentication Problems

**Symptoms:**
- API returns 401 Unauthorized errors
- Unable to log in or access protected endpoints

**Solutions:**

1. **Verify JWT Secret**
   - Ensure JWT_SECRET is consistent across services
   - Check for whitespace or special characters

2. **Check Token Expiration**
   - Tokens expire after the time specified in JWT_EXPIRATION
   - Request a new token if expired

3. **Validate User Credentials**
   - Ensure user exists in the database
   - Check password is correct

4. **Clear Browser Storage**
   - Clear localStorage and sessionStorage
   - Try logging in again

## Frontend Issues

### Frontend Not Loading

**Symptoms:**
- Blank page
- Console errors in browser developer tools

**Solutions:**

1. **Check Console Errors**
   - Open browser developer tools (F12)
   - Look for errors in the Console tab

2. **Verify API Connection**
   - Ensure VITE_API_URL is set correctly in `.env`
   - Check if API Gateway is accessible

3. **Clear Browser Cache**
   ```
   Ctrl+Shift+Delete in most browsers
   ```

4. **Rebuild Frontend**
   ```bash
   cd frontend
   npm run build
   npm run preview
   ```

### API Connection Errors

**Symptoms:**
- Network errors in console
- "Failed to fetch" errors

**Solutions:**

1. **Check API Gateway Status**
   ```bash
   curl http://192.168.7.60:8000/health
   ```

2. **Verify CORS Configuration**
   - Ensure API Gateway allows requests from frontend origin
   - Check for CORS errors in browser console

3. **Check Network Tab**
   - Open browser developer tools
   - Go to Network tab and look for failed requests

4. **Test API Directly**
   ```bash
   curl -v http://192.168.7.60:8000/api/v1/auth/me -H "Authorization: Bearer YOUR_TOKEN"
   ```

## QR Code Generation Issues

### QR Code Not Generating

**Symptoms:**
- Error when trying to generate QR code
- QR code image not displaying

**Solutions:**

1. **Check QR Service Logs**
   ```bash
   docker-compose logs qr-service
   ```

2. **Verify MinIO Configuration**
   - Ensure MinIO is running: `docker-compose ps minio`
   - Check MinIO credentials in `.env`

3. **Check Favicon Availability**
   - Ensure Phonon favicon is available at the expected path
   - Run the download script if needed:
     ```bash
     cd microservices/qr-service/app/assets
     ./download-favicon.bat
     ```

4. **Test QR Generation Directly**
   ```bash
   curl -X POST http://192.168.7.60:8003/qr/preview \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -d '{"vcard_data":{"first_name":"Test","last_name":"User","email":"test@example.com"}}'
   ```

### QR Code Not Scanning

**Symptoms:**
- QR code generates but doesn't scan
- Scanner app can't recognize the code

**Solutions:**

1. **Check QR Code Size**
   - Ensure QR code is large enough (at least 200x200 pixels)
   - Increase box_size parameter if needed

2. **Verify Error Correction Level**
   - Use higher error correction level (Q or H) for more reliable scanning
   - Especially important when using logos

3. **Check Logo Size**
   - Logo should not cover more than 30% of the QR code
   - Reduce logo_size parameter if scanning fails

4. **Test with Different Scanners**
   - Try multiple QR code scanner apps
   - Test with both iOS and Android devices if possible

## Analytics Issues

### Analytics Not Recording

**Symptoms:**
- Scans not showing up in analytics dashboard
- Scan count not increasing

**Solutions:**

1. **Check Analytics Service Logs**
   ```bash
   docker-compose logs analytics-service
   ```

2. **Verify Redis Connection**
   - Ensure Redis is running: `docker-compose ps redis`
   - Check REDIS_URL in `.env`

3. **Test Scan Event Recording**
   ```bash
   curl -X POST http://192.168.7.60:8004/api/v1/analytics/scan \
     -H "Content-Type: application/json" \
     -d '{"vcard_id":"YOUR_VCARD_ID","action_type":"scan","device_info":{"is_mobile":true}}'
   ```

4. **Check Redirect Service**
   - Ensure redirect service is properly sending events to analytics
   - Test redirect endpoint: `curl -v http://192.168.7.60:8005/r/YOUR_VCARD_ID`

### Real-time Updates Not Working

**Symptoms:**
- Analytics dashboard not updating in real-time
- Need to refresh to see new scans

**Solutions:**

1. **Check SSE Connection**
   - Open browser developer tools
   - Look for EventSource connection in Network tab

2. **Verify Redis Pub/Sub**
   - Ensure Redis is running and accessible
   - Check for errors in analytics service logs

3. **Test SSE Endpoint**
   ```bash
   curl -N http://192.168.7.60:8004/api/v1/analytics/events \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

4. **Restart Analytics Service**
   ```bash
   docker-compose restart analytics-service
   ```

## Storage Issues

### Files Not Uploading to MinIO

**Symptoms:**
- Profile pictures or QR codes not saving
- Storage-related errors in logs

**Solutions:**

1. **Check MinIO Status**
   ```bash
   docker-compose ps minio
   ```

2. **Verify MinIO Configuration**
   - Check MINIO_ENDPOINT, MINIO_ACCESS_KEY, and MINIO_SECRET_KEY in `.env`
   - Ensure MINIO_BUCKET_NAME is correct

3. **Check MinIO Logs**
   ```bash
   docker-compose logs minio
   ```

4. **Access MinIO Console**
   - Open http://192.168.7.60:9001 in browser
   - Log in with access key and secret key
   - Check if bucket exists and is accessible

### Storage URLs Not Working

**Symptoms:**
- Images not displaying
- 404 errors when accessing storage URLs

**Solutions:**

1. **Check URL Format**
   - Ensure storage URLs are properly formatted
   - URLs should be in format: `http://192.168.7.60:8000/api/v1/storage/qrcodes/...`

2. **Verify API Gateway Configuration**
   - Ensure API Gateway is properly routing storage requests
   - Check storage proxy configuration

3. **Test Direct MinIO Access**
   - Try accessing the file directly through MinIO
   - Use MinIO console to verify file exists

4. **Check File Permissions**
   - Ensure bucket policy allows public read access if needed
   - Verify object ACLs in MinIO console

## Environment-Specific Issues

### Staging Environment Issues

**Symptoms:**
- Services work locally but not in staging
- Configuration-related errors

**Solutions:**

1. **Compare Environment Files**
   - Check differences between `.env.dev` and `.env.staging`
   - Ensure all required variables are set correctly

2. **Verify Network Configuration**
   - Ensure services can communicate with each other
   - Check for firewall or network restrictions

3. **Check Server Resources**
   - Verify sufficient CPU, memory, and disk space
   - Monitor resource usage during operation

4. **Review Logs**
   - Check service logs for environment-specific errors
   - Look for configuration or connection issues

## Common Error Messages

### "Connection refused"

**Possible Causes:**
- Service is not running
- Wrong port or hostname
- Firewall blocking connection

**Solutions:**
- Verify service is running: `docker-compose ps`
- Check connection details (hostname, port)
- Check firewall settings

### "Unauthorized"

**Possible Causes:**
- Missing or invalid JWT token
- Token expired
- User not authorized for resource

**Solutions:**
- Obtain a new token by logging in
- Check token expiration
- Verify user permissions

### "Internal Server Error"

**Possible Causes:**
- Unhandled exception in service
- Database query error
- Configuration issue

**Solutions:**
- Check service logs for detailed error
- Verify database connection
- Review service configuration

### "Not Found"

**Possible Causes:**
- Resource doesn't exist
- Wrong URL or endpoint
- Service not registered with API Gateway

**Solutions:**
- Verify resource ID is correct
- Check URL format and spelling
- Ensure service is registered with API Gateway

## Getting Help

If you're still experiencing issues after trying these troubleshooting steps:

1. **Check Documentation**
   - Review service-specific README files
   - Check API documentation

2. **Search Issue Tracker**
   - Look for similar issues in the project's issue tracker
   - Check if there are known bugs or limitations

3. **Contact Support**
   - Provide detailed information about the issue
   - Include relevant logs and error messages
   - Describe steps to reproduce the problem
