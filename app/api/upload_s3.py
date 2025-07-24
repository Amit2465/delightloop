from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from app.core.config import settings
import aiobotocore.session
from uuid import UUID

router = APIRouter(tags=["Audio Upload"], prefix="/v1/audio")

AWS_S3_BUCKET = settings.bucket_name
S3_AUDIO_PREFIX = "audio/"

async def upload_audio_to_s3(session_id, file_bytes, content_type):
    session = aiobotocore.session.get_session()
    key = f"{S3_AUDIO_PREFIX}{session_id}"
    async with session.create_client(
        's3',
        region_name=settings.aws_origin,
        aws_secret_access_key=settings.aws_secret_access_key,
        aws_access_key_id=settings.aws_access_key,
    ) as s3_client:
        await s3_client.put_object(
            Bucket=AWS_S3_BUCKET,
            Key=key,
            Body=file_bytes,
            ContentType=content_type
        )
        url = f"https://{AWS_S3_BUCKET}.s3.{settings.aws_origin}.amazonaws.com/{key}"
        return url

@router.post("/upload", response_model=dict, status_code=201)
async def upload_audio(
    audio: UploadFile = File(...),
    session_id: str = Form(...)
):
    try:
        UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="session_id must be a valid UUID")
    if not audio.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="File must be an audio file.")
    audio_bytes = await audio.read()
    audio_url = await upload_audio_to_s3(session_id, audio_bytes, audio.content_type)
    return {"success": True, "audio_url": audio_url}
