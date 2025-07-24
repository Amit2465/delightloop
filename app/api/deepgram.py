from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from uuid import UUID
import httpx
from app.core.config import settings
from app.agent.summarize import summarize_interest
from app.agent.personalized_email import generate_email_body
from app.api.upload_s3 import upload_audio_to_s3
from app.db.models.session import Session
from app.db.models.lead import Lead
from app.db.models.email import PersonalizedEmail
from datetime import datetime, timezone


router = APIRouter(prefix="/v1/deepgram", tags=["Deepgram"])

def utc_now():
    return datetime.now(timezone.utc)

@router.post("/", response_model=dict)
async def transcribe_and_summarize(
    session_id: str = Form(...),
    audio: UploadFile = File(...)
):
    try:
        session_uuid = UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="session_id must be a valid UUID")

    if not audio.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="File must be an audio file.")

    audio_bytes = await audio.read()

    # Upload to S3
    audio_url = await upload_audio_to_s3(session_id, audio_bytes, audio.content_type)

    # Deepgram transcription
    deepgram_url = settings.deepgram_url
    headers = {
        "Authorization": f"Token {settings.deepgram_api_key}",
        "Content-Type": audio.content_type,
    }
    params = {"punctuate": "true", "language": "en"}
    async with httpx.AsyncClient() as client:
        response = await client.post(
            deepgram_url,
            headers=headers,
            params=params,
            content=audio_bytes,
            timeout=120.0
        )

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail=f"Deepgram API error: {response.text}")

    dg_result = response.json()
    transcript = dg_result.get("results", {}).get("channels", [{}])[0].get("alternatives", [{}])[0].get("transcript", "")
    if not transcript:
        raise HTTPException(status_code=422, detail={"message": "No transcript returned from Deepgram.", "deepgram_response": dg_result})

    # Summarize
    summary = await summarize_interest(transcript)

    # Update or create session doc
    session_doc = await Session.find_one({"session_id": session_uuid})
    if session_doc:
        session_doc.audio_file_url = audio_url
        session_doc.transcription = transcript
        session_doc.summary = summary
        await session_doc.save()
    else:
        session_doc = Session(
            session_id=session_uuid,
            audio_file_url=audio_url,
            transcription=transcript,
            summary=summary
        )
        await session_doc.insert()

    # === QUERY lead info to enrich AI prompt ===
    lead_doc = await Lead.find_one({"session_id": session_uuid})
    if not lead_doc or not lead_doc.name:
        raise HTTPException(status_code=404, detail="Lead with name not found for session_id")

    # Build extra info dictionary from available fields
    extra_info = {
        "company": getattr(lead_doc.parsed_fields, "company", None) if lead_doc.parsed_fields else None,
        "job_title": getattr(lead_doc.parsed_fields, "job_title", None) if lead_doc.parsed_fields else None,
    }

    # Call AI agent
    email_result = await generate_email_body(
        name=lead_doc.name,
        transcript=transcript,
        extra_info=extra_info
    )

    # Save personalized email to DB
    email_doc = PersonalizedEmail(
        session_id=session_uuid,
        subject="This is your personalized email",
        body=email_result["text"],
        created_at=utc_now()
    )
    await email_doc.insert()

    return {
        "session_id": session_id,
        "audio_file_url": audio_url,
        "transcript": transcript,
        "summary": summary,
        "email_subject": email_doc.subject,
        "email_body": email_doc.body
    }
