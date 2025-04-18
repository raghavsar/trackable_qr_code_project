from fastapi import FastAPI, HTTPException, Depends, Request, status, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import RedirectResponse, StreamingResponse
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
    max_age=3600,  # Cache preflight requests for 1 hour
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

async def forward_request(request: Request, service_url: str, endpoint: str, user_id: Optional[str] = None, override_params: Optional[dict] = None) -> dict:
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
                # If endpoint already has query params, don't add them again
                if "?" in endpoint:
                    # Endpoint already has query parameters
                    params = {}
                    url = f"{service_url}{endpoint}"
                    logger.info(f"Using endpoint with embedded query params: {url}")
                else:
                    # Use query params from request or override
                    params = override_params if override_params is not None else dict(request.query_params)
                    url = f"{service_url}{endpoint}"
                    logger.info(f"Using endpoint with separate query params: {url}, params: {params}")

                response = await client.request(
                    request.method,
                    url,
                    params=params,
                    content=body,
                    headers=headers
                )

                # Get content type
                content_type = response.headers.get("content-type", "").lower()
                logger.info(f"Response content type: {content_type}")

                # Handle VCard responses
                if "text/vcard" in content_type:
                    logger.info("Detected VCard response, forwarding with proper headers")
                    return Response(
                        content=response.content,
                        media_type="text/vcard",
                        status_code=response.status_code,
                        headers={
                            "Content-Type": "text/vcard",
                            "Content-Disposition": response.headers.get("content-disposition"),
                            "Cache-Control": "no-cache"
                        }
                    )

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
@app.post("/v1/auth/register")
async def register(request: Request):
    """Register a new user."""
    return await forward_request(request, settings.USER_SERVICE_URL, "/api/v1/auth/register")

@app.post("/v1/auth/login")
async def login(request: Request):
    """Login with email and password."""
    return await forward_request(request, settings.USER_SERVICE_URL, "/api/v1/auth/login")

@app.get("/v1/auth/google/authorize")
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

@app.get("/v1/auth/google/callback")
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
        # Create a JSON body with the code and redirect_uri
        body_data = {
            "code": code,
            "redirect_uri": "http://localhost:5173/auth/google/callback"
        }

        # Create a custom async generator to yield the body content
        async def receive_body():
            yield {"type": "http.request", "body": json.dumps(body_data).encode(), "more_body": False}

        # Create a modified request with the custom body
        modified_request = Request(
            scope={
                **request.scope,
                "headers": [(k.lower().encode(), v.encode()) for k, v in request.headers.items() if k.lower() != "content-length"] +
                           [(b"content-type", b"application/json")]
            },
            receive=receive_body
        )

        # Use the modified request to forward the request
        response = await forward_request(
            modified_request,
            settings.USER_SERVICE_URL,
            "/api/v1/auth/google/callback"
        )

        if not response.get("access_token"):
            logger.error("No access token in user service response")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get access token"
            )

        # Redirect to frontend with success
        frontend_url = settings.FRONTEND_URL
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

@app.post("/v1/auth/google/callback")
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

@app.get("/v1/auth/me")
async def get_current_user(request: Request, user_id: str = Depends(verify_token)):
    """Get current user profile."""
    logger.info("=== /v1/auth/me endpoint called ===")
    logger.info(f"Authenticated user_id: {user_id}")
    return await forward_request(request, settings.USER_SERVICE_URL, "/api/v1/auth/me", user_id)

@app.post("/v1/auth/refresh")
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
@app.post("/v1/vcards")
async def create_vcard(request: Request, user_id: str = Depends(verify_token)):
    return await forward_request(request, settings.VCARD_SERVICE_URL, "/vcards", user_id)

@app.get("/v1/vcards/{vcard_id}")
async def get_vcard(vcard_id: str, request: Request, user_id: str = Depends(verify_token)):
    return await forward_request(request, settings.VCARD_SERVICE_URL, f"/vcards/{vcard_id}", user_id)

@app.get("/v1/vcards/user/{user_id}")
async def get_user_vcards(user_id: str, request: Request, current_user_id: str = Depends(verify_token)):
    return await forward_request(request, settings.VCARD_SERVICE_URL, f"/vcards/user/{user_id}", current_user_id)

@app.put("/v1/vcards/{vcard_id}")
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

@app.delete("/v1/vcards/{vcard_id}")
async def delete_vcard(vcard_id: str, request: Request, user_id: str = Depends(verify_token)):
    return await forward_request(request, settings.VCARD_SERVICE_URL, f"/vcards/{vcard_id}", user_id)

@app.get("/v1/vcards/{vcard_id}/download")
async def download_vcard(
    request: Request,
    vcard_id: str
):
    """Forward VCard download request to VCard service."""
    try:
        # Add Accept header for VCard
        headers = dict(request.headers)
        headers["Accept"] = "text/vcard"

        # Create new request with updated headers
        modified_request = Request(
            scope=request.scope,
            receive=request.receive,
        )
        modified_request._headers = headers

        # Forward request to VCard service
        response = await forward_request(
            modified_request,
            settings.VCARD_SERVICE_URL,
            f"/vcards/{vcard_id}/download"
        )

        # Return response directly since forward_request now handles VCard responses
        return response

    except Exception as e:
        logger.error(f"Error downloading VCard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error downloading VCard: {str(e)}"
        )

# QR Code routes
@app.post("/v1/qrcodes")
async def create_qr_code(request: Request, user_id: str = Depends(verify_token)):
    """Create a QR code."""
    return await forward_request(request, settings.QR_SERVICE_URL, "/qrcodes", user_id)

@app.get("/v1/qrcodes")
async def list_qr_codes(request: Request, user_id: str = Depends(verify_token)):
    """List all QR codes for the current user."""
    return await forward_request(request, settings.QR_SERVICE_URL, "/qrcodes", user_id)

@app.get("/v1/qrcodes/{qr_id}")
async def get_qr_code(qr_id: str, request: Request, user_id: str = Depends(verify_token)):
    """Get a specific QR code."""
    return await forward_request(request, settings.QR_SERVICE_URL, f"/qrcodes/{qr_id}", user_id)

@app.put("/v1/qrcodes/{qr_id}")
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

@app.get("/v1/qrcodes/vcard/{vcard_id}")
async def get_vcard_qr_code(vcard_id: str, request: Request, user_id: str = Depends(verify_token)):
    """Get QR code for a VCard."""
    return await forward_request(request, settings.QR_SERVICE_URL, f"/qrcodes/vcard/{vcard_id}", user_id)

@app.delete("/v1/qrcodes/{qr_id}")
async def delete_qr_code(qr_id: str, request: Request, user_id: str = Depends(verify_token)):
    """Delete a QR code."""
    return await forward_request(request, settings.QR_SERVICE_URL, f"/qrcodes/{qr_id}", user_id)

# Analytics routes
@app.get("/v1/analytics/metrics")
async def get_global_metrics(request: Request, user_id: str = Depends(verify_token)):
    """Get global analytics metrics."""
    return await forward_request(request, settings.ANALYTICS_SERVICE_URL, "/api/v1/analytics/metrics", user_id)

@app.get("/v1/analytics/vcard/{vcard_id}")
async def get_vcard_analytics(vcard_id: str, request: Request, user_id: str = Depends(verify_token)):
    return await forward_request(request, settings.ANALYTICS_SERVICE_URL, f"/api/v1/analytics/vcard/{vcard_id}", user_id)

@app.get("/v1/analytics/metrics/daily")
async def get_daily_metrics(request: Request, user_id: str = Depends(verify_token)):
    """Get daily analytics metrics for a date range."""
    return await forward_request(request, settings.ANALYTICS_SERVICE_URL, "/api/v1/analytics/metrics/daily", user_id)

@app.get("/v1/analytics/qr/{qr_id}")
async def get_qr_analytics(qr_id: str, request: Request, user_id: str = Depends(verify_token)):
    return await forward_request(request, settings.ANALYTICS_SERVICE_URL, f"/api/v1/analytics/qr/{qr_id}", user_id)

@app.get("/v1/analytics/user/{user_id}")
async def get_user_analytics(user_id: str, request: Request, current_user_id: str = Depends(verify_token)):
    return await forward_request(request, settings.ANALYTICS_SERVICE_URL, f"/api/v1/analytics/user/{user_id}", current_user_id)

@app.post("/v1/analytics/scan")
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

@app.get("/v1/analytics/stream")
async def analytics_stream(
    request: Request,
    access_token: str = None
):
    """Stream real-time analytics metrics."""
    try:
        logger.info("SSE request received for global analytics")
        logger.info(f"Request headers: {dict(request.headers)}")
        logger.info(f"Query params: {dict(request.query_params)}")

        # Get token from query param or header
        if not access_token:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                access_token = auth_header.replace("Bearer ", "")
                logger.info("Token extracted from Authorization header")
            else:
                # Try to get from query params
                access_token = request.query_params.get("access_token") or request.query_params.get("token")
                if access_token:
                    logger.info("Token extracted from query parameters")
                else:
                    logger.warning("No token found in Authorization header or query parameters")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Authentication token is required"
                    )
        else:
            logger.info("Token provided as function parameter")

        # Verify the token
        try:
            payload = jwt.decode(
                access_token,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM]
            )
            user_id = payload.get("sub")
            if not user_id:
                logger.error("Invalid token payload: missing 'sub' field")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication token"
                )
            logger.info(f"Token verified successfully for user {user_id}")
        except jwt.JWTError as e:
            logger.error(f"JWT verification error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )

        # Forward the SSE request to analytics service
        analytics_url = f"{settings.ANALYTICS_SERVICE_URL}/api/v1/analytics/stream"
        logger.info(f"Forwarding SSE request to: {analytics_url}")

        # Create client session with proper headers
        async with httpx.AsyncClient() as client:
            response = await client.get(
                analytics_url,
                headers={
                    'Accept': 'text/event-stream',
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'Authorization': f'Bearer {access_token}'
                },
                timeout=None  # No timeout for SSE
            )

            logger.info(f"Analytics service response status: {response.status_code}")

            return StreamingResponse(
                response.aiter_bytes(),
                media_type="text/event-stream",
                headers={
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'Content-Type': 'text/event-stream',
                    'X-Accel-Buffering': 'no',
                    'Access-Control-Allow-Origin': '*'
                }
            )
    except HTTPException as e:
        logger.error(f"HTTP exception in analytics_stream: {str(e)}")
        raise e
    except Exception as e:
        logger.error(f"Error streaming global analytics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error streaming global analytics: {str(e)}"
        )

@app.get("/v1/analytics/qr/{qr_id}/stream")
async def qr_analytics_stream(
    qr_id: str,
    request: Request,
    access_token: str = None
):
    """Stream real-time analytics metrics for a specific QR code."""
    try:
        logger.info(f"SSE request received for QR {qr_id}")
        logger.info(f"Request headers: {dict(request.headers)}")
        logger.info(f"Query params: {dict(request.query_params)}")

        # Get token from query param or header
        if not access_token:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                access_token = auth_header.replace("Bearer ", "")
                logger.info("Token extracted from Authorization header")
            else:
                # Try to get from query params
                access_token = request.query_params.get("access_token")
                if access_token:
                    logger.info("Token extracted from query parameters")
                else:
                    logger.warning("No token found in Authorization header or query parameters")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Authentication token is required"
                    )
        else:
            logger.info("Token provided as function parameter")

        # Verify the token
        try:
            payload = jwt.decode(
                access_token,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM]
            )
            user_id = payload.get("sub")
            if not user_id:
                logger.error("Invalid token payload: missing 'sub' field")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication token"
                )
            logger.info(f"Token verified successfully for user {user_id}")
        except jwt.JWTError as e:
            logger.error(f"JWT verification error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )

        # Forward the SSE request to analytics service
        analytics_url = f"{settings.ANALYTICS_SERVICE_URL}/api/v1/analytics/qr/{qr_id}/stream"
        logger.info(f"Forwarding SSE request to: {analytics_url}")

        # Create client session with proper headers
        async with httpx.AsyncClient() as client:
            response = await client.get(
                analytics_url,
                headers={
                    'Accept': 'text/event-stream',
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'Authorization': f'Bearer {access_token}'
                },
                timeout=None  # No timeout for SSE
            )

            logger.info(f"Analytics service response status: {response.status_code}")

            return StreamingResponse(
                response.aiter_bytes(),
                media_type="text/event-stream",
                headers={
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'Content-Type': 'text/event-stream',
                    'X-Accel-Buffering': 'no',
                    'Access-Control-Allow-Origin': '*'
                }
            )
    except HTTPException as e:
        logger.error(f"HTTP exception in qr_analytics_stream: {str(e)}")
        raise e
    except Exception as e:
        logger.error(f"Error streaming QR analytics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error streaming QR analytics: {str(e)}"
        )

@app.get("/v1/analytics/vcard/{vcard_id}/stream")
async def vcard_analytics_stream(
    vcard_id: str,
    request: Request,
    access_token: str = None
):
    """Stream real-time analytics metrics for a specific VCard."""
    try:
        logger.info(f"SSE request received for VCard {vcard_id}")
        logger.info(f"Request headers: {dict(request.headers)}")
        logger.info(f"Query params: {dict(request.query_params)}")

        # Get token from query param or header
        if not access_token:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                access_token = auth_header.replace("Bearer ", "")
                logger.info("Token extracted from Authorization header")
            else:
                # Try to get from query params
                access_token = request.query_params.get("access_token")
                if access_token:
                    logger.info("Token extracted from query parameters")
                else:
                    logger.warning("No token found in Authorization header or query parameters")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Authentication token is required"
                    )
        else:
            logger.info("Token provided as function parameter")

        # Verify the token
        try:
            payload = jwt.decode(
                access_token,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM]
            )
            user_id = payload.get("sub")
            if not user_id:
                logger.error("Invalid token payload: missing 'sub' field")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication token"
                )
            logger.info(f"Token verified successfully for user {user_id}")
        except jwt.JWTError as e:
            logger.error(f"JWT verification error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )

        # Forward the SSE request to analytics service
        analytics_url = f"{settings.ANALYTICS_SERVICE_URL}/api/v1/analytics/vcard/{vcard_id}/stream"
        logger.info(f"Forwarding SSE request to: {analytics_url}")

        # Create client session with proper headers
        async with httpx.AsyncClient() as client:
            response = await client.get(
                analytics_url,
                headers={
                    'Accept': 'text/event-stream',
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'Authorization': f'Bearer {access_token}'
                },
                timeout=None  # No timeout for SSE
            )

            logger.info(f"Analytics service response status: {response.status_code}")

            return StreamingResponse(
                response.aiter_bytes(),
                media_type="text/event-stream",
                headers={
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'Content-Type': 'text/event-stream',
                    'X-Accel-Buffering': 'no',
                    'Access-Control-Allow-Origin': '*'
                }
            )
    except HTTPException as e:
        logger.error(f"HTTP exception in vcard_analytics_stream: {str(e)}")
        raise e
    except Exception as e:
        logger.error(f"Error streaming VCard analytics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error streaming VCard analytics: {str(e)}"
        )

@app.get("/v1/health")
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
        "timestamp": datetime.now(datetime.timezone.utc).isoformat(),
        "services": services
    }

@app.get("/v1/vcards/public/{vcard_id}")
async def get_public_vcard(vcard_id: str, request: Request):
    """Get public VCard data without authentication."""
    return await forward_request(request, settings.VCARD_SERVICE_URL, f"/vcards/public/{vcard_id}")

# Redirect service routes
@app.get("/r/{vcard_id}")
async def redirect_vcard(
    vcard_id: str,
    request: Request,
    format: Optional[str] = None,
    action: Optional[str] = None
):
    """Forward redirect requests to the redirect service."""
    try:
        logger.info(f"Forwarding redirect request for VCard {vcard_id}")
        logger.info(f"Query parameters: format={format}, action={action}")

        # Explicitly construct the endpoint with query parameters
        endpoint = f"/r/{vcard_id}"
        params = {}
        if format:
            params["format"] = format
        if action:
            params["action"] = action

        # Add query string if we have parameters
        if params:
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            endpoint = f"{endpoint}?{query_string}"

        logger.info(f"Constructed endpoint: {endpoint}")
        return await forward_request(request, settings.REDIRECT_SERVICE_URL, endpoint)
    except Exception as e:
        logger.error(f"Error forwarding redirect request: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error forwarding redirect request: {str(e)}"
        )

# Add this diagnostic endpoint for testing client IP handling
@app.get("/v1/test-client-ip")
async def get_client_ip(request: Request):
    # This logs the IP Uvicorn directly sees connecting
    client_host = request.client.host
    logger.info(f"Direct client host seen: {client_host}")

    # Log the raw header Uvicorn received
    x_forwarded_for = request.headers.get('x-forwarded-for')
    logger.info(f"X-Forwarded-For header received: {x_forwarded_for}")

    # Also log all request headers for complete debugging
    logger.info("All request headers:")
    for header_name, header_value in request.headers.items():
        logger.info(f"  {header_name}: {header_value}")

    return {
        "client_host": client_host,
        "x_forwarded_for": x_forwarded_for,
        "all_headers": dict(request.headers)
    }

# MinIO proxy endpoint for QR code images
@app.get("/v1/storage/{bucket}/{path:path}")
async def proxy_minio_storage(bucket: str, path: str, request: Request):
    """Proxy requests to MinIO storage."""
    logger.info(f"Proxying MinIO request for bucket: {bucket}, path: {path}")
    logger.info(f"Client IP: {request.client.host if request.client else 'unknown'}")
    logger.info(f"User Agent: {request.headers.get('user-agent', 'unknown')}")

    # Construct the MinIO URL
    minio_url = f"http://minio:9000/{bucket}/{path}"
    logger.info(f"Forwarding to MinIO URL: {minio_url}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Forward the request to MinIO
            response = await client.get(minio_url)

            # Get content type
            content_type = response.headers.get("content-type", "application/octet-stream")
            logger.info(f"MinIO response content type: {content_type}")

            # Return the response with appropriate headers
            return Response(
                content=response.content,
                media_type=content_type,
                status_code=response.status_code,
                headers={
                    "Content-Type": content_type,
                    "Cache-Control": "public, max-age=86400",  # Cache for 24 hours
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, OPTIONS",
                    "Access-Control-Allow-Headers": "*"
                }
            )
    except Exception as e:
        logger.error(f"Error proxying MinIO request: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Storage service unavailable: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )