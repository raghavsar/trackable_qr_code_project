from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, Depends, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
try:
    from sse_starlette.sse import EventSourceResponse
except ImportError:
    # Fallback implementation if sse_starlette is not available
    from fastapi.responses import StreamingResponse
    
    class EventSourceResponse(StreamingResponse):
        def __init__(self, content, status_code=200, headers=None, media_type="text/event-stream"):
            if headers is None:
                headers = {}
            headers.setdefault("Cache-Control", "no-cache")
            headers.setdefault("Connection", "keep-alive")
            headers.setdefault("Content-Type", "text/event-stream")
            super().__init__(content, status_code, headers, media_type)
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta
import json
import asyncio
from typing import Dict, List, Optional, Any, AsyncGenerator, Set, TYPE_CHECKING
import logging
import os
import uuid
import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError, DecodeError
from fastapi import status
import traceback
import time
import httpx

from shared.models import PyObjectId, ScanTrackingEvent
from app.database import get_database
from app.redis_store import get_redis_client, RedisStore, DummyRedisClient
from app.config import settings
from app.auth import get_current_user

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase
    import redis.asyncio as redis

# Configure logging
logger = logging.getLogger(__name__)

app = FastAPI(title="Analytics Service")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",  # For development
        # Add your production domains here when ready
        # "https://app.yourdomain.com",
        # "https://api.yourdomain.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Type", "Authorization"]
)

# Helper function to parse datetime strings
def parse_datetime(dt_str):
    if isinstance(dt_str, str):
        try:
            return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        except ValueError:
            try:
                return datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S.%fZ")
            except ValueError:
                try:
                    return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    return datetime.utcnow()
    return dt_str if isinstance(dt_str, datetime) else datetime.utcnow()

class SSEManager:
    def __init__(self):
        self._clients: Dict[str, Set[asyncio.Queue]] = {
            "global": set(),  # Global clients
        }
        self._vcard_clients: Dict[str, Set[asyncio.Queue]] = {}  # VCard-specific clients
        self._latest_metrics: Dict[str, Any] = {}
        self._vcard_metrics: Dict[str, Dict[str, Any]] = {}
        self._client_info: Dict[str, Dict[str, Any]] = {}  # Track client info by client_id
        logger.info("SSE Manager initialized")

    async def register_global(self, client_id: str, queue: asyncio.Queue, client_info: Dict[str, Any]) -> asyncio.Queue:
        """Register a new client for global metrics"""
        if "global" not in self._clients:
            self._clients["global"] = set()
        self._clients["global"].add(queue)
        
        # Track client info
        self._client_info[client_id] = client_info
        
        logger.info(f"Global client registered: {client_id}")
        logger.info(f"Total global clients: {len(self._clients['global'])}")
        
        # Send latest metrics immediately
        if self._latest_metrics:
            # Wrap metrics in the correct event structure
            await queue.put({
                "event": "metrics",
                "data": self._latest_metrics
            })
            logger.info(f"Sent initial metrics to new global client: {client_id}")
        else:
            logger.warning(f"No initial metrics available for new global client: {client_id}")
            
        # Send connection established event
        await queue.put({
            "event": "connection",
            "data": {
                "client_id": client_id,
                "connected_at": client_info["connected_at"],
                "status": "connected"
            }
        })
            
        return queue

    async def register_vcard(self, vcard_id: str, client_id: str, queue: asyncio.Queue, client_info: Dict[str, Any]) -> asyncio.Queue:
        """Register a new client for VCard-specific metrics"""
        if vcard_id not in self._vcard_clients:
            self._vcard_clients[vcard_id] = set()
        self._vcard_clients[vcard_id].add(queue)
        
        # Track client info
        self._client_info[client_id] = client_info
        
        logger.info(f"VCard client registered: {client_id} for VCard {vcard_id}")
        logger.info(f"Total clients for VCard {vcard_id}: {len(self._vcard_clients[vcard_id])}")
        
        # Send latest metrics immediately
        if vcard_id in self._vcard_metrics:
            # Wrap metrics in the correct event structure
            await queue.put({
                "event": "metrics",
                "data": self._vcard_metrics[vcard_id]
            })
            logger.info(f"Sent initial metrics to new VCard client: {client_id}")
        else:
            logger.warning(f"No initial metrics available for new VCard client: {client_id} for VCard {vcard_id}")
        
        # Send connection established event
        await queue.put({
            "event": "connection",
            "data": {
                "client_id": client_id,
                "vcard_id": vcard_id,
                "connected_at": client_info["connected_at"],
                "status": "connected"
            }
        })
            
        return queue

    def remove_client(self, client_id: str) -> None:
        """Remove a client connection by client_id"""
        if client_id in self._client_info:
            client_info = self._client_info[client_id]
            queue = client_info["queue"]
            
            if client_info["type"] == "global":
                if "global" in self._clients:
                    self._clients["global"].discard(queue)
                    logger.info(f"Global client removed: {client_id}")
                    logger.info(f"Remaining global clients: {len(self._clients['global'])}")
            elif client_info["type"] == "vcard":
                vcard_id = client_info["vcard_id"]
                if vcard_id in self._vcard_clients:
                    self._vcard_clients[vcard_id].discard(queue)
                    logger.info(f"VCard client removed: {client_id} for VCard {vcard_id}")
                    logger.info(f"Remaining clients for VCard {vcard_id}: {len(self._vcard_clients[vcard_id])}")
            
            # Remove client info
            del self._client_info[client_id]

    async def broadcast_global(self, metrics: Dict[str, Any]) -> None:
        """Broadcast metrics to all global clients"""
        self._latest_metrics = metrics
        
        # Prepare event data
        event_data = {
            "event": "metrics",
            "data": metrics
        }
        
        # Broadcast to global clients
        if "global" in self._clients:
            dead_clients = []
            for client_queue in self._clients["global"]:
                try:
                    await client_queue.put(event_data)
                except Exception as e:
                    logger.error(f"Error broadcasting to global client: {e}")
                    dead_clients.append(client_queue)
            
            # Remove dead clients
            for client_queue in dead_clients:
                self._clients["global"].discard(client_queue)
                # Find and remove client info
                for client_id, info in list(self._client_info.items()):
                    if info["queue"] == client_queue:
                        del self._client_info[client_id]
                        logger.info(f"Removed dead global client: {client_id}")

    async def broadcast_vcard(self, vcard_id: str, metrics: Dict[str, Any]) -> None:
        """Broadcast metrics to VCard-specific clients"""
        # Store latest metrics for this VCard
        self._vcard_metrics[vcard_id] = metrics
        
        # Prepare event data
        event_data = {
            "event": "metrics",
            "data": metrics
        }
        
        # Broadcast to VCard-specific clients
        if vcard_id in self._vcard_clients:
            dead_clients = []
            for client_queue in self._vcard_clients[vcard_id]:
                try:
                    await client_queue.put(event_data)
                except Exception as e:
                    logger.error(f"Error broadcasting to VCard client for {vcard_id}: {e}")
                    dead_clients.append(client_queue)
            
            # Remove dead clients
            for client_queue in dead_clients:
                self._vcard_clients[vcard_id].discard(client_queue)
                # Find and remove client info
                for client_id, info in list(self._client_info.items()):
                    if info["queue"] == client_queue and info["type"] == "vcard" and info["vcard_id"] == vcard_id:
                        del self._client_info[client_id]
                        logger.info(f"Removed dead VCard client: {client_id} for VCard {vcard_id}")

    async def broadcast(self, metrics: Dict[str, Any]) -> None:
        """Broadcast metrics to all connected clients"""
        try:
            # Broadcast to global clients
            await self.broadcast_global(metrics)
            
            # If metrics contain vcard_id, broadcast to VCard-specific clients
            vcard_id = metrics.get("vcard_id")
            if vcard_id:
                await self.broadcast_vcard(vcard_id, metrics)
                
            logger.debug(f"Broadcast complete. Metrics: {metrics}")
        except Exception as e:
            logger.error(f"Error in broadcast: {e}")
            logger.error(traceback.format_exc())

    async def send_heartbeat(self) -> None:
        """Send heartbeat to all connected clients"""
        try:
            heartbeat_data = {
                "event": "heartbeat",
                "data": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "server_time": datetime.utcnow().isoformat()
                }
            }
            
            # Send to global clients
            if "global" in self._clients:
                for client_queue in self._clients["global"]:
                    try:
                        await client_queue.put(heartbeat_data)
                    except Exception:
                        pass  # Ignore errors, will be cleaned up on next broadcast
            
            # Send to VCard-specific clients
            for vcard_id, clients in self._vcard_clients.items():
                for client_queue in clients:
                    try:
                        heartbeat_data["data"]["vcard_id"] = vcard_id
                        await client_queue.put(heartbeat_data)
                    except Exception:
                        pass  # Ignore errors, will be cleaned up on next broadcast
                        
            logger.debug("Heartbeat sent to all clients")
        except Exception as e:
            logger.error(f"Error sending heartbeat: {e}")

    def get_client_count(self) -> Dict[str, int]:
        """Get count of connected clients"""
        global_count = len(self._clients.get("global", set()))
        vcard_counts = {vcard_id: len(clients) for vcard_id, clients in self._vcard_clients.items()}
        total_count = global_count + sum(vcard_counts.values())
        
        return {
            "total": total_count,
            "global": global_count,
            "vcard": vcard_counts
        }

sse_manager = SSEManager()

@app.on_event("startup")
async def startup_db_client():
    """Initialize database, Redis, SSE manager, and HTTP client on startup"""
    try:
        logger.info("Initializing Analytics Service...")
        
        # Initialize MongoDB client
        app.mongodb_client = AsyncIOMotorClient(settings.MONGODB_URL)
        app.mongodb = app.mongodb_client.get_default_database()
        logger.info(f"Connected to MongoDB: {settings.MONGODB_URL}")
        
        # Initialize Redis client - use DummyRedisClient since Redis is not implemented
        try:
            # Just use DummyRedisClient directly since Redis is not implemented
            from app.redis_store import DummyRedisClient
            app.redis_client = DummyRedisClient()
            logger.warning("Redis is not implemented - using DummyRedisClient for graceful fallback")
        except Exception as redis_error:
            logger.error(f"Failed to initialize Redis client: {redis_error}")
            logger.warning("Redis features will be disabled")
            app.redis_client = None
        
        # Initialize SSE manager
        app.state.sse_manager = SSEManager()
        logger.info("SSE Manager initialized")
        
        # Initialize HTTP client for outgoing requests
        app.http_client = httpx.AsyncClient()
        logger.info("HTTP client initialized")
        
        # Preload initial metrics data into SSE manager
        try:
            initial_metrics = await get_real_time_metrics(app.mongodb)
            logger.info(f"Preloaded initial global metrics: {initial_metrics}")
            await app.state.sse_manager.broadcast_global(initial_metrics)
            logger.info("Initial metrics loaded into SSE manager")
        except Exception as metrics_error:
            logger.error(f"Failed to preload initial metrics: {metrics_error}")
        
        logger.info("Analytics service started successfully")
    except Exception as e:
        logger.error(f"Startup error: {e}")
        logger.error(traceback.format_exc())
        raise

@app.on_event("shutdown")
async def shutdown_db_client():
    """Close connections on shutdown"""
    try:
        if hasattr(app, "mongodb_client"):
            app.mongodb_client.close()
            logger.info("MongoDB connection closed")
            
        if hasattr(app, "http_client"):
            await app.http_client.aclose()
            logger.info("HTTP client closed")
            
        logger.info("Analytics service shutdown complete")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
        logger.error(traceback.format_exc())

async def get_real_time_metrics(db: Any) -> Dict[str, Any]:
    """Get real-time analytics metrics"""
    try:
        # Get total counts
        total_scans = await db.scan_events.count_documents({"action_type": "scan"})
        contact_adds = await db.scan_events.count_documents({"action_type": "contact_add"})
        vcf_downloads = await db.scan_events.count_documents({"action_type": "vcf_download"})
        
        # Get device breakdown
        mobile_scans = await db.scan_events.count_documents({
            "action_type": "scan",
            "device_info.is_mobile": True
        })
        desktop_scans = await db.scan_events.count_documents({
            "action_type": "scan",
            "device_info.is_mobile": False
        })
        
        # Get recent scans (last 10)
        recent_scans_cursor = db.scan_events.find().sort("timestamp", -1).limit(10)
        recent_scans = await recent_scans_cursor.to_list(length=10)
        
        # Format recent scans
        formatted_recent_scans = []
        for scan in recent_scans:
            formatted_scan = {
                "vcard_id": scan.get("vcard_id", ""),
                "timestamp": scan.get("timestamp", datetime.utcnow()).isoformat(),
                "action_type": scan.get("action_type", "scan"),
                "device_info": scan.get("device_info", {})
            }
            formatted_recent_scans.append(formatted_scan)
        
        metrics = {
            "total_scans": total_scans,
            "contact_adds": contact_adds,
            "vcf_downloads": vcf_downloads,
            "mobile_scans": mobile_scans,
            "desktop_scans": desktop_scans,
            "recent_scans": formatted_recent_scans,
            "timestamp": datetime.utcnow().isoformat()
        }
            
        return metrics
    except Exception as e:
        logger.error(f"Error getting real-time metrics: {e}")
        logger.error(traceback.format_exc())
        return {
            "total_scans": 0,
            "contact_adds": 0,
            "vcf_downloads": 0,
            "mobile_scans": 0,
            "desktop_scans": 0,
            "recent_scans": [],
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }

@app.get("/api/v1/analytics/stream")
async def stream_metrics(
    request: Request,
    db: Any = Depends(get_database),
    current_user: dict = Depends(get_current_user)
) -> EventSourceResponse:
    """Generate SSE with real-time metrics using queue-based approach for enhanced reliability"""
    client_id = str(uuid.uuid4())
    logger.info(f"New global SSE connection: {client_id}")
    
    # Create a queue for this client
    client_queue = asyncio.Queue()
    
    # Register connection info
    connection_time = datetime.utcnow().isoformat()
    client_info = {
        "client_id": client_id,
        "connected_at": connection_time,
        "type": "global",
        "user_agent": request.headers.get("user-agent", ""),
        "ip": request.client.host if request.client else "unknown",
        "queue": client_queue
    }
    
    # Ensure SSE manager exists
    if not hasattr(app.state, "sse_manager"):
        app.state.sse_manager = SSEManager()
        logger.info("Created new SSE Manager instance")
    
    # Register client with SSE manager
    await app.state.sse_manager.register_global(client_id, client_queue, client_info)
    
    # Define event generator that listens to the queue
    async def event_generator():
        try:
            # Send immediate global metrics
            metrics = await get_real_time_metrics(db)
            logger.info(f"Sending initial global metrics")
            
            # Send metrics directly in the root with a type field
            metrics["type"] = "global"
            metrics["timestamp"] = datetime.utcnow().isoformat()
            
            yield {
                "event": "metrics",
                "data": json.dumps(metrics)
            }
            
            # Send a connection event
            yield {
                "event": "connection",
                "data": json.dumps({
                    "client_id": client_id,
                    "connected_at": connection_time,
                    "status": "connected"
                })
            }
            
            # Start listening for events from the queue
            while True:
                try:
                    # Wait for new events with a timeout
                    event = await asyncio.wait_for(client_queue.get(), timeout=30)
                    
                    # Check if it's a close event
                    if event.get("event") == "close":
                        logger.info(f"Received close event for global client {client_id}")
                        break
                        
                    # Otherwise yield the event to the client
                    if isinstance(event.get("data"), dict):
                        yield {
                            "event": event.get("event", "message"),
                            "data": json.dumps(event.get("data"))
                        }
                    else:
                        yield {
                            "event": event.get("event", "message"),
                            "data": event.get("data", "")
                        }
                    
                except asyncio.TimeoutError:
                    # Send keep-alive heartbeat event
                    logger.debug(f"Sending keep-alive for global client {client_id}")
                    yield {
                        "event": "heartbeat",
                        "data": json.dumps({
                            "timestamp": datetime.utcnow().isoformat()
                        })
                    }
                except Exception as e:
                    logger.error(f"Error in event generator for global client {client_id}: {e}")
                    logger.error(traceback.format_exc())
                    
                    # Send error event to client
                    yield {
                        "event": "error",
                        "data": json.dumps({
                            "error": str(e)
                        })
                    }
                    
                    # Try to wait and continue
                    await asyncio.sleep(5)
            
        except Exception as outer_e:
            logger.error(f"Fatal error in event generator for global client {client_id}: {outer_e}")
            logger.error(traceback.format_exc())
            
            # Clean up client registration
            app.state.sse_manager.remove_client(client_id)
            
            # Send final error to client
            yield {
                "event": "error",
                "data": json.dumps({
                    "error": str(outer_e),
                    "fatal": True
                })
            }
        finally:
            # Clean up when the generator exits (client disconnected)
            logger.info(f"Global client disconnected: {client_id}")
            app.state.sse_manager.remove_client(client_id)
    
    return EventSourceResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*"
        }
    )

@app.get("/api/v1/analytics/vcard/{vcard_id}/stream")
async def stream_vcard_metrics(
    vcard_id: str,
    request: Request,
    db: Any = Depends(get_database),
    current_user: dict = Depends(get_current_user)
) -> EventSourceResponse:
    """SSE endpoint for real-time metrics of a specific VCard with enhanced error handling"""
    try:
        # Optionally: Verify user owns or has access to this vcard_id
        # user_id_from_token = current_user.get("id")
        # Perform check against DB if necessary...
        # logger.info(f"User {user_id_from_token} requesting stream for vcard {vcard_id}")
        pass
    except Exception as e:
        logger.error(f"Auth/access check failed for vcard stream {vcard_id}: {e}")
        # ... existing code ...
    client_id = str(uuid.uuid4())
    logger.info(f"New VCard SSE connection: {client_id} for VCard {vcard_id}")
    
    # Create a queue for this client
    client_queue = asyncio.Queue()
    
    # Register connection info
    connection_time = datetime.utcnow().isoformat()
    client_info = {
        "client_id": client_id,
        "connected_at": connection_time,
        "type": "vcard",
        "vcard_id": vcard_id,
        "user_agent": request.headers.get("user-agent", ""),
        "ip": request.client.host if request.client else "unknown",
        "queue": client_queue
    }
    
    try:
        # Try as ObjectId first
        vcard = None
        try:
            vcard = await db.vcards.find_one({"_id": PyObjectId(vcard_id)})
        except:
            # Try as string if ObjectId fails
            vcard = await db.vcards.find_one({"_id": vcard_id})
                
        if not vcard:
            logger.error(f"VCard not found for SSE stream: {vcard_id}")
            
            async def error_generator():
                yield {
                    "event": "error",
                    "data": json.dumps({
                        "error": "VCard not found",
                        "vcard_id": vcard_id
                    })
                }
            
            return EventSourceResponse(
                error_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                    "Access-Control-Allow-Origin": "*"
                }
            )
        
        # Register client with SSE manager
        if not hasattr(app.state, "sse_manager"):
            app.state.sse_manager = SSEManager()
            logger.info("Created new SSE Manager instance")
            
        await app.state.sse_manager.register_vcard(vcard_id, client_id, client_queue, client_info)
        
        # Define event generator that listens to the queue
        async def event_generator():
            try:
                # Send immediate VCard metrics
                metrics = await get_vcard_real_time_metrics(db, vcard_id)
                logger.info(f"Sending initial metrics for VCard {vcard_id}")
                
                # Add type and vcard_id at the root level
                metrics["type"] = "vcard"
                metrics["vcard_id"] = vcard_id
                metrics["timestamp"] = datetime.utcnow().isoformat()
                
                yield {
                    "event": "metrics",
                    "data": json.dumps(metrics)
                }
                
                # Send a connection event
                yield {
                    "event": "connection",
                    "data": json.dumps({
                        "client_id": client_id,
                        "vcard_id": vcard_id,
                        "connected_at": connection_time,
                        "status": "connected"
                    })
                }
                
                # Start listening for events from the queue
                while True:
                    try:
                        # Wait for events with a timeout
                        event = await asyncio.wait_for(client_queue.get(), timeout=30)
                        
                        # Check if it's a close event
                        if event.get("event") == "close":
                            logger.info(f"Received close event for client {client_id}")
                            break
                            
                        # Otherwise yield the event to the client
                        if isinstance(event.get("data"), dict):
                            yield {
                                "event": event.get("event", "message"),
                                "data": json.dumps(event.get("data"))
                            }
                        else:
                            yield {
                                "event": event.get("event", "message"),
                                "data": event.get("data", "")
                            }
                        
                    except asyncio.TimeoutError:
                        # Send keep-alive heartbeat event
                        logger.debug(f"Sending keep-alive for client {client_id}")
                        yield {
                            "event": "heartbeat",
                            "data": json.dumps({
                                "timestamp": datetime.utcnow().isoformat()
                            })
                        }
                    except Exception as e:
                        logger.error(f"Error in event generator for client {client_id}: {e}")
                        logger.error(traceback.format_exc())
                        
                        # Send error event to client
                        yield {
                            "event": "error",
                            "data": json.dumps({
                                "error": str(e)
                            })
                        }
                        
                        # Try to wait and continue
                        await asyncio.sleep(5)
                
            except Exception as outer_e:
                logger.error(f"Fatal error in event generator for client {client_id}: {outer_e}")
                logger.error(traceback.format_exc())
                
                # Clean up client registration
                app.state.sse_manager.remove_client(client_id)
                
                # Send final error to client
                yield {
                    "event": "error",
                    "data": json.dumps({
                        "error": str(outer_e),
                        "fatal": True
                    })
                }
            finally:
                # Clean up when the generator exits (client disconnected)
                logger.info(f"Client disconnected: {client_id} for VCard {vcard_id}")
                app.state.sse_manager.remove_client(client_id)
        
        return EventSourceResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream",
                "X-Accel-Buffering": "no",
                "Access-Control-Allow-Origin": "*"
            }
        )
        
    except Exception as e:
        logger.error(f"Error setting up SSE for VCard {vcard_id}, client {client_id}: {e}")
        logger.error(traceback.format_exc())
        
        # Capture the error in local variable to avoid scope issues
        error_message = str(e)
        
        async def error_generator():
            yield {
                "event": "error",
                "data": json.dumps({
                    "error": error_message,
                    "fatal": True
                })
            }
        
        return EventSourceResponse(
            error_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream",
                "X-Accel-Buffering": "no" 
            }
        )

@app.get("/api/v1/analytics/metrics/daily")
async def get_daily_metrics(
    start_date: str,
    end_date: str,
    db: Any = Depends(get_database)
) -> Dict[str, Any]:
    """Get daily analytics metrics for a date range"""
    try:
        logger.info(f"Fetching daily metrics from {start_date} to {end_date}")
        
        # Parse dates
        try:
            start = parse_datetime(start_date)
            end = parse_datetime(end_date)
            # Add one day to end date to include the end date in the range
            end = end + timedelta(days=1)
        except ValueError as e:
            logger.error(f"Invalid date format: {e}")
            return JSONResponse(
                status_code=400,
                content={"error": f"Invalid date format: {str(e)}"}
            )
            
        # Query scan events grouped by date
        pipeline = [
            {
                "$match": {
                    "timestamp": {
                        "$gte": start,
                        "$lt": end
                    }
                }
            },
            {
                "$group": {
                    "_id": {
                        "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
                        "action_type": "$action_type",
                        "is_mobile": {"$ifNull": [{"$getField": {"field": "is_mobile", "input": "$device_info"}}, False]}
                    },
                    "count": {"$sum": 1}
                }
            },
            {
                "$group": {
                    "_id": "$_id.date",
                    "metrics": {
                        "$push": {
                            "action_type": "$_id.action_type",
                            "is_mobile": "$_id.is_mobile",
                            "count": "$count"
                        }
                    }
                }
            },
            {
                "$sort": {"_id": 1}
            }
        ]
        
        # Execute aggregation
        result = await db.scan_events.aggregate(pipeline).to_list(None)
        
        # Process results into daily metrics
        daily_metrics = []
        for day in result:
            date = day["_id"]
            metrics = day["metrics"]
            
            # Initialize counters
            total_scans = 0
            mobile_scans = 0
            desktop_scans = 0
            contact_adds = 0
            vcf_downloads = 0
            
            # Process metrics
            for metric in metrics:
                count = metric["count"]
                action = metric["action_type"]
                is_mobile = metric["is_mobile"]
                
                # Update counters
                if action == "scan":
                    total_scans += count
                    if is_mobile:
                        mobile_scans += count
                    else:
                        desktop_scans += count
                elif action == "contact_add":
                    contact_adds += count
                elif action == "vcf_download":
                    vcf_downloads += count
            
            # Add daily metric
            daily_metrics.append({
                "date": date,
                "total_scans": total_scans,
                "mobile_scans": mobile_scans,
                "desktop_scans": desktop_scans,
                "contact_adds": contact_adds,
                "vcf_downloads": vcf_downloads
            })
        
        # If no data, return empty array
        if not daily_metrics:
            logger.info("No daily metrics found for the specified date range")
            return {"metrics": []}
            
        logger.info(f"Found {len(daily_metrics)} days of metrics")
        return {"metrics": daily_metrics}
        
    except Exception as e:
        logger.error(f"Error getting daily metrics: {e}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"error": f"Error getting daily metrics: {str(e)}"}
        )

@app.get("/health")
async def health_check(request: Request) -> Dict[str, str]:
    """Health check endpoint for the analytics service"""
    try:
        # Check database connection
        db = await get_database(request)
        await db.command("ping")
        
        # Check Redis connection if available
        redis_status = "not_configured"
        try:
            # Import the Redis client function
            from app.redis_store import get_redis_client
            
            # Try to get a Redis client
            redis = await get_redis_client()
            await redis.ping()
            redis_status = "healthy"
        except ImportError:
            # Redis client not configured, but that's okay
            redis_status = "not_configured"
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            redis_status = "unhealthy"
        
        # Check Redis - we know it's using DummyRedisClient since Redis is not implemented
        redis_status = "dummy_client"
        try:
            # Import the DummyRedisClient directly
            from app.redis_store import DummyRedisClient
            
            # Just note we're using the dummy client
            if isinstance(app.redis_client, DummyRedisClient):
                logger.info("Redis health check: using DummyRedisClient")
                redis_status = "using_dummy_client"
            else:
                # If Redis is somehow configured, try to ping it
                await app.redis_client.ping()
                redis_status = "healthy"
        except Exception as e:
            logger.warning(f"Redis health check note: {e}")
            redis_status = "not_implemented"
        
        return {
            "status": "healthy",
            "service": "analytics-service",
            "database": "connected",
            "redis": redis_status,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "analytics-service",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

async def get_vcard_real_time_metrics(db: Any, vcard_id: str) -> Dict[str, Any]:
    """Get real-time analytics metrics for a specific VCard"""
    try:
        logger.info(f"Fetching real-time metrics for VCard: {vcard_id}")
        
        # Get total counts for this VCard
        total_scans = await db.scan_events.count_documents({"vcard_id": vcard_id, "action_type": "scan"})
        contact_adds = await db.scan_events.count_documents({"vcard_id": vcard_id, "action_type": "contact_add"})
        vcf_downloads = await db.scan_events.count_documents({"vcard_id": vcard_id, "action_type": "vcf_download"})
        
        # Get device breakdown
        mobile_scans = await db.scan_events.count_documents({
            "vcard_id": vcard_id,
            "action_type": "scan",
            "device_info.is_mobile": True
        })
        desktop_scans = await db.scan_events.count_documents({
            "vcard_id": vcard_id,
            "action_type": "scan",
            "device_info.is_mobile": False
        })
        
        # Get recent scans for this VCard
        recent_scans_cursor = db.scan_events.find(
            {"vcard_id": vcard_id}
        ).sort("timestamp", -1).limit(10)
        
        recent_scans = await recent_scans_cursor.to_list(length=10)
        
        # Format recent scans
        formatted_recent_scans = []
        for scan in recent_scans:
            formatted_scan = {
                "vcard_id": scan.get("vcard_id", ""),
                "timestamp": scan.get("timestamp", datetime.utcnow()).isoformat(),
                "action_type": scan.get("action_type", "scan"),
                "device_info": scan.get("device_info", {})
            }
            formatted_recent_scans.append(formatted_scan)
        
        # Get hourly distribution (last 24 hours)
        now = datetime.utcnow()
        yesterday = now - timedelta(days=1)
        
        hourly_pipeline = [
            {
                "$match": {
                    "vcard_id": vcard_id,
                    "timestamp": {"$gte": yesterday, "$lte": now},
                    "action_type": "scan"
                }
            },
            {
                "$group": {
                    "_id": {"$hour": "$timestamp"},
                    "count": {"$sum": 1}
                }
            },
            {
                "$sort": {"_id": 1}
            }
        ]
        
        hourly_results = await db.scan_events.aggregate(hourly_pipeline).to_list(None)
        hourly_distribution = {str(item["_id"]): item["count"] for item in hourly_results}
        
        # Get daily distribution (last 7 days)
        week_ago = now - timedelta(days=7)
        
        daily_pipeline = [
            {
                "$match": {
                    "vcard_id": vcard_id,
                    "timestamp": {"$gte": week_ago, "$lte": now},
                    "action_type": "scan"
                }
            },
            {
                "$group": {
                    "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
                    "count": {"$sum": 1}
                }
            },
            {
                "$sort": {"_id": 1}
            }
        ]
        
        daily_results = await db.scan_events.aggregate(daily_pipeline).to_list(None)
        daily_distribution = {item["_id"]: item["count"] for item in daily_results}
        
        # Get interaction breakdown
        interaction_breakdown = {
            "direct_scans": total_scans,
            "vcf_downloads": vcf_downloads,
            "contact_adds": contact_adds
        }
        
        metrics = {
            "vcard_id": vcard_id,
            "total_scans": total_scans,
            "contact_adds": contact_adds,
            "vcf_downloads": vcf_downloads,
            "mobile_scans": mobile_scans,
            "desktop_scans": desktop_scans,
            "recent_scans": formatted_recent_scans,
            "hourly_distribution": hourly_distribution,
            "daily_distribution": daily_distribution,
            "interaction_breakdown": interaction_breakdown,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Real-time metrics for VCard {vcard_id}: {metrics}")
        return metrics
        
    except Exception as e:
        logger.error(f"Error getting real-time metrics for VCard {vcard_id}: {e}")
        logger.error(traceback.format_exc())
        # Return default metrics on error
        return {
            "vcard_id": vcard_id,
            "total_scans": 0,
            "contact_adds": 0,
            "vcf_downloads": 0,
            "mobile_scans": 0,
            "desktop_scans": 0,
            "recent_scans": [],
            "hourly_distribution": {},
            "daily_distribution": {},
            "interaction_breakdown": {
                "direct_scans": 0,
                "vcf_downloads": 0,
                "contact_adds": 0
            },
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }

@app.get("/api/v1/analytics/vcard/{vcard_id}")
async def get_vcard_analytics(
    vcard_id: str,
    timeRange: str = "30d",
    request: Request = None,
    db: Any = Depends(get_database)
) -> Dict[str, Any]:
    """Get analytics for a specific VCard"""
    logger.info(f"Getting analytics for VCard {vcard_id} with timeRange {timeRange}")
    
    try:
        # Get real-time metrics
        real_time_metrics = await get_vcard_real_time_metrics(db, vcard_id)
        
        # Get historical data based on timeRange
        # Parse timeRange (e.g., "30d" for 30 days)
        days = 30  # Default
        if timeRange.endswith("d"):
            try:
                days = int(timeRange[:-1])
            except ValueError:
                logger.warning(f"Invalid timeRange format: {timeRange}, using default 30 days")
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Format dates for query
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")
        
        # Combine real-time and historical data
        result = {
            **real_time_metrics,
            "timeRange": timeRange,
            "start_date": start_date_str,
            "end_date": end_date_str
        }
        
        return result
    except Exception as e:
        logger.error(f"Error getting VCard analytics: {e}")
        logger.error(traceback.format_exc())
        return {
            "error": str(e),
            "vcard_id": vcard_id,
            "timeRange": timeRange
        }

@app.post("/api/v1/analytics/scan")
async def record_scan_event(
    scan_data: ScanTrackingEvent,
    db: Any = Depends(get_database),
    background_tasks: BackgroundTasks = None
):
    """Record a scan event and broadcast to SSE clients"""
    event_id = str(uuid.uuid4())
    
    try:
        # Log the incoming event
        logger.info(f"Recording scan event: {scan_data.dict()}")
        
        # Store in MongoDB
        scan_record = scan_data.dict()
        
        # Parse timestamp if it's a string
        if isinstance(scan_data.timestamp, str):
            try:
                scan_record["timestamp"] = parse_datetime(scan_data.timestamp)
            except Exception as e:
                logger.error(f"Error parsing timestamp: {e}")
                scan_record["timestamp"] = datetime.utcnow()
        
        # Insert into MongoDB
        result = await db.scan_events.insert_one(scan_record)
        inserted_id = str(result.inserted_id)
        logger.info(f"Scan event stored with ID: {inserted_id}")
        
        # Try to record in Redis, but don't worry if it fails since Redis is not implemented
        try:
            # Get a Redis client (will be DummyRedisClient since Redis is not implemented)
            redis_client = await get_redis_client()
            
            # Create a RedisStore that uses the DummyRedisClient
            redis_store = RedisStore(os.getenv("REDIS_URL", "redis://redis:6379/0"))
            
            # This won't actually store the scan, but will log what would have happened
            await redis_store.record_scan(scan_record)
            logger.debug("Scan event processed by Redis handler (using dummy client)")
        except Exception as redis_error:
            # Just log at debug level since Redis isn't expected to work
            logger.debug(f"Redis operation skipped: {redis_error}")
        
        # Ensure SSE manager exists
        if not hasattr(app.state, "sse_manager"):
            app.state.sse_manager = SSEManager()
            logger.info("Created new SSE Manager instance for broadcast")
        
        # STEP 1: Always update global metrics and broadcast to global clients
        try:
            # Get updated global metrics
            global_metrics = await get_real_time_metrics(db)
            
            # Broadcast to global clients
            await app.state.sse_manager.broadcast_global(global_metrics)
            logger.info("Broadcast scan event to global clients")
        except Exception as global_sse_error:
            logger.error(f"Error broadcasting to global SSE clients: {global_sse_error}")
            logger.error(traceback.format_exc())
        
        # STEP 2: If vcard_id is present, also broadcast to VCard-specific clients
        if scan_data.vcard_id:
            try:
                # Get updated metrics for this VCard
                vcard_metrics = await get_vcard_real_time_metrics(db, scan_data.vcard_id)
                
                # Broadcast to VCard-specific clients
                await app.state.sse_manager.broadcast_vcard(scan_data.vcard_id, {
                    "event": "scan",
                    "data": vcard_metrics
                })
                logger.info(f"Broadcast scan event to VCard {scan_data.vcard_id} clients")
            except Exception as sse_error:
                logger.error(f"Error broadcasting to SSE clients: {sse_error}")
                logger.error(traceback.format_exc())
        
        return {"success": True, "event_id": inserted_id}
    except Exception as e:
        logger.error(f"Error recording scan event {event_id}: {e}")
        logger.error(traceback.format_exc())
        # Return an error response, but don't raise an exception to ensure tracking still works
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e), "event_id": event_id}
        )

@app.post("/t/{tracking_id}")
async def track_scan(
    tracking_id: str,
    request: Request,
    db: Any = Depends(get_database),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Handle tracking requests from redirect service"""
    try:
        logger.info(f"Tracking scan for ID: {tracking_id}")
        
        # Check if SSE manager exists
        has_sse_manager = hasattr(app.state, "sse_manager")
        logger.info(f"SSE manager exists: {has_sse_manager}")
        
        if has_sse_manager:
            # Log client counts for debugging
            client_counts = app.state.sse_manager.get_client_count()
            logger.info(f"Connected clients: {client_counts}")
        
        # Try to get user agent and parse device info
        user_agent = request.headers.get("user-agent", "")
        
        # Extract basic device info from user agent
        is_mobile = "mobile" in user_agent.lower() or "android" in user_agent.lower() or "iphone" in user_agent.lower()
        
        # Create scan event data
        scan_data = ScanTrackingEvent(
            event_id=str(uuid.uuid4()),
            vcard_id=tracking_id,  # Use tracking_id as vcard_id
            timestamp=datetime.utcnow(),
            device_info={
                "is_mobile": is_mobile,
                "user_agent": user_agent,
                "ip_address": request.client.host if request.client else None,
            },
            action_type="scan",
            success=True,
            ip_address=request.client.host if request.client else None,
            referrer=request.headers.get("referer", None),
            user_agent=user_agent
        )
        
        # Use background task to record scan to avoid blocking the response
        logger.info(f"Adding background task to record scan event for tracking ID: {tracking_id}")
        background_tasks.add_task(record_scan_event, scan_data, db)
        
        # Return a 204 No Content response to ensure fast response time
        return Response(status_code=204)
    except Exception as e:
        logger.error(f"Error tracking scan for {tracking_id}: {e}")
        logger.error(traceback.format_exc())
        # Return 204 anyway to avoid client errors
        return Response(status_code=204)

@app.get("/api/v1/analytics/metrics/vcard/{vcard_id}/daily")
async def get_vcard_daily_metrics(
    vcard_id: str,
    start_date: str,
    end_date: str,
    db: Any = Depends(get_database)
) -> Dict[str, Any]:
    """Get daily analytics metrics for a specific VCard and date range"""
    try:
        logger.info(f"Fetching daily metrics for VCard {vcard_id} from {start_date} to {end_date}")
        
        # Parse dates
        try:
            start = parse_datetime(start_date)
            end = parse_datetime(end_date)
            # Add one day to end date to include the end date in the range
            end = end + timedelta(days=1)
        except ValueError as e:
            logger.error(f"Invalid date format: {e}")
            return JSONResponse(
                status_code=400,
                content={"error": f"Invalid date format: {str(e)}"}
            )
            
        # Query scan events grouped by date for this specific VCard
        pipeline = [
            {
                "$match": {
                    "vcard_id": vcard_id,
                    "timestamp": {
                        "$gte": start,
                        "$lt": end
                    }
                }
            },
            {
                "$group": {
                    "_id": {
                        "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
                        "action_type": "$action_type",
                        "is_mobile": {"$ifNull": [{"$getField": {"field": "is_mobile", "input": "$device_info"}}, False]}
                    },
                    "count": {"$sum": 1}
                }
            },
            {
                "$group": {
                    "_id": "$_id.date",
                    "metrics": {
                        "$push": {
                            "action_type": "$_id.action_type",
                            "is_mobile": "$_id.is_mobile",
                            "count": "$count"
                        }
                    }
                }
            },
            {
                "$sort": {"_id": 1}
            }
        ]
        
        # Execute aggregation
        result = await db.scan_events.aggregate(pipeline).to_list(None)
        
        # Process results into daily metrics
        daily_metrics = []
        for day in result:
            date = day["_id"]
            metrics = day["metrics"]
            
            # Initialize counters
            total_scans = 0
            mobile_scans = 0
            desktop_scans = 0
            contact_adds = 0
            vcf_downloads = 0
            
            # Process metrics
            for metric in metrics:
                count = metric["count"]
                action = metric["action_type"]
                is_mobile = metric["is_mobile"]
                
                # Update counters
                if action == "scan":
                    total_scans += count
                    if is_mobile:
                        mobile_scans += count
                    else:
                        desktop_scans += count
                elif action == "contact_add":
                    contact_adds += count
                elif action == "vcf_download":
                    vcf_downloads += count
            
            # Add daily metric
            daily_metrics.append({
                "date": date,
                "total_scans": total_scans,
                "mobile_scans": mobile_scans,
                "desktop_scans": desktop_scans,
                "contact_adds": contact_adds,
                "vcf_downloads": vcf_downloads
            })
        
        # If no data, return empty array
        if not daily_metrics:
            logger.info(f"No daily metrics found for VCard {vcard_id} in the specified date range")
            return {"metrics": []}
            
        logger.info(f"Found {len(daily_metrics)} days of metrics for VCard {vcard_id}")
        return {"metrics": daily_metrics}
        
    except Exception as e:
        logger.error(f"Error getting VCard daily metrics: {e}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"error": f"Error getting VCard daily metrics: {str(e)}"}
        )

@app.get("/api/v1/analytics/metrics")
async def get_analytics_metrics(
    timeRange: str = "30d",
    request: Request = None,
    db: Any = Depends(get_database)
) -> Dict[str, Any]:
    """Get global analytics metrics"""
    logger.info(f"Getting global analytics metrics with timeRange {timeRange}")
    
    try:
        # Get real-time metrics
        real_time_metrics = await get_real_time_metrics(db)
        
        # Get historical data based on timeRange
        # Parse timeRange (e.g., "30d" for 30 days)
        days = 30  # Default
        if timeRange.endswith("d"):
            try:
                days = int(timeRange[:-1])
            except ValueError:
                logger.warning(f"Invalid timeRange format: {timeRange}, using default 30 days")
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Format dates for query
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")
        
        # Add type identifier 
        real_time_metrics["type"] = "global"
        
        # Combine real-time and historical data
        result = {
            **real_time_metrics,
            "timeRange": timeRange,
            "start_date": start_date_str,
            "end_date": end_date_str
        }
        
        return result
    except Exception as e:
        logger.error(f"Error getting global analytics metrics: {e}")
        logger.error(traceback.format_exc())
        return {
            "error": str(e),
            "timeRange": timeRange,
            "total_scans": 0,
            "contact_adds": 0,
            "vcf_downloads": 0,
            "mobile_scans": 0,
            "desktop_scans": 0,
            "recent_scans": [],
            "type": "global"
        }

@app.post("/api/v1/analytics/test/broadcast")
@app.post("/test/broadcast")  # Add a simpler route for easier access
async def test_broadcast(
    request: Request,
    db: Any = Depends(get_database)
) -> Dict[str, Any]:
    """Test endpoint to trigger manual broadcast of analytics updates for debugging"""
    try:
        logger.info("Manual broadcast triggered via test endpoint")
        logger.info(f"Request path: {request.url.path}")
        logger.info(f"Request headers: {request.headers}")
        
        # Ensure SSE manager exists
        if not hasattr(app.state, "sse_manager"):
            app.state.sse_manager = SSEManager()
            logger.info("Created new SSE Manager instance for test broadcast")
            
        # Get client counts
        client_counts = app.state.sse_manager.get_client_count()
        logger.info(f"Current clients: {client_counts}")
        
        # Get updated global metrics
        global_metrics = await get_real_time_metrics(db)
        logger.info(f"Broadcasting global metrics: {global_metrics}")
        
        # Broadcast to global clients
        await app.state.sse_manager.broadcast_global(global_metrics)
        logger.info("Test broadcast sent to global clients")
        
        return {
            "success": True,
            "message": "Test broadcast sent successfully",
            "client_counts": client_counts,
            "metrics": global_metrics
        }
    except Exception as e:
        logger.error(f"Error in test broadcast: {e}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )

@app.get("/api/v1/analytics/debug")
@app.get("/debug")  # Simpler route for direct access
async def debug_analytics(
    request: Request,
    db: Any = Depends(get_database)
) -> Dict[str, Any]:
    """Debug endpoint to check the current state of the analytics service"""
    logger.info("Debug endpoint called")
    
    try:
        # Check if SSE manager exists
        has_sse_manager = hasattr(app.state, "sse_manager")
        
        # Get client info
        client_counts = {}
        latest_metrics = {}
        vcard_metrics_count = 0
        
        if has_sse_manager:
            client_counts = app.state.sse_manager.get_client_count()
            latest_metrics = app.state.sse_manager._latest_metrics
            vcard_metrics_count = len(app.state.sse_manager._vcard_metrics)
        
        # Get real-time metrics to check data consistency
        current_metrics = await get_real_time_metrics(db)
        
        # Get some stats from the database
        total_scans = await db.scan_events.count_documents({"action_type": "scan"})
        total_events = await db.scan_events.count_documents({})
        
        # Return all debug info
        return {
            "server_time": datetime.utcnow().isoformat(),
            "has_sse_manager": has_sse_manager,
            "client_counts": client_counts,
            "metrics_cached": bool(latest_metrics),
            "latest_metrics_timestamp": latest_metrics.get("timestamp", "not_available"),
            "vcard_metrics_count": vcard_metrics_count,
            "current_metrics": current_metrics,
            "database_stats": {
                "total_scans": total_scans,
                "total_events": total_events
            }
        }
    except Exception as e:
        logger.error(f"Error in debug endpoint: {e}")
        logger.error(traceback.format_exc())
        return {
            "error": str(e),
            "server_time": datetime.utcnow().isoformat()
        }