from beanie import Document
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import List, Optional

def utc_now():
    return datetime.now(timezone.utc)

class ParsedFields(BaseModel):
    """Flexible container for OCR-parsed data not in Lead's main schema."""
    model_config = ConfigDict(extra="allow")

class Lead(Document):
    id: UUID = Field(default_factory=uuid4, alias="_id")
    session_id: UUID = Field(..., index=True)
    name: Optional[str] = Field(None)
    image_url: str = Field(...)
    emails: List[EmailStr] = Field(default_factory=list)
    phones: List[str] = Field(default_factory=list)
    interest_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    interest_reason: Optional[str] = Field(default=None, description="Reason behind the interest score")
    existing_customer: bool = Field(default=False)
    parsed_fields: Optional[ParsedFields] = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)

    model_config = ConfigDict(populate_by_name=True)

    class Settings:
        collection = "lead"
