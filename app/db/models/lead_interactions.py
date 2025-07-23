from beanie import Document
from uuid import UUID, uuid4
from pydantic import EmailStr, Field
from typing import List, Optional

class MockLeadInteraction(Document):
    """
    Minimal mock interaction for past lead engagement.
    """
    id: UUID = Field(default_factory=uuid4, alias="_id")
    emails: List[EmailStr] = Field(default_factory=list)
    phones: List[str] = Field(default_factory=list)
    name: Optional[str] = None
    company: Optional[str] = None
    interaction_summary: Optional[str] = Field(
        default=None,
        description="Notes about what was discussed or asked in a past interaction"
    )

    class Settings:
        name = "mock_lead_interactions"
