from uuid import uuid4

from fastapi import APIRouter, Response

from app.schemas.session import SessionResponse

router = APIRouter(prefix="/v1", tags=["Sessions"])


@router.post("/sessions/", response_model=SessionResponse, status_code=201)
async def generate_session_id(response: Response):
    session_id = str(uuid4())
    response.set_cookie(
        key="session_id", value=session_id, httponly=True, samesite="lax"
    )
    return SessionResponse(session_id=session_id)


@router.delete("/sessions/", status_code=204)
async def delete_session(response: Response):
    response.delete_cookie("session_id")
