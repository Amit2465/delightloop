from beanie import Document
from pydantic import Field, ConfigDict
from uuid import UUID, uuid4
from datetime import datetime, timezone

def utc_now():
    return datetime.now(timezone.utc)

class PersonalizedEmail(Document):
    id: UUID = Field(default_factory=uuid4, alias="_id")
    session_id: UUID = Field(..., index=True)
    subject: str = Field(default="This is your personalized mail")
    body: str = Field(...)
    email: str = Field(default="amityadav23461@email.com")
    created_at: datetime = Field(default_factory=utc_now)

    model_config = ConfigDict(populate_by_name=True)

    class Settings:
        collection = "personalized_email"
