from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel, EmailStr, Field

from app.db.models.lead_interactions import MockLeadInteraction

router = APIRouter(prefix="/v1/dev", tags=["Mock Seed (Dev Only)"])


# Pydantic schema for incoming request
class MockInteractionCreate(BaseModel):
    emails: List[EmailStr] = Field(default_factory=list)
    phones: List[str] = Field(default_factory=list)
    name: Optional[str] = None
    company: Optional[str] = None
    interaction_summary: Optional[str] = None


@router.post("/mock-interactions", status_code=201)
async def create_mock_interaction(mock: MockInteractionCreate):
    """
    Create a mock lead interaction from request body.
    """
    doc = MockLeadInteraction(
        id=uuid4(),
        emails=mock.emails,
        phones=mock.phones,
        name=mock.name,
        company=mock.company,
        interaction_summary=mock.interaction_summary,
    )
    await doc.insert()
    return {"message": "Mock interaction saved"}
