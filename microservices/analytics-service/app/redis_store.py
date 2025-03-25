from redis import asyncio as aioredis
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import redis.asyncio as redis
import os
from fastapi import Depends
import logging

logger = logging.getLogger(__name__)

class DummyRedisClient:
    """A dummy Redis client that logs operations without performing them.
    
    This class is used as a fallback when Redis is not implemented or unavailable,
    to prevent application errors while still logging what would have happened.
    """
    async def ping(self):
        logger.debug("DummyRedisClient: PING (Redis not implemented)")
        return True
        
    async def hincrby(self, key, field, amount):
        logger.debug(f"DummyRedisClient: HINCRBY {key} {field} {amount} (Redis not implemented)")
        return amount
        
    async def expire(self, key, seconds):
        logger.debug(f"DummyRedisClient: EXPIRE {key} {seconds} (Redis not implemented)")
        return True
        
    async def hgetall(self, key):
        logger.debug(f"DummyRedisClient: HGETALL {key} (Redis not implemented)")
        return {}
        
    async def zadd(self, key, mapping):
        logger.debug(f"DummyRedisClient: ZADD {key} (Redis not implemented)")
        return 0
        
    async def zremrangebyrank(self, key, start, end):
        logger.debug(f"DummyRedisClient: ZREMRANGEBYRANK {key} {start} {end} (Redis not implemented)")
        return 0
        
    async def zrevrange(self, key, start, end):
        logger.debug(f"DummyRedisClient: ZREVRANGE {key} {start} {end} (Redis not implemented)")
        return []
        
    async def delete(self, key):
        logger.debug(f"DummyRedisClient: DEL {key} (Redis not implemented)")
        return 0
        
    # Handle any other method by logging and returning a sensible default
    async def __getattr__(self, name):
        async def dummy_method(*args, **kwargs):
            args_str = ", ".join([str(arg) for arg in args])
            kwargs_str = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
            logger.debug(f"DummyRedisClient: {name} {args_str} {kwargs_str} (Redis not implemented)")
            return None
        return dummy_method

class RedisClient:
    _instance: Optional[redis.Redis] = None

    @classmethod
    async def get_instance(cls) -> redis.Redis:
        if cls._instance is None:
            # Since Redis is not implemented, we'll always use the DummyRedisClient
            logger.warning("Redis is not implemented. Using DummyRedisClient instead.")
            cls._instance = DummyRedisClient()
        return cls._instance

async def get_redis_client() -> redis.Redis:
    """FastAPI dependency for Redis client"""
    return await RedisClient.get_instance()

class RedisStore:
    def __init__(self, redis_url: str):
        try:
            # Try to connect to Redis, but use DummyRedisClient if it fails
            logger.info(f"Creating RedisStore with URL: {redis_url}")
            self.redis = aioredis.from_url(redis_url)
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}, using DummyRedisClient")
            self.redis = DummyRedisClient()
        
        self.KEY_PREFIX = "analytics:"
        self.EXPIRY = 60 * 60 * 24  # 24 hours
        self.using_dummy = isinstance(self.redis, DummyRedisClient)

    async def increment_counter(self, key: str, field: str, amount: int = 1) -> None:
        """Increment a counter in Redis hash"""
        full_key = f"{self.KEY_PREFIX}{key}"
        await self.redis.hincrby(full_key, field, amount)
        await self.redis.expire(full_key, self.EXPIRY)

    async def get_counters(self, key: str) -> Dict[str, int]:
        """Get all counters from a Redis hash"""
        full_key = f"{self.KEY_PREFIX}{key}"
        try:
            data = await self.redis.hgetall(full_key)
            
            # Handle different return types based on if we're using DummyRedisClient
            if self.using_dummy:
                # DummyRedisClient returns empty dict
                return {}
            else:
                # Real Redis client returns bytes
                return {k.decode(): int(v.decode()) for k, v in data.items()}
        except Exception as e:
            logger.error(f"Error getting counters: {e}")
            return {}

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
        try:
            scans = await self.redis.zrevrange(key, 0, -1)
            
            # Handle different return types based on if we're using DummyRedisClient
            if self.using_dummy:
                # DummyRedisClient returns empty list
                return []
            else:
                # Real Redis client returns bytes
                return [json.loads(scan.decode()) for scan in scans]
        except Exception as e:
            logger.error(f"Error getting recent scans: {e}")
            return []

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