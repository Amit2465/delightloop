from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agent.summarize import summarize_interest

router = APIRouter(tags=["Summarization"])


class SummaryRequest(BaseModel):
    transcript: str


@router.post("/v1/summarize")
async def summarize_endpoint(payload: SummaryRequest):
    if not payload.transcript.strip():
        raise HTTPException(status_code=400, detail="Transcript cannot be empty")

    summary = await summarize_interest(payload.transcript)
    return {"summary": summary}
