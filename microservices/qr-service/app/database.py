from fastapi import Request
from motor.motor_asyncio import AsyncIOMotorDatabase

def get_database(request: Request) -> AsyncIOMotorDatabase: #type: ignore
    return request.app.mongodb