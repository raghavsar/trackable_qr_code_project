from redis import asyncio as aioredis
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import redis.asyncio as redis
import os
from fastapi import Depends
import logging

logger = logging.getLogger(__name__)

class RedisClient:
    _instance: Optional[redis.Redis] = None

    @classmethod
    async def get_instance(cls) -> redis.Redis:
        if cls._instance is None:
            redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
            logger.info(f"Connecting to Redis at {redis_url}")
            cls._instance = redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True
            )
        return cls._instance

async def get_redis_client() -> redis.Redis:
    """FastAPI dependency for Redis client"""
    return await RedisClient.get_instance()

class RedisStore:
    def __init__(self, redis_url: str):
        self.redis = aioredis.from_url(redis_url)
        self.KEY_PREFIX = "analytics:"
        self.EXPIRY = 60 * 60 * 24  # 24 hours

    async def increment_counter(self, key: str, field: str, amount: int = 1) -> None:
        """Increment a counter in Redis hash"""
        full_key = f"{self.KEY_PREFIX}{key}"
        await self.redis.hincrby(full_key, field, amount)
        await self.redis.expire(full_key, self.EXPIRY)

    async def get_counters(self, key: str) -> Dict[str, int]:
        """Get all counters from a Redis hash"""
        full_key = f"{self.KEY_PREFIX}{key}"
        data = await self.redis.hgetall(full_key)
        return {k.decode(): int(v.decode()) for k, v in data.items()}

    async def add_recent_scan(self, scan_data: Dict[str, Any]) -> None:
        """Add a scan to the recent scans list"""
        key = f"{self.KEY_PREFIX}recent_scans"
        max_scans = 10

        # Create scan entry
        scan_entry = {
            "vcard_id": scan_data["vcard_id"],
            "timestamp": scan_data["timestamp"].isoformat(),
            "device_info": scan_data["device_info"],
            "action_type": scan_data["action_type"]
        }

        # Add to sorted set with timestamp as score
        timestamp = datetime.fromisoformat(scan_entry["timestamp"]).timestamp()
        await self.redis.zadd(key, {json.dumps(scan_entry): timestamp})
        
        # Trim to keep only latest N scans
        await self.redis.zremrangebyrank(key, 0, -(max_scans + 1))
        await self.redis.expire(key, self.EXPIRY)

    async def get_recent_scans(self) -> list:
        """Get recent scans from Redis"""
        key = f"{self.KEY_PREFIX}recent_scans"
        scans = await self.redis.zrevrange(key, 0, -1)
        return [json.loads(scan.decode()) for scan in scans]

    async def get_metrics(self) -> Dict[str, Any]:
        """Get all analytics metrics"""
        today = datetime.utcnow().date().isoformat()
        counters = await self.get_counters(today)
        recent_scans = await self.get_recent_scans()

        return {
            "total_scans": counters.get("total_scans", 0),
            "contact_adds": counters.get("contact_adds", 0),
            "vcf_downloads": counters.get("vcf_downloads", 0),
            "mobile_scans": counters.get("mobile_scans", 0),
            "desktop_scans": counters.get("desktop_scans", 0),
            "recent_scans": recent_scans
        }

    async def record_scan(self, scan_data: Dict[str, Any]) -> None:
        """Record a scan event in Redis"""
        today = datetime.utcnow().date().isoformat()
        
        # Increment appropriate counters based on action type
        if scan_data["action_type"] == "scan":
            # Only increment total_scans for actual scan events
            await self.increment_counter(today, "total_scans")
            
            # Increment device type counter only for scan events
            if scan_data["device_info"]["is_mobile"]:
                await self.increment_counter(today, "mobile_scans")
            else:
                await self.increment_counter(today, "desktop_scans")
        elif scan_data["action_type"] == "contact_add":
            await self.increment_counter(today, "contact_adds")
        elif scan_data["action_type"] == "vcf_download":
            await self.increment_counter(today, "vcf_downloads")
        
        # Add to recent scans list regardless of action type
        await self.add_recent_scan(scan_data) 