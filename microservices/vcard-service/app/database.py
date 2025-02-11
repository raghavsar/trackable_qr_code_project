from fastapi import Request
from motor.motor_asyncio import AsyncIOMotorDatabase

async def get_database(request: Request) -> AsyncIOMotorDatabase:
    return request.app.mongodb 