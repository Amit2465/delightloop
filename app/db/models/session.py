from beanie import Document
from pydantic import Field
from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import Optional
from pydantic import ConfigDict

def utc_now():
    return datetime.now(timezone.utc)

class Session(Document):
    """
    Represents a scanning session (can have multiple leads).
    """
    id: UUID = Field(default_factory=uuid4, alias="_id")
    session_id: UUID = Field(default_factory=uuid4, unique=True, index=True)
    summary: Optional[str] = Field(None, description="Summary of the session")
    audio_file_url: Optional[str] = Field(None, description="URL to the audio file")
    transcription_url: Optional[str] = Field(None, description="URL to the transcription file")
    created_at: datetime = Field(default_factory=utc_now)

    model_config = ConfigDict(populate_by_name=True)

    class Settings:
        collection = "session"
