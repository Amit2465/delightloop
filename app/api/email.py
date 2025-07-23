from fastapi import APIRouter, Form
from app.services.mail_service import send_email_async

router = APIRouter(prefix="/v1/email", tags=["Email"])

@router.post("/send")
async def send_email_endpoint(
    to_email: str = Form(...),
    subject: str = Form(...),
    content: str = Form(...),
):
    result = await send_email_async(to_email, subject, content)
    return result
