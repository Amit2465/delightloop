from fastapi import APIRouter, Form
from app.services.mail_service import send_email_async
from app.db.models.email import PersonalizedEmail
from uuid import UUID
from fastapi import HTTPException
from typing import List, Optional

router = APIRouter(prefix="/v1/email", tags=["Email"])

@router.post("/send")
async def send_email_endpoint(
    to_email: str = Form(...),
    subject: str = Form(...),
    content: str = Form(...),
):
    result = await send_email_async(to_email, subject, content)
    return result



@router.get("/", response_model=Optional[dict])
async def get_email_by_session(session_id: str):
    """Get the personalized email for a given session_id (as a query parameter)."""
    try:
        session_uuid = UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="session_id must be a valid UUID")
    email = await PersonalizedEmail.find_one({"session_id": session_uuid})
    if email:
        return email.dict()
    return None
