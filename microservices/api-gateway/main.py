from fastapi import FastAPI, HTTPException, Depends, Request, status, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import RedirectResponse
import httpx
import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from datetime import datetime, timedelta
import logging
from config import settings
from typing import Optional, Callable
import json
from circuit_breaker import circuit_breaker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.SERVICE_NAME,
    version=settings.VERSION
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"],  # Expose all headers
    max_age=settings.CORS_MAX_AGE,  # Cache preflight requests
)

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Verify JWT token and return user_id."""
    try:
        token = credentials.credentials
        logger.info("=== Starting token verification ===")
        logger.info(f"Token prefix: {token[:20]}...")
        
        try:
            # Log JWT secret configuration
            logger.info(f"Using JWT algorithm: {settings.JWT_ALGORITHM}")
            logger.info(f"JWT secret key length: {len(settings.JWT_SECRET)}")
            
            # Decode without verification first to check token structure
            logger.info("Attempting preliminary token decode without verification")
            unverified_payload = jwt.decode(token, options={"verify_signature": False})
            logger.info(f"Preliminary token payload: {json.dumps(unverified_payload)}")
            
            # Now decode with verification
            logger.info("Attempting token verification with signature")
            payload = jwt.decode(
                token,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM]
            )
            logger.info(f"Token successfully verified. Full payload: {json.dumps(payload)}")
            
            user_id = payload.get("sub")
            if not user_id:
                logger.error("Token payload missing 'sub' claim")
                logger.info("Available claims: " + ", ".join(payload.keys()))
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: missing user ID"
                )
                
            logger.info(f"Successfully extracted user_id: {user_id}")
            return user_id
            
        except ExpiredSignatureError:
            logger.error("Token validation failed: Token has expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except InvalidTokenError as e:
            logger.error(f"Token validation failed: Invalid token structure - {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}"
            )
            
    except Exception as e:
        logger.error("=== Token verification failed ===")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error("Full error details:", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token verification failed"
        )

async def forward_request(request: Request, service_url: str, endpoint: str, user_id: Optional[str] = None) -> dict:
    """Forward request to microservice with circuit breaker and authenticated user info."""
    service_name = service_url.split("://")[-1].split(":")[0]
    
    async def make_request():
        try:
            logger.info("\n=== Starting request forwarding ===")
            logger.info(f"Target URL: {service_url}{endpoint}")
            logger.info(f"Method: {request.method}")
            logger.info(f"User ID: {user_id}")
            logger.info(f"Query params: {request.query_params}")
            
            # Get request body if present
            body = await request.body()
            
            # Prepare headers
            headers = dict(request.headers)
            if "host" in headers:
                del headers["host"]
            
            # Add auth headers if user is authenticated
            if user_id:
                logger.info("\n=== Adding authentication headers ===")
                auth_header = request.headers.get("Authorization")
                if auth_header:
                    headers["Authorization"] = auth_header
                    logger.info("Authorization header forwarded")
                headers["X-User-ID"] = user_id
                logger.info(f"X-User-ID header set: {user_id}")
                
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Include query parameters in the request
                params = dict(request.query_params)
                response = await client.request(
                    request.method,
                    f"{service_url}{endpoint}",
                    params=params,
                    content=body,
                    headers=headers
                )
                
                # Get content type
                content_type = response.headers.get("content-type", "").lower()
                logger.info(f"Response content type: {content_type}")
                
                # Handle binary responses (like QR codes)
                if "image/" in content_type or (response.content and response.content.startswith(b'\x89PNG')):
                    logger.info("Detected binary response, returning raw content")
                    return Response(
                        content=response.content,
                        media_type=content_type or "image/png",
                        status_code=response.status_code,
                        headers={
                            "Content-Type": content_type or "image/png",
                            "Content-Length": str(len(response.content))
                        }
                    )
                
                # Handle JSON responses
                try:
                    response_data = response.json()
                    if response.status_code >= 400:
                        raise HTTPException(
                            status_code=response.status_code,
                            detail=response_data.get("detail", "Request failed")
                        )
                    return response_data
                except json.JSONDecodeError:
                    # If not JSON and not binary, return raw response
                    return Response(
                        content=response.content,
                        media_type=content_type or "application/octet-stream",
                        status_code=response.status_code
                    )
                    
        except Exception as e:
            logger.error(f"\n=== Error in forward_request to {service_name} ===")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error message: {str(e)}")
            logger.error("Full error details:", exc_info=True)
            raise e

    try:
        return await circuit_breaker.call_service(service_name, make_request)
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service {service_name} is currently unavailable"
        )

# Auth routes
@app.post("/api/v1/auth/register")
async def register(request: Request):
    """Register a new user."""
    return await forward_request(request, settings.USER_SERVICE_URL, "/api/v1/auth/register")

@app.post("/api/v1/auth/login")
async def login(request: Request):
    """Login with email and password."""
    return await forward_request(request, settings.USER_SERVICE_URL, "/api/v1/auth/login")

@app.get("/api/v1/auth/google/authorize")
async def init_google_login(request: Request):
    """Initialize Google OAuth flow."""
    try:
        logger.info("Received Google login init request")
        logger.info(f"Query params: {request.query_params}")
        
        return await forward_request(request, settings.USER_SERVICE_URL, "/api/v1/auth/google/authorize")
        
    except Exception as e:
        logger.error(f"Error initializing Google login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/api/v1/auth/google/callback")
async def google_callback_redirect(request: Request):
    """Handle Google OAuth redirect."""
    try:
        code = request.query_params.get("code")
        state = request.query_params.get("state")
        error = request.query_params.get("error")
        
        logger.info("Received Google callback request")
        logger.info(f"Code: {code}")
        logger.info(f"State: {state}")
        
        if error:
            logger.error(f"Google OAuth error: {error}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Google OAuth error: {error}"
            )
            
        if not code:
            logger.error("No authorization code in query parameters")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Authorization code is required"
            )
            
        # Exchange code for tokens
        response = await forward_request(
            request,
            settings.USER_SERVICE_URL,
            "/api/v1/auth/google/callback",
            override_body={
                "code": code,
                "redirect_uri": "http://localhost:5173/auth/google/callback"
            }
        )
        
        if not response.get("access_token"):
            logger.error("No access token in user service response")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get access token"
            )
            
        # Redirect to frontend with success
        frontend_url = settings.CORS_ORIGINS[0]
        return RedirectResponse(
            url=f"{frontend_url}/auth/google/success?token={response['access_token']}",
            status_code=status.HTTP_302_FOUND
        )
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error in Google callback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.post("/api/v1/auth/google/callback")
async def google_callback(request: Request):
    """Handle Google OAuth callback from frontend."""
    try:
        body = await request.json()
        logger.info("Received Google callback request")
        logger.info(f"Request body: {json.dumps(body)}")
        
        if not body.get("code"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Authorization code is required"
            )
            
        if not body.get("redirect_uri"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Redirect URI is required"
            )
            
        response = await forward_request(
            request,
            settings.USER_SERVICE_URL,
            "/api/v1/auth/google/callback"
        )
        
        if not response.get("access_token"):
            logger.error("No access token in user service response")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get access token"
            )
            
        return response
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error in Google callback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/api/v1/auth/me")
async def get_current_user(request: Request, user_id: str = Depends(verify_token)):
    """Get current user profile."""
    logger.info("=== /api/v1/auth/me endpoint called ===")
    logger.info(f"Authenticated user_id: {user_id}")
    return await forward_request(request, settings.USER_SERVICE_URL, "/api/v1/auth/me", user_id)

@app.post("/api/v1/auth/refresh")
async def refresh_token(request: Request):
    """Refresh access token using refresh token."""
    try:
        body = await request.json()
        refresh_token = body.get("refresh_token")
        
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Refresh token is required"
            )
            
        return await forward_request(
            request,
            settings.USER_SERVICE_URL,
            "/api/v1/auth/refresh"
        )
        
    except Exception as e:
        logger.error(f"Error refreshing token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# VCard routes
@app.post("/api/v1/vcards")
async def create_vcard(request: Request, user_id: str = Depends(verify_token)):
    return await forward_request(request, settings.VCARD_SERVICE_URL, "/vcards", user_id)

@app.get("/api/v1/vcards/{vcard_id}")
async def get_vcard(vcard_id: str, request: Request, user_id: str = Depends(verify_token)):
    return await forward_request(request, settings.VCARD_SERVICE_URL, f"/vcards/{vcard_id}", user_id)

@app.get("/api/v1/vcards/user/{user_id}")
async def get_user_vcards(user_id: str, request: Request, current_user_id: str = Depends(verify_token)):
    return await forward_request(request, settings.VCARD_SERVICE_URL, f"/vcards/user/{user_id}", current_user_id)

@app.put("/api/v1/vcards/{vcard_id}")
async def update_vcard(vcard_id: str, request: Request, user_id: str = Depends(verify_token)):
    """Update a VCard."""
    try:
        # Forward the request to the VCard service
        response = await forward_request(
            request,
            settings.VCARD_SERVICE_URL,
            f"/vcards/{vcard_id}",
            user_id
        )
        return response
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error updating VCard: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error updating VCard: {str(e)}"
        )

@app.delete("/api/v1/vcards/{vcard_id}")
async def delete_vcard(vcard_id: str, request: Request, user_id: str = Depends(verify_token)):
    return await forward_request(request, settings.VCARD_SERVICE_URL, f"/vcards/{vcard_id}", user_id)

# QR Code routes
@app.post("/api/v1/qrcodes")
async def create_qr_code(request: Request, user_id: str = Depends(verify_token)):
    """Create a QR code."""
    return await forward_request(request, settings.QR_SERVICE_URL, "/qrcodes", user_id)

@app.get("/api/v1/qrcodes")
async def list_qr_codes(request: Request, user_id: str = Depends(verify_token)):
    """List all QR codes for the current user."""
    return await forward_request(request, settings.QR_SERVICE_URL, "/qrcodes", user_id)

@app.get("/api/v1/qrcodes/{qr_id}")
async def get_qr_code(qr_id: str, request: Request, user_id: str = Depends(verify_token)):
    """Get a specific QR code."""
    return await forward_request(request, settings.QR_SERVICE_URL, f"/qrcodes/{qr_id}", user_id)

@app.put("/api/v1/qrcodes/{qr_id}")
async def update_qr_code(qr_id: str, request: Request, user_id: str = Depends(verify_token)):
    """Update a QR code."""
    try:
        logger.info(f"Updating QR code {qr_id} for user {user_id}")
        response = await forward_request(
            request,
            settings.QR_SERVICE_URL,
            f"/qrcodes/{qr_id}",
            user_id
        )
        return response
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error updating QR code: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error updating QR code: {str(e)}"
        )

@app.get("/api/v1/qrcodes/vcard/{vcard_id}")
async def get_vcard_qr_code(vcard_id: str, request: Request, user_id: str = Depends(verify_token)):
    """Get QR code for a VCard."""
    return await forward_request(request, settings.QR_SERVICE_URL, f"/qrcodes/vcard/{vcard_id}", user_id)

@app.delete("/api/v1/qrcodes/{qr_id}")
async def delete_qr_code(qr_id: str, request: Request, user_id: str = Depends(verify_token)):
    """Delete a QR code."""
    return await forward_request(request, settings.QR_SERVICE_URL, f"/qrcodes/{qr_id}", user_id)

# Analytics routes
@app.get("/api/v1/analytics/vcard/{vcard_id}")
async def get_vcard_analytics(vcard_id: str, request: Request, user_id: str = Depends(verify_token)):
    return await forward_request(request, settings.ANALYTICS_SERVICE_URL, f"/api/v1/analytics/vcard/{vcard_id}", user_id)

@app.get("/api/v1/analytics/qr/{qr_id}")
async def get_qr_analytics(qr_id: str, request: Request, user_id: str = Depends(verify_token)):
    return await forward_request(request, settings.ANALYTICS_SERVICE_URL, f"/api/v1/analytics/qr/{qr_id}", user_id)

@app.get("/api/v1/analytics/user/{user_id}")
async def get_user_analytics(user_id: str, request: Request, current_user_id: str = Depends(verify_token)):
    return await forward_request(request, settings.ANALYTICS_SERVICE_URL, f"/api/v1/analytics/user/{user_id}", current_user_id)

@app.post("/api/v1/analytics/scan")
async def record_scan(request: Request):
    """Record a scan event."""
    try:
        return await forward_request(
            request,
            settings.ANALYTICS_SERVICE_URL,
            "/api/v1/analytics/scan"
        )
    except Exception as e:
        logger.error(f"Error recording scan: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error recording scan: {str(e)}"
        )

@app.get("/api/v1/health")
async def health_check():
    """Check health of all services."""
    services = {
        "gateway": {
            "status": "healthy",
            "version": settings.VERSION
        }
    }
    
    # Check all microservices
    async with httpx.AsyncClient(timeout=5.0) as client:
        service_checks = [
            ("user", settings.USER_SERVICE_URL),
            ("vcard", settings.VCARD_SERVICE_URL),
            ("qr", settings.QR_SERVICE_URL),
            ("analytics", settings.ANALYTICS_SERVICE_URL)
        ]
        
        for name, url in service_checks:
            try:
                response = await client.get(f"{url}/health")
                if response.status_code == 200:
                    services[name] = response.json()
                else:
                    services[name] = {
                        "status": "unhealthy",
                        "error": f"Status code: {response.status_code}"
                    }
            except Exception as e:
                logger.error(f"Health check failed for {name}: {str(e)}")
                services[name] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
    
    # Determine overall health
    overall_status = all(
        service.get("status") == "healthy"
        for service in services.values()
    )
    
    return {
        "status": "healthy" if overall_status else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "services": services
    }

@app.get("/api/v1/vcards/public/{vcard_id}")
async def get_public_vcard(vcard_id: str, request: Request):
    """Get public VCard data without authentication."""
    return await forward_request(request, settings.VCARD_SERVICE_URL, f"/vcards/public/{vcard_id}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    ) 