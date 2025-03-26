import httpx
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from fastapi.logger import logger
import os
from pydantic_settings import BaseSettings
import json
from typing import Dict, Any
import traceback
from fastapi import HTTPException
import logging
from fastapi import status

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class Settings(BaseSettings):
    ANALYTICS_SERVICE_URL: str = os.getenv("ANALYTICS_SERVICE_URL", "http://analytics-service:8004")
    QR_SERVICE_URL: str = os.getenv("QR_SERVICE_URL", "http://qr-service:8003")

settings = Settings()
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://192.168.7.60:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/t/{tracking_id}")
async def track_scan(tracking_id: str, request: Request):
    """Forward tracking requests to analytics service"""
    try:
        analytics_url = f"{settings.ANALYTICS_SERVICE_URL}/t/{tracking_id}"
        async with httpx.AsyncClient() as client:
            response = await client.post(
                analytics_url,
                headers=dict(request.headers),
                timeout=2.0  # Short timeout for quick response
            )
        return Response(status_code=204)
    except Exception as e:
        logger.error(f"Error forwarding tracking: {e}")
        return Response(status_code=204)  # Silent fail

@app.post("/api/v1/qrcodes")
async def create_qr_code(request: Request):
    """Handle QR code generation requests"""
    try:
        qr_service_url = f"{settings.QR_SERVICE_URL}/qrcodes"
        
        # Get request body once and store it
        body = await request.body()
        
        # Log request details
        logger.info(f"Forwarding request to QR service: {qr_service_url}")
        logger.info(f"Request headers: {dict(request.headers)}")
        
        # Forward the request directly
        async with httpx.AsyncClient() as client:
            response = await client.post(
                qr_service_url,
                headers=dict(request.headers),
                content=body,
                timeout=30.0
            )
            
            logger.info(f"QR service response status: {response.status_code}")
            logger.info(f"QR service response content-type: {response.headers.get('content-type')}")
            
            # Get response content once
            content = await response.aread()
            
            # Return raw response with proper content type
            return Response(
                content=content,
                media_type=response.headers.get("content-type", "image/png"),
                status_code=response.status_code,
                headers={
                    "Content-Type": response.headers.get("content-type", "image/png"),
                    "Content-Length": str(len(content))
                }
            )
            
    except httpx.RequestError as e:
        logger.error(f"QR service connection error: {str(e)}")
        raise HTTPException(status_code=503, detail="QR service is unavailable")
    except Exception as e:
        logger.error(f"Error generating QR code: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analytics/qr/{qr_id}/stream")
async def stream_qr_analytics(
    qr_id: str,
    request: Request,
    access_token: str = None
):
    """Forward SSE streaming requests to analytics service"""
    try:
        # Debug logging for request
        logger.info(f"Received SSE request for QR {qr_id}")
        logger.info(f"Request headers: {dict(request.headers)}")
        logger.info(f"Query params: {dict(request.query_params)}")
        
        # Get access token from multiple possible sources
        if not access_token:
            # Try query params
            access_token = request.query_params.get('access_token')
            logger.info("Got token from query params")
            
        if not access_token:
            # Try Authorization header
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                access_token = auth_header.split(' ')[1]
                logger.info("Got token from Authorization header")
                
        if not access_token:
            logger.error("No access token found in request")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Access token is required"
            )

        logger.info(f"Found access token (first 10 chars): {access_token[:10]}...")

        # Construct analytics service URL with token in both query params and header
        analytics_url = f"{settings.ANALYTICS_SERVICE_URL}/api/v1/analytics/qr/{qr_id}/stream"
        analytics_url += f"?access_token={access_token}"

        # Forward the request as streaming response
        async with httpx.AsyncClient() as client:
            # Include token in both query params and Authorization header
            headers = {
                **dict(request.headers),
                'Accept': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Authorization': f'Bearer {access_token}'
            }
            
            logger.info(f"Forwarding request to analytics service: {analytics_url}")
            logger.info(f"With headers: {headers}")
            
            response = await client.get(
                analytics_url,
                headers=headers,
                timeout=None,  # No timeout for SSE connections
                stream=True  # Enable streaming
            )
            
            if response.status_code != 200:
                error_content = await response.aread()
                logger.error(f"Analytics service error: {error_content}")
                return Response(
                    content=error_content,
                    status_code=response.status_code,
                    media_type=response.headers.get('content-type', 'application/json')
                )
            
            return Response(
                content=response.aiter_raw(),
                media_type="text/event-stream",
                headers={
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'X-Accel-Buffering': 'no',
                    'Access-Control-Allow-Origin': request.headers.get('origin', '*'),
                    'Access-Control-Allow-Credentials': 'true'
                }
            )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in SSE streaming: {str(e)}")
        logger.error(f"Full error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

async def make_request(
    method: str,
    url: str,
    headers: Dict[str, str] = None,
    params: Dict[str, str] = None,
    data: Any = None,
    user_id: str = None
) -> Response:
    """Make a request to an internal service"""
    try:
        # Add user ID to headers if provided
        if user_id and headers:
            headers["X-User-ID"] = user_id

        # Log request details
        logger.info("\n=== Request details ===")
        logger.info(f"URL: {url}")
        logger.info(f"Method: {method}")
        logger.info(f"Headers: {headers}")
        logger.info(f"Params: {params}")
        if data:
            logger.info(f"Data: {json.dumps(data, indent=2)}")

        # Make the request
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=data if data else None,
                timeout=30.0
            )
            
            logger.info(f"HTTP Request: {method} {url} {response.status_code}")
            
            # Get content type and log it
            content_type = response.headers.get("content-type", "").lower()
            logger.info(f"Response content type: {content_type}")
            
            # Special handling for QR code endpoint
            if url.endswith('/qrcodes') and method.upper() == 'POST':
                logger.info("Handling QR code response")
                content = await response.aread()
                return Response(
                    content=content,
                    media_type=content_type or "image/png",
                    status_code=response.status_code,
                    headers={
                        "Content-Type": content_type or "image/png",
                        "Content-Length": str(len(content))
                    }
                )
            
            # Handle other binary responses
            if "image/" in content_type or (response.content and response.content.startswith(b'\x89PNG')):
                logger.info("Detected binary image response")
                return Response(
                    content=response.content,
                    media_type=content_type or "image/png",
                    status_code=response.status_code
                )
            
            # Try JSON for everything else
            try:
                return JSONResponse(
                    content=response.json(),
                    status_code=response.status_code
                )
            except json.JSONDecodeError:
                # If not JSON, return raw response
                return Response(
                    content=response.content,
                    media_type=content_type or "application/octet-stream",
                    status_code=response.status_code
                )
                
    except httpx.RequestError as e:
        logger.error(f"\n=== Error in make_request to {url} ===")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error("Full error details:")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=503, detail=f"Service unavailable: {str(e)}")
    except Exception as e:
        logger.error(f"\n=== Error in make_request to {url} ===")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error("Full error details:")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# ... rest of existing routes ... 