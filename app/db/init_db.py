from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings
from app.db.models.lead import Lead
from app.db.models.session import Session


async def init_db():
    client = AsyncIOMotorClient(settings.mongo_url)
    db = client.get_default_database()
    await init_beanie(database=db, document_models=[Lead, Session])
