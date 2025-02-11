from datetime import datetime, timedelta
import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from redis import asyncio as aioredis
from typing import Dict, Any
import os

logger = logging.getLogger(__name__)

class AnalyticsCron:
    def __init__(self, mongodb_url: str, redis_url: str):
        self.mongodb = AsyncIOMotorClient(mongodb_url)
        self.redis = aioredis.from_url(redis_url)
        self.db = self.mongodb.get_database()
        self.KEY_PREFIX = "analytics:"

    async def aggregate_daily_metrics(self) -> None:
        """Aggregate daily metrics and store in MongoDB"""
        try:
            # Get yesterday's date
            yesterday = (datetime.utcnow() - timedelta(days=1)).date()
            yesterday_str = yesterday.isoformat()
            
            # Get metrics from Redis
            redis_key = f"{self.KEY_PREFIX}{yesterday_str}"
            metrics = await self.redis.hgetall(redis_key)
            
            if not metrics:
                logger.warning(f"No metrics found for {yesterday_str}")
                return
            
            # Convert Redis data
            metrics_dict = {
                k.decode(): int(v.decode()) 
                for k, v in metrics.items()
            }
            
            # Store in MongoDB
            await self.db.daily_metrics.insert_one({
                "date": yesterday,
                "metrics": metrics_dict,
                "created_at": datetime.utcnow()
            })
            
            logger.info(f"Successfully aggregated metrics for {yesterday_str}")
            
            # Optionally clean up Redis data
            await self.redis.delete(redis_key)
            
        except Exception as e:
            logger.error(f"Error aggregating daily metrics: {e}")
            raise

    async def get_aggregated_metrics(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get aggregated metrics for a date range"""
        try:
            pipeline = [
                {
                    "$match": {
                        "date": {
                            "$gte": start_date,
                            "$lte": end_date
                        }
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "total_scans": {"$sum": "$metrics.total_scans"},
                        "contact_adds": {"$sum": "$metrics.contact_adds"},
                        "vcf_downloads": {"$sum": "$metrics.vcf_downloads"},
                        "mobile_scans": {"$sum": "$metrics.mobile_scans"},
                        "desktop_scans": {"$sum": "$metrics.desktop_scans"}
                    }
                }
            ]
            
            result = await self.db.daily_metrics.aggregate(pipeline).to_list(1)
            return result[0] if result else {}
            
        except Exception as e:
            logger.error(f"Error getting aggregated metrics: {e}")
            raise

    async def run_daily_job(self) -> None:
        """Run the daily aggregation job"""
        try:
            logger.info("Starting daily analytics aggregation")
            await self.aggregate_daily_metrics()
            logger.info("Completed daily analytics aggregation")
        except Exception as e:
            logger.error(f"Error in daily analytics job: {e}")

async def start_cron():
    """Start the cron job scheduler"""
    cron = AnalyticsCron(
        mongodb_url=os.getenv("MONGODB_URL"),
        redis_url=os.getenv("REDIS_URL")
    )
    
    while True:
        now = datetime.utcnow()
        # Run at 00:05 UTC every day
        next_run = (now + timedelta(days=1)).replace(
            hour=0, minute=5, second=0, microsecond=0
        )
        
        # Sleep until next run time
        sleep_seconds = (next_run - now).total_seconds()
        logger.info(f"Next analytics aggregation in {sleep_seconds/3600:.2f} hours")
        await asyncio.sleep(sleep_seconds)
        
        # Run the job
        await cron.run_daily_job() 