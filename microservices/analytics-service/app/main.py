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

from shared.models import PyObjectId, ScanTrackingEvent
from app.database import get_database
from app.redis_store import get_redis_client
from app.config import settings

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

# Configure logging
logger = logging.getLogger(__name__)

app = FastAPI(title="Analytics Service")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development - replace with specific origins in production
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
            await queue.put(self._latest_metrics)
            
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
            await queue.put(self._vcard_metrics[vcard_id])
        
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
async def startup_db_client() -> None:
    """Initialize database connection on startup"""
    logger.info("Starting up analytics service")
    # Connect to MongoDB
    app.mongodb_client = AsyncIOMotorClient(os.getenv("MONGODB_URL"))
    app.mongodb = app.mongodb_client.get_database()
    logger.info("Connected to MongoDB")

@app.on_event("shutdown")
async def shutdown_db_client() -> None:
    """Close database connection on shutdown"""
    logger.info("Shutting down analytics service")
    if hasattr(app, "mongodb_client"):
        app.mongodb_client.close()
        logger.info("Closed MongoDB connection")

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
    db: Any = Depends(get_database)
) -> EventSourceResponse:
    """Generate SSE with real-time metrics"""
    client_id = str(uuid.uuid4())
    logger.info(f"New global SSE connection: {client_id}")
    
    async def event_generator():
        try:
            # Get initial metrics
            metrics = await get_real_time_metrics(db)
            
            # Send initial metrics
            yield {
                "event": "metrics",
                "id": str(uuid.uuid4()),
                "data": json.dumps(metrics)
            }
            
            # Send connection established event
            yield {
                "event": "connection",
                "id": str(uuid.uuid4()),
                "data": json.dumps({
                    "client_id": client_id,
                    "connected_at": datetime.utcnow().isoformat(),
                    "status": "connected"
                })
            }
            
            # Keep connection alive and process updates
            while True:
                if await request.is_disconnected():
                    logger.info(f"Client disconnected: {client_id}")
                    break
                
                # Get updated metrics
                metrics = await get_real_time_metrics(db)
                
                # Send metrics update
                yield {
                    "event": "metrics",
                    "id": str(uuid.uuid4()),
                    "data": json.dumps(metrics)
                }
                
                # Send heartbeat
                yield {
                    "event": "heartbeat",
                    "id": str(uuid.uuid4()),
                    "data": json.dumps({"timestamp": datetime.utcnow().isoformat()})
                }
                
                # Wait before next update
                await asyncio.sleep(5)
                
        except Exception as e:
            logger.error(f"Error in SSE stream for client {client_id}: {e}")
            logger.error(traceback.format_exc())
            
            # Send error event
            yield {
                "event": "error",
                "id": str(uuid.uuid4()),
                "data": json.dumps({"error": str(e), "timestamp": datetime.utcnow().isoformat()})
            }
            
    return EventSourceResponse(event_generator())

@app.get("/api/v1/analytics/vcard/{vcard_id}/stream")
async def stream_vcard_metrics_alt(
    vcard_id: str,
    request: Request,
    db: Any = Depends(get_database)
) -> EventSourceResponse:
    """SSE endpoint for real-time metrics of a specific VCard"""
    client_id = str(uuid.uuid4())
    logger.info(f"New VCard SSE connection: {client_id} for VCard {vcard_id}")
    
    # Validate VCard exists
    vcard = None
    try:
        # Try as ObjectId first
        vcard = await db.vcards.find_one({"_id": PyObjectId(vcard_id)})
    except:
        # If that fails, try as string
        vcard = await db.vcards.find_one({"_id": vcard_id})
        
    if not vcard:
        logger.error(f"VCard not found for SSE stream: {vcard_id}")
        # Return error response
        async def error_generator():
            yield {
                "event": "error",
                "id": str(uuid.uuid4()),
                "data": json.dumps({"error": f"VCard not found: {vcard_id}"})
            }
        return EventSourceResponse(error_generator())
    
    async def event_generator():
        try:
            # Get initial metrics
            metrics = await get_vcard_real_time_metrics(db, vcard_id)
            logger.info(f"Initial metrics for VCard {vcard_id}: {metrics}")
            
            # Send initial metrics
            yield {
                "event": "metrics",
                "id": str(uuid.uuid4()),
                "data": json.dumps(metrics)
            }
            
            # Send connection established event
            yield {
                "event": "connection",
                "id": str(uuid.uuid4()),
                "data": json.dumps({
                    "client_id": client_id,
                    "vcard_id": vcard_id,
                    "connected_at": datetime.utcnow().isoformat(),
                    "status": "connected"
                })
            }
            
            # Keep connection alive and process updates
            while True:
                if await request.is_disconnected():
                    logger.info(f"VCard client disconnected: {client_id} for {vcard_id}")
                    break
                
                # Get updated metrics
                metrics = await get_vcard_real_time_metrics(db, vcard_id)
                
                # Send metrics update
                yield {
                    "event": "metrics",
                    "id": str(uuid.uuid4()),
                    "data": json.dumps(metrics)
                }
                
                # Send heartbeat
                yield {
                    "event": "heartbeat",
                    "id": str(uuid.uuid4()),
                    "data": json.dumps({
                        "timestamp": datetime.utcnow().isoformat(),
                        "vcard_id": vcard_id
                    })
                }
                
                # Wait before next update
                await asyncio.sleep(5)
                
        except Exception as e:
            logger.error(f"Error in VCard SSE stream for client {client_id}: {e}")
            logger.error(traceback.format_exc())
            
            # Send error event
            yield {
                "event": "error",
                "id": str(uuid.uuid4()),
                "data": json.dumps({"error": str(e), "timestamp": datetime.utcnow().isoformat()})
            }
            
    return EventSourceResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization"
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