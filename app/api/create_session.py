from uuid import uuid4

from fastapi import APIRouter

from app.schemas.session import SessionResponse

router = APIRouter(prefix="/v1", tags=["Sessions"])


@router.post("/sessions/", response_model=SessionResponse, status_code=201)
async def generate_session_id():
    session_id = str(uuid4())
    return SessionResponse(session_id=session_id)