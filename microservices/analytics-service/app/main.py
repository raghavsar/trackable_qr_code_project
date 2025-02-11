from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta
import json
import asyncio
from typing import Dict, List, Optional, Any, AsyncGenerator, Set, TYPE_CHECKING
import logging
import os

from shared.models import PyObjectId
from .database import get_database

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

# Configure logging
logger = logging.getLogger(__name__)

app = FastAPI(title="Analytics Service")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    now = datetime.utcnow()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Get today's metrics
    pipeline = [
        {
            "$match": {
                "timestamp": {"$gte": today}
            }
        },
        {
            "$group": {
                "_id": None,
                "total_scans": {"$sum": 1},
                "contact_adds": {
                    "$sum": {"$cond": [{"$eq": ["$action_type", "contact_add"]}, 1, 0]}
                },
                "vcf_downloads": {
                    "$sum": {"$cond": [{"$eq": ["$action_type", "vcf_download"]}, 1, 0]}
                },
                "mobile_scans": {
                    "$sum": {"$cond": [{"$eq": ["$device_info.is_mobile", True]}, 1, 0]}
                },
                "desktop_scans": {
                    "$sum": {"$cond": [{"$eq": ["$device_info.is_mobile", False]}, 1, 0]}
                },
                "recent_scans": {
                    "$push": {
                        "vcard_id": "$vcard_id",
                        "timestamp": "$timestamp",
                        "device_info": "$device_info",
                        "action_type": "$action_type"
                    }
                }
            }
        }
    ]
    
    result = await db.scan_events.aggregate(pipeline).to_list(1)
    metrics = result[0] if result else {
        "total_scans": 0,
        "contact_adds": 0,
        "vcf_downloads": 0,
        "mobile_scans": 0,
        "desktop_scans": 0,
        "recent_scans": []
    }
    
    # Sort and limit recent scans
    metrics["recent_scans"] = sorted(
        metrics["recent_scans"],
        key=lambda x: x["timestamp"],
        reverse=True
    )[:10]
    
    return metrics

async def event_generator(request: Request, db: Any) -> AsyncGenerator[str, None]:
    """Generate SSE events"""
    client_queue = await sse_manager.register(request)
    try:
        while True:
            if await request.is_disconnected():
                break

            # Wait for new data
            metrics = await client_queue.get()
            
            # Format as SSE
            yield f"data: {json.dumps(metrics)}\n\n"
            
            # Optional: Add heartbeat
            await asyncio.sleep(1)
    finally:
        sse_manager.remove(client_queue)

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

@app.get("/health")
async def health_check() -> Dict[str, str]:
    return {"status": "healthy"}