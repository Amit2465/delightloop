from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import ValidationError
from datetime import datetime, timezone
from app.agent.gemini_ocr import extract_card_data
from app.agent.tagging_agent import score_lead_interest_with_ai
from app.db.models.lead import Lead, ParsedFields as LeadParsedFields
import logging
import aiobotocore.session
from app.core.config import settings
from uuid import UUID

router = APIRouter(tags=["Card OCR"], prefix="/v1/card")
logger = logging.getLogger("ocr_logger")

FIELD_ALIASES = {
    "full_name": "name",
    "name": "name",
    "emails": "email",
    "email address": "email",
    "mob": "phone",
    "mobile": "phone",
    "designation": "job_title",
    "org": "company",
    "organization": "company",
    "site": "website",
    "location": "address",
}

KNOWN_LEAD_FIELDS = {"emails", "phones", "name", "image_url", "interest_score", "existing_customer", "session_id", "created_at"}

PARSED_FIELDS = {"company", "job_title", "address", "website"}

AWS_S3_BUCKET = settings.bucket_name
S3_IMAGE_PREFIX = "images/"

async def upload_to_s3(filename, file_bytes, content_type):
    session = aiobotocore.session.get_session()
    key = f"{S3_IMAGE_PREFIX}{filename}"
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

def normalize_key(key: str) -> str:
    return FIELD_ALIASES.get(key.strip().lower(), key.strip().lower())

@router.post("/ocr", response_model=dict, status_code=201)
async def upload_card_image(file: UploadFile = File(...), session_id: str = Form(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image.")

    # Validate session_id first
    try:
        session_uuid = UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="session_id must be a valid UUID")

    image_bytes = await file.read()
    image_url = await upload_to_s3(file.filename, image_bytes, file.content_type)

    try:
        extracted = extract_card_data(image_bytes, file.content_type)
        logger.info("OCR Output: %s", extracted)

        if "message" in extracted:
            raise HTTPException(status_code=422, detail=extracted["message"])

        normalized = {}
        parsed_fields = {}

        for raw_key, value in extracted.items():
            if not value:
                continue
            key = normalize_key(raw_key)

            if key == "email":
                if isinstance(value, str):
                    normalized["emails"] = [e.strip().lower() for e in value.split(",") if "@" in e]
                elif isinstance(value, list):
                    normalized["emails"] = [e.strip().lower() for e in value if "@" in e]

            elif key == "phone":
                if isinstance(value, str):
                    normalized["phones"] = [p.strip() for p in value.split(",") if p.strip()]
                elif isinstance(value, list):
                    normalized["phones"] = [p.strip() for p in value if p.strip()]

            elif key == "name":
                normalized["name"] = value.strip()

            elif key in PARSED_FIELDS:
                parsed_fields[key] = value

            elif key == "custom_fields" and isinstance(value, dict):
                parsed_fields["custom_fields"] = value

        normalized.setdefault("emails", [])
        normalized.setdefault("phones", [])
        normalized.setdefault("name", "")

        existing = await Lead.find_one({
            "$or": [
                {"emails": {"$in": normalized["emails"]}},
                {"phones": {"$in": normalized["phones"]}}
            ]
        })
        existing_customer = bool(existing)

        # Build input for interest scoring
        lead_ai_data = {
            "full_name": normalized["name"],
            "emails": normalized["emails"],
            "phones": normalized["phones"],
            **parsed_fields.get("custom_fields", {}),
            **{k: v for k, v in parsed_fields.items() if k != "custom_fields"}
        }

        # AI score + reason
        score_result = await score_lead_interest_with_ai(lead_ai_data)
        interest_score = score_result.get("interest_score", 0.0)
        interest_reason = score_result.get("reason", "")

        lead = Lead(
            session_id=session_uuid,
            image_url=image_url,
            emails=normalized["emails"],
            phones=normalized["phones"],
            name=normalized["name"],
            interest_score=interest_score,
            interest_reason=interest_reason,
            existing_customer=existing_customer,
            parsed_fields=LeadParsedFields(**parsed_fields) if parsed_fields else None,
            created_at=datetime.now(timezone.utc)
        )
        await lead.insert()

        # Count the number of leads for this session
        count = await Lead.find({"session_id": session_uuid}).count()

        return {
            "lead_id": str(lead.id),
            "status": "lead saved",
            "emails": normalized["emails"],
            "phones": normalized["phones"],
            "name": normalized["name"],
            "interest_score": interest_score,
            "interest_reason": interest_reason,
            "existing_customer": existing_customer,
            "parsed_fields": parsed_fields,
            "count": count,
        }

    except ValidationError as ve:
        logger.error("ValidationError: %s", ve)
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        logger.exception("Unexpected error during OCR processing")
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {str(e)}")
