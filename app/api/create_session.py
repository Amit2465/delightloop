from uuid import uuid4

from fastapi import APIRouter

from app.schemas.session import SessionResponse
from app.db.models.lead import Lead
from uuid import UUID
from fastapi import HTTPException
from typing import List

router = APIRouter(prefix="/v1", tags=["Sessions"])


@router.post("/sessions/", response_model=SessionResponse, status_code=201)
async def generate_session_id():
    session_id = str(uuid4())
    return SessionResponse(session_id=session_id)


@router.get("/leads", response_model=List[dict])
async def get_leads_by_session(session_id: str):
    """Get all leads for a given session_id (as a query parameter)."""
    try:
        session_uuid = UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="session_id must be a valid UUID")
    leads = await Lead.find({"session_id": session_uuid}).to_list()
    return [lead.dict() for lead in leads]