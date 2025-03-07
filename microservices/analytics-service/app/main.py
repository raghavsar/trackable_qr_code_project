from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, Depends, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
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

from shared.models import PyObjectId, ScanTrackingEvent
from app.database import get_database
from app.redis_store import get_redis_client
from app.config import settings

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

# Configure logging
logger = logging.getLogger(__name__)

app = FastAPI(title="Analytics Service")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://192.168.7.154:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SSEManager:
    def __init__(self):
        self._clients: Set[asyncio.Queue] = set()
        self._latest_metrics: Dict[str, Any] = {}

    async def register(self, client: Request) -> asyncio.Queue:
        """Register a new client connection"""
        client_queue = asyncio.Queue()
        self._clients.add(client_queue)
        try:
            # Send latest metrics immediately upon connection
            if self._latest_metrics:
                await client_queue.put(self._latest_metrics)
            return client_queue
        except:
            self._clients.remove(client_queue)
            raise

    def remove(self, client_queue: asyncio.Queue) -> None:
        """Remove a client connection"""
        self._clients.remove(client_queue)

    async def broadcast(self, metrics: Dict[str, Any]) -> None:
        """Broadcast metrics to all connected clients"""
        self._latest_metrics = metrics
        for client_queue in self._clients:
            try:
                await client_queue.put(metrics)
            except:
                # Remove dead clients
                self.remove(client_queue)

sse_manager = SSEManager()

# Database connection
@app.on_event("startup")
async def startup_db_client() -> None:
    app.mongodb_client = AsyncIOMotorClient(os.getenv("MONGODB_URL"))
    app.mongodb = app.mongodb_client.get_database()

@app.on_event("shutdown")
async def shutdown_db_client() -> None:
    app.mongodb_client.close()

async def get_real_time_metrics(db: Any) -> Dict[str, Any]:
    """Get current analytics metrics"""
    try:
        # Get metrics for the last 24 hours
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=24)
        
        pipeline = [
            {
                "$match": {
                    "timestamp": {"$gte": start_time, "$lte": end_time},
                    "action_type": {"$in": ["scan", "vcf_download", "contact_add"]}  # Include all relevant actions
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_scans": {"$sum": 1},  # Count all interactions as scans
                    "contact_adds": {
                        "$sum": {"$cond": [{"$eq": ["$action_type", "contact_add"]}, 1, 0]}
                    },
                    "vcf_downloads": {
                        "$sum": {"$cond": [{"$eq": ["$action_type", "vcf_download"]}, 1, 0]}
                    }
                }
            }
        ]
        
        result = await db.scan_events.aggregate(pipeline).to_list(1)
        metrics = result[0] if result else {
            "total_scans": 0,
            "contact_adds": 0,
            "vcf_downloads": 0
        }
        
        # Get recent scans (including page_view for visibility)
        recent_scans = await db.scan_events.find(
            sort=[("timestamp", -1)],
            limit=5
        ).to_list(5)
        
        metrics["recent_scans"] = [
            {
                "timestamp": scan["timestamp"].isoformat(),
                "action_type": scan["action_type"],
                "device_info": scan["device_info"]
            }
            for scan in recent_scans
        ]
        
        # Remove MongoDB _id
        if "_id" in metrics:
            del metrics["_id"]
            
        return metrics
        
    except Exception as e:
        logger.error(f"Error getting real-time metrics: {e}")
        return {
            "total_scans": 0,
            "contact_adds": 0,
            "vcf_downloads": 0,
            "recent_scans": []
        }

async def event_generator(request: Request, db: Any):
    """Generate SSE events with real-time metrics."""
    client_id = str(uuid.uuid4())
    logger.info(f"New client connected: {client_id}")
    
    try:
        while True:
            # Get current metrics
            metrics = await get_real_time_metrics(db)
            
            # Format as SSE event
            event_data = json.dumps(metrics)
            yield f"data: {event_data}\n\n"
            
            # Wait before sending next update
            await asyncio.sleep(2)  # Send updates every 2 seconds
            
    except Exception as e:
        logger.error(f"Error in event generator for client {client_id}: {e}")
    finally:
        logger.info(f"Client disconnected: {client_id}")

@app.post("/api/v1/analytics/scan")
async def record_scan(
    scan_data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    db: Any = Depends(get_database)
) -> JSONResponse:
    """Record a scan event"""
    try:
        # Validate required fields
        if "vcard_id" not in scan_data:
            return JSONResponse(
                status_code=400,
                content={"error": "Missing vcard_id field"}
            )
            
        vcard_id = scan_data["vcard_id"]
        
        # Try to find VCard with either ObjectId or string
        vcard = None
        try:
            # Try as ObjectId first
            vcard = await db.vcards.find_one({"_id": PyObjectId(vcard_id)})
        except:
            # If that fails, try as string
            vcard = await db.vcards.find_one({"_id": vcard_id})
            
        if not vcard:
            return JSONResponse(
                status_code=404,
                content={"error": f"VCard not found: {vcard_id}"}
            )
            
        # Create scan event
        scan_event = {
            "vcard_id": vcard_id,
            "timestamp": datetime.utcnow(),
            "user_agent": scan_data.get("user_agent", ""),
            "ip_address": scan_data.get("ip_address", ""),
            "action_type": scan_data.get("action_type", "scan"),
            "device_info": scan_data.get("device_info", {}),
            "success": scan_data.get("success", True)
        }
        
        # Store in database
        background_tasks.add_task(store_scan_event, scan_event, db)
        
        return JSONResponse(
            status_code=200,
            content={"message": "Scan recorded successfully"}
        )
    except Exception as e:
        logger.error(f"Error recording scan: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error recording scan: {str(e)}"}
        )

@app.get("/api/v1/analytics/stream")
async def stream_metrics(
    request: Request,
    db: Any = Depends(get_database)
) -> StreamingResponse:
    """SSE endpoint for real-time metrics"""
    return StreamingResponse(
        event_generator(request, db),
        media_type="text/event-stream",
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )

@app.get("/api/v1/analytics/metrics")
async def get_metrics(
    db: Any = Depends(get_database)
) -> Dict[str, Any]:
    """Get current analytics metrics"""
    return await get_real_time_metrics(db)

@app.post("/r/{vcard_id}")
async def track_scan(
    vcard_id: str,
    request: Request,
    db = Depends(get_database),
    redis = Depends(get_redis_client)
):
    """Track vCard scan from QR code"""
    try:
        # Get vCard by ID
        vcard = await db.vcards.find_one({"_id": PyObjectId(vcard_id)})
        if not vcard:
            logger.warning(f"No vCard found for ID: {vcard_id}")
            return Response(status_code=204)
        
        # Create scan event
        scan_event = ScanTrackingEvent(
            vcard_id=vcard_id,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host,
            headers=dict(request.headers),
            action_type="scan",  # Explicitly set action_type to "scan"
            device_info={
                "browser": request.headers.get("sec-ch-ua"),
                "os": request.headers.get("sec-ch-ua-platform"),
                "is_mobile": request.headers.get("sec-ch-ua-mobile") == "?1"
            }
        )
        
        # Store in Redis for real-time updates
        await redis.lpush(
            f"scans:{vcard_id}",
            scan_event.json()
        )
        await redis.expire(f"scans:{vcard_id}", 86400)  # Expire after 24 hours
        
        # Update MongoDB
        await db.vcards.update_one(
            {"_id": PyObjectId(vcard_id)},
            {
                "$inc": {"analytics.total_scans": 1},
                "$set": {"analytics.last_scan": datetime.utcnow()},
                "$push": {
                    "analytics.scans": {
                        "timestamp": scan_event.timestamp,
                        "user_agent": scan_event.user_agent,
                        "ip_address": scan_event.ip_address,
                        "device_info": scan_event.device_info
                    }
                }
            }
        )
        
        # Store scan event in analytics collection
        await db.scan_events.insert_one(scan_event.dict())
        
        logger.info(f"Tracked scan for vCard {vcard_id}")
        return Response(status_code=204)
        
    except Exception as e:
        logger.error(f"Error tracking scan: {str(e)}")
        return Response(status_code=204)  # Silent fail for tracking

@app.get("/health")
async def health_check() -> Dict[str, str]:
    return {"status": "healthy"}

@app.get("/api/v1/analytics/qr/{vcard_id}")
async def get_vcard_analytics(
    vcard_id: str,
    timeRange: str = "7d",
    db = Depends(get_database)
):
    """Get analytics for a specific VCard."""
    try:
        logger.info(f"Fetching analytics for vCard: {vcard_id}")
        
        # Parse time range
        time_delta = {
            "24h": timedelta(days=1),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30),
            "90d": timedelta(days=90)
        }.get(timeRange, timedelta(days=7))
        
        start_time = datetime.utcnow() - time_delta
        
        # Get scan events for this vCard
        # Use the vcard_id as is - MongoDB will match it whether it's a string or ObjectId
        pipeline = [
            {
                "$match": {
                    "vcard_id": vcard_id,
                    "timestamp": {"$gte": start_time},
                    "action_type": {"$ne": "page_view"}  # Exclude page_view events
                }
            },
            {
                "$group": {
                    "_id": {
                        "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
                        "action": "$action_type"
                    },
                    "count": {"$sum": 1}
                }
            },
            {
                "$sort": {"_id.date": 1}
            }
        ]
        
        scan_events = await db.scan_events.aggregate(pipeline).to_list(None)
        
        # Format response
        analytics_data = {
            "vcard_id": vcard_id,
            "timeRange": timeRange,
            "total_scans": sum(event["count"] for event in scan_events if event["_id"]["action"] == "scan"),  # Only count 'scan' events
            "scan_history": [
                {
                    "date": event["_id"]["date"],
                    "action": event["_id"]["action"],
                    "count": event["count"]
                }
                for event in scan_events
            ]
        }
        
        logger.info(f"Successfully retrieved analytics for vCard {vcard_id}")
        return analytics_data
        
    except Exception as e:
        logger.error(f"Error fetching vCard analytics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching analytics: {str(e)}"
        )

# Add new endpoint with vcard in the URL instead of qr
@app.get("/api/v1/analytics/vcard/{vcard_id}")
async def get_vcard_analytics_new_endpoint(
    vcard_id: str,
    timeRange: str = "7d",
    db = Depends(get_database)
):
    """Get analytics for a specific VCard using the new URL pattern."""
    # Reuse the same implementation
    return await get_vcard_analytics(vcard_id, timeRange, db)

async def get_vcard_real_time_metrics(db: Any, vcard_id: str) -> Dict[str, Any]:
    """Get current analytics metrics for a specific VCard"""
    try:
        # Get metrics for the last 24 hours
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=24)
        
        pipeline = [
            {
                "$match": {
                    "vcard_id": vcard_id,  # Use vcard_id as is
                    "timestamp": {"$gte": start_time, "$lte": end_time},
                    "action_type": {"$in": ["scan", "vcf_download", "contact_add"]}  # Include all relevant actions
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_scans": {"$sum": 1},  # Count all interactions as scans
                    "contact_adds": {
                        "$sum": {"$cond": [{"$eq": ["$action_type", "contact_add"]}, 1, 0]}
                    },
                    "vcf_downloads": {
                        "$sum": {"$cond": [{"$eq": ["$action_type", "vcf_download"]}, 1, 0]}
                    }
                }
            }
        ]
        
        result = await db.scan_events.aggregate(pipeline).to_list(1)
        metrics = result[0] if result else {
            "total_scans": 0,
            "contact_adds": 0,
            "vcf_downloads": 0
        }
        
        # Get recent scans for this vCard (including page_view for visibility)
        recent_scans = await db.scan_events.find(
            {"vcard_id": vcard_id},  # Use vcard_id as is
            sort=[("timestamp", -1)],
            limit=5
        ).to_list(5)
        
        metrics["recent_scans"] = [
            {
                "timestamp": scan["timestamp"].isoformat(),
                "action_type": scan["action_type"],
                "device_info": scan["device_info"]
            }
            for scan in recent_scans
        ]
        
        # Remove MongoDB _id
        if "_id" in metrics:
            del metrics["_id"]
            
        return metrics
        
    except Exception as e:
        logger.error(f"Error getting VCard real-time metrics: {e}")
        return {
            "total_scans": 0,
            "contact_adds": 0,
            "vcf_downloads": 0,
            "recent_scans": []
        }

@app.get("/api/v1/analytics/qr/{vcard_id}/stream")
async def stream_vcard_metrics(
    vcard_id: str,
    request: Request,
    db: Any = Depends(get_database)
) -> StreamingResponse:
    """SSE endpoint for real-time metrics of a specific VCard"""
    try:
        async def event_generator():
            client_id = str(uuid.uuid4())
            logger.info(f"Starting event stream for client {client_id}, VCard {vcard_id}")
            try:
                while True:
                    try:
                        # Get current metrics for this VCard
                        metrics = await get_vcard_real_time_metrics(db, vcard_id)
                        
                        # Format as SSE event
                        event_data = json.dumps(metrics)
                        yield f"data: {event_data}\n\n"
                        
                        # Wait before sending next update
                        await asyncio.sleep(2)  # Send updates every 2 seconds
                        
                    except Exception as e:
                        logger.error(f"Error in VCard metrics generator for client {client_id}: {e}")
                        # Don't break the loop on error, just log and continue
                        continue
            finally:
                logger.info(f"Client {client_id} disconnected from VCard {vcard_id} stream")

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Content-Type': 'text/event-stream',
                'X-Accel-Buffering': 'no',
            }
        )
    except Exception as e:
        logger.error(f"Error setting up VCard metrics stream: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Add new endpoint with vcard in the URL instead of qr
@app.get("/api/v1/analytics/vcard/{vcard_id}/stream")
async def stream_vcard_metrics_new_endpoint(
    vcard_id: str,
    request: Request,
    db: Any = Depends(get_database)
) -> StreamingResponse:
    """SSE endpoint for real-time metrics of a specific VCard using the new URL pattern"""
    # Reuse the same implementation
    return await stream_vcard_metrics(vcard_id, request, db)

async def store_scan_event(scan_event: Dict[str, Any], db: Any):
    """Store a scan event and update related metrics"""
    try:
        # Insert into scan_events collection
        await db.scan_events.insert_one(scan_event)
        
        vcard_id = scan_event["vcard_id"]
        action_type = scan_event["action_type"]
        timestamp = scan_event["timestamp"]
        
        # Only update analytics for scan events
        if action_type == "scan":
            # Update VCard analytics
            date_str = timestamp.strftime("%Y-%m-%d")
            device_type = "mobile" if scan_event.get("device_info", {}).get("is_mobile", False) else "desktop"
            
            logger.info(f"Updating analytics for VCard: {vcard_id}, date: {date_str}, device: {device_type}")
            
            # First, check if the VCard exists and has analytics
            vcard = None
            try:
                # Try as ObjectId first
                vcard = await db.vcards.find_one({"_id": PyObjectId(vcard_id)})
            except:
                # If that fails, try as string
                vcard = await db.vcards.find_one({"_id": vcard_id})
            
            if not vcard:
                logger.error(f"VCard not found: {vcard_id}")
                return
            
            # Check if analytics object exists
            has_analytics = "analytics" in vcard and vcard["analytics"] is not None
            logger.info(f"VCard has analytics: {has_analytics}")
            
            # Initialize analytics object if it doesn't exist and update metrics
            update_data = {
                "$inc": {
                    "analytics.total_scans": 1,
                    f"analytics.scans_by_date.{date_str}": 1,
                    f"analytics.scans_by_device.{device_type}": 1
                },
                "$set": {
                    "analytics.last_scan": timestamp
                },
                "$push": {
                    "analytics.scans": {
                        "timestamp": timestamp,
                        "device_info": scan_event.get("device_info", {}),
                        "ip_address": scan_event.get("ip_address", "")
                    }
                }
            }
            
            # If analytics doesn't exist, initialize it
            if not has_analytics:
                logger.info(f"Initializing analytics for VCard: {vcard_id}")
                update_data["$setOnInsert"] = {
                    "analytics": {
                        "total_scans": 0,
                        "scans": [],
                        "scans_by_date": {},
                        "scans_by_device": {}
                    }
                }
            
            # Determine the correct ID format for the update
            vcard_id_for_update = PyObjectId(vcard_id) if isinstance(vcard.get("_id"), PyObjectId) else vcard_id
            logger.info(f"VCard ID for update: {vcard_id_for_update}, Type: {type(vcard_id_for_update)}")
            
            # Try to update VCard document with either ObjectId or string
            try:
                # Try as ObjectId first
                result = await db.vcards.update_one(
                    {"_id": vcard_id_for_update},
                    update_data,
                    upsert=False
                )
                
                logger.info(f"VCard update result: matched={result.matched_count}, modified={result.modified_count}")
                
                if result.matched_count == 0:
                    logger.warning(f"VCard not found during update: {vcard_id}")
                elif result.modified_count == 0:
                    logger.warning(f"VCard found but not modified: {vcard_id}")
                else:
                    logger.info(f"VCard analytics updated successfully: {vcard_id}")
            except Exception as e:
                logger.error(f"Error updating VCard analytics: {e}")
        
        # Update real-time metrics and broadcast
        metrics = await get_real_time_metrics(db)
        await sse_manager.broadcast(metrics)
        
        # Update VCard-specific metrics
        vcard_metrics = await get_vcard_real_time_metrics(db, vcard_id)
        await sse_manager.broadcast(vcard_metrics)
        
    except Exception as e:
        logger.error(f"Error storing scan event: {e}")
        logger.error(traceback.format_exc())