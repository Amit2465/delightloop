from beanie import Document, Indexed
from pydantic import BaseModel, Field, EmailStr
from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import List, Optional, Literal, Dict

def utc_now():
    return datetime.now(timezone.utc)

class ParsedFields(BaseModel):
    """
    Flexible container for OCR-parsed data from a card.
    """
    full_name: Optional[str] = None
    company: Optional[str] = None
    job_title: Optional[str] = None
    address: Optional[str] = None
    website: Optional[str] = None
    custom_fields: Dict[str, str] = Field(default_factory=dict, description="Free-form extra OCR data")

    model_config = {
        "extra": "allow"
    }

class Lead(Document):
    """
    Represents a single business card scan associated with a session.
    """
    id: UUID = Field(default_factory=uuid4, alias="_id")
    session_id: UUID = Indexed()
    parsed_fields: Optional[ParsedFields] = Field(default=None)
    emails: List[EmailStr] = Field(default_factory=list, description="OCR-detected emails (0..N)")
    phones: List[str] = Field(default_factory=list, description="OCR-detected phone numbers (0..N)")
    tag: Optional[Literal["hot", "warm", "cold"]] = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)

    model_config = {
        "populate_by_name": True
    }

    class Settings:
        name = "lead"
