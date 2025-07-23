from beanie import Document, Indexed
from pydantic import Field
from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import Optional

def utc_now():
    return datetime.now(timezone.utc)

class Session(Document):
    """
    Represents a scanning session (can have multiple leads).
    """
    id: UUID = Field(default_factory=uuid4, alias="_id")
    session_id: str = Indexed(unique=True)
    notes: Optional[str] = Field(None, description="Optional notes about the session")
    created_at: datetime = Field(default_factory=utc_now)

    model_config = {
        "populate_by_name": True
    }

    class Settings:
        name = "session"
