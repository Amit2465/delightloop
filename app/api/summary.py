from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agent.summarize import summarize_interest
from app.db.models.session import Session
from uuid import UUID
from fastapi import HTTPException
from typing import Optional

router = APIRouter(tags=["Summarization"])


class SummaryRequest(BaseModel):
    transcript: str


@router.post("/v1/summarize")
async def summarize_endpoint(payload: SummaryRequest):
    if not payload.transcript.strip():
        raise HTTPException(status_code=400, detail="Transcript cannot be empty")

    summary = await summarize_interest(payload.transcript)
    return {"summary": summary}


@router.get("/v1/summary", response_model=Optional[dict])
async def get_session_summary(session_id: str):
    """Get session summary and details by session_id (as a query parameter)."""
    try:
        session_uuid = UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="session_id must be a valid UUID")
    session_doc = await Session.find_one({"session_id": session_uuid})
    if session_doc:
        return session_doc.dict()
    return None
