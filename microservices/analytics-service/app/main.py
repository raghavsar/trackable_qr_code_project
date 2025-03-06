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
                    "action_type": {"$ne": "page_view"}  # Exclude page_view events
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_scans": {"$sum": {"$cond": [{"$eq": ["$action_type", "scan"]}, 1, 0]}},  # Only count 'scan' events
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
    """Record a new scan event"""
    try:
        # Store scan event
        scan_event = {
            "vcard_id": scan_data["vcard_id"],
            "timestamp": datetime.fromisoformat(scan_data["timestamp"]),
            "device_info": scan_data["device_info"],
            "action_type": scan_data["action_type"],
            "success": scan_data.get("success", True),
            "ip_address": scan_data.get("ip_address"),
            "headers": scan_data.get("headers", {})
        }
        
        await db.scan_events.insert_one(scan_event)
        
        # Update real-time metrics and broadcast
        metrics = await get_real_time_metrics(db)
        background_tasks.add_task(sse_manager.broadcast, metrics)
        
        return JSONResponse({"status": "success"})
    except Exception as e:
        logger.error(f"Error recording scan: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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

@app.post("/t/{tracking_id}")
async def track_scan(
    tracking_id: str,
    request: Request,
    db = Depends(get_database),
    redis = Depends(get_redis_client)
):
    """Track vCard scan from QR code"""
    try:
        # Get vCard from tracking ID
        vcard = await db.vcards.find_one({"tracking_id": tracking_id})
        if not vcard:
            logger.warning(f"No vCard found for tracking ID: {tracking_id}")
            return Response(status_code=204)
        
        # Create scan event
        scan_event = ScanTrackingEvent(
            tracking_id=tracking_id,
            vcard_id=str(vcard["_id"]),
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
            f"scans:{tracking_id}",
            scan_event.json()
        )
        await redis.expire(f"scans:{tracking_id}", 86400)  # Expire after 24 hours
        
        # Update MongoDB
        await db.vcards.update_one(
            {"tracking_id": tracking_id},
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
        
        logger.info(f"Tracked scan for vCard {vcard['_id']} with tracking ID {tracking_id}")
        return Response(status_code=204)
        
    except Exception as e:
        logger.error(f"Error tracking scan: {str(e)}")
        return Response(status_code=204)  # Silent fail for tracking

@app.get("/health")
async def health_check() -> Dict[str, str]:
    return {"status": "healthy"}

@app.get("/api/v1/analytics/qr/{qr_id}")
async def get_qr_analytics(
    qr_id: str,
    timeRange: str = "7d",
    db = Depends(get_database)
):
    """Get analytics for a specific QR code."""
    try:
        logger.info(f"Fetching analytics for vCard: {qr_id}")
        
        # Parse time range
        time_delta = {
            "24h": timedelta(days=1),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30),
            "90d": timedelta(days=90)
        }.get(timeRange, timedelta(days=7))
        
        start_time = datetime.utcnow() - time_delta
        
        # Get scan events for this vCard
        pipeline = [
            {
                "$match": {
                    "vcard_id": qr_id,
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
            "qr_id": qr_id,
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
        
        logger.info(f"Successfully retrieved analytics for vCard {qr_id}")
        return analytics_data
        
    except Exception as e:
        logger.error(f"Error fetching vCard analytics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching analytics: {str(e)}"
        )

async def get_qr_real_time_metrics(db: Any, qr_id: str) -> Dict[str, Any]:
    """Get current analytics metrics for a specific QR code"""
    try:
        # Get metrics for the last 24 hours
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=24)
        
        pipeline = [
            {
                "$match": {
                    "vcard_id": qr_id,
                    "timestamp": {"$gte": start_time, "$lte": end_time},
                    "action_type": {"$ne": "page_view"}  # Exclude page_view events
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_scans": {"$sum": {"$cond": [{"$eq": ["$action_type", "scan"]}, 1, 0]}},  # Only count 'scan' events
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
            {"vcard_id": qr_id},
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
        logger.error(f"Error getting QR real-time metrics: {e}")
        return {
            "total_scans": 0,
            "contact_adds": 0,
            "vcf_downloads": 0,
            "recent_scans": []
        }

@app.get("/api/v1/analytics/qr/{qr_id}/stream")
async def stream_qr_metrics(
    qr_id: str,
    request: Request,
    db: Any = Depends(get_database)
) -> StreamingResponse:
    """SSE endpoint for real-time metrics of a specific QR code"""
    try:
        async def event_generator():
            client_id = str(uuid.uuid4())
            logger.info(f"Starting event stream for client {client_id}, QR {qr_id}")
            try:
                while True:
                    try:
                        # Get current metrics for this QR code
                        metrics = await get_qr_real_time_metrics(db, qr_id)
                        
                        # Format as SSE event
                        event_data = json.dumps(metrics)
                        yield f"data: {event_data}\n\n"
                        
                        # Wait before sending next update
                        await asyncio.sleep(2)  # Send updates every 2 seconds
                        
                    except Exception as e:
                        logger.error(f"Error in QR metrics generator for client {client_id}: {e}")
                        # Don't break the loop on error, just log and continue
                        continue
            finally:
                logger.info(f"Client {client_id} disconnected from QR {qr_id} stream")

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Content-Type': 'text/event-stream',
                'X-Accel-Buffering': 'no',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Credentials': 'true'
            }
        )
            
    except Exception as e:
        logger.error(f"Error streaming QR analytics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error streaming QR analytics: {str(e)}"
        )