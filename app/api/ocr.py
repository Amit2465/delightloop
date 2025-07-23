import logging
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import ValidationError

from app.agent.gemini_ocr import extract_card_data
from app.agent.tagging_agent import classify_lead_with_ai
from app.db.models.lead import Lead
from app.db.models.session import Session
from app.schemas.ocr import OcrResult, ParsedFields
from app.services.match_data import find_mock_interactions

router = APIRouter(tags=["Card OCR"], prefix="/v1/card")
logger = logging.getLogger("ocr_logger")


def flatten_field(value):
    """
    Normalize OCR output field into a flat list of strings.

    Args:
        value: A string, list of strings, or dict of strings.

    Returns:
        List[str]: A flat list of cleaned strings.
    """
    if isinstance(value, str):
        return [value]
    elif isinstance(value, dict):
        return [v for v in value.values() if isinstance(v, str)]
    elif isinstance(value, list):
        return [v for v in value if isinstance(v, str)]
    return []


@router.post("/ocr", response_model=OcrResult, status_code=201)
async def upload_card_image(file: UploadFile = File(...), session_id: str = Form(...)):
    """
    OCR endpoint for business card image upload. It extracts contact details, enriches them,
    classifies the lead using AI, and stores the result in the database.

    Args:
        file (UploadFile): Image file of a business card.
        session_id (str): Unique identifier for the OCR session.

    Returns:
        OcrResult: Object containing parsed contact data and AI-generated tag.

    Raises:
        HTTPException: If file type is invalid or processing fails.
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image.")

    image_bytes = await file.read()

    try:
        extracted = extract_card_data(image_bytes, file.content_type)
        logger.info("Raw OCR Output: %s", extracted)

        if "message" in extracted:
            raise HTTPException(status_code=422, detail=extracted["message"])

        field_aliases = {
            "name": "full_name",
            "fullname": "full_name",
            "full name": "full_name",
            "title": "job_title",
            "job": "job_title",
            "designation": "job_title",
            "company": "company",
            "organization": "company",
            "website": "website",
            "site": "website",
            "address": "address",
            "location": "address",
        }

        raw_emails: List[str] = []
        raw_phones: List[str] = []
        parsed_fields_data: dict = {}
        custom_fields: dict = {}

        # Process all extracted fields
        for key, value in extracted.items():
            key_lower = key.lower()

            if "email" in key_lower:
                for email in flatten_field(value):
                    email_clean = email.strip()
                    if email_clean:
                        raw_emails.extend(
                            email_clean.split(",")
                        )  # support comma-separated

            elif "phone" in key_lower:
                for phone in flatten_field(value):
                    for number in phone.split(","):  # support comma-separated
                        number_clean = number.strip()
                        if number_clean:
                            raw_phones.append(number_clean)

            elif key_lower in [
                "full_name",
                "company",
                "job_title",
                "address",
                "website",
            ]:
                parsed_fields_data[key_lower] = value

            elif key_lower in field_aliases:
                mapped_key = field_aliases[key_lower]
                parsed_fields_data[mapped_key] = value

            else:
                custom_fields[key_lower] = value

        # Normalize and deduplicate
        emails = sorted({e.strip() for e in raw_emails if "@" in e})
        phones = sorted({p.strip() for p in raw_phones if p.strip()})

        parsed_fields_data["custom_fields"] = custom_fields

        logger.info("Parsed Emails: %s", emails)
        logger.info("Parsed Phones: %s", phones)
        logger.info("Parsed Fields: %s", parsed_fields_data)

        full_name = parsed_fields_data.get("full_name")
        company = parsed_fields_data.get("company")
        job_title = parsed_fields_data.get("job_title")

        # Get or create session
        session = await Session.find_one(Session.session_id == session_id)
        if not session:
            session = Session(session_id=session_id)
            await session.insert()

        # Find matching historical interactions
        interactions = await find_mock_interactions(emails, phones, full_name, company)

        # Count leads that match based on contact identity
        session_match_count = await Lead.find(
            {
                "$or": [
                    {"emails": {"$in": emails}},
                    {"phones": {"$in": phones}},
                    {"parsed_fields.full_name": full_name},
                    {"parsed_fields.company": company},
                ]
            }
        ).count()

        # Prepare data for Gemini classification
        lead_ai_data = {
            "emails": emails,
            "phones": phones,
            "full_name": full_name,
            "title": job_title,
            "company": company,
            "website": parsed_fields_data.get("website"),
        }

        logger.info("Sending to AI classifier: %s", lead_ai_data)

        # Classify lead using Gemini
        tag_result = await classify_lead_with_ai(
            lead_ai_data, interactions, session_match_count
        )
        lead_tag = tag_result.get("tag", "cold")

        # Validate and store the lead
        parsed_fields_model = ParsedFields(**parsed_fields_data)

        lead = Lead(
            session_id=session.id,
            emails=emails,
            phones=phones,
            parsed_fields=parsed_fields_model.model_dump(),
            tag=lead_tag,
            created_at=datetime.now(timezone.utc),
        )
        await lead.insert()

        return OcrResult(
            lead_id=str(lead.id),
            status="lead saved",
            emails=emails,
            phones=phones,
            parsed_fields=parsed_fields_model,
            tag=lead_tag,
        )

    except ValidationError as ve:
        logger.error("ValidationError: %s", ve)
        raise HTTPException(status_code=422, detail=str(ve))

    except Exception as e:
        logger.exception("Unexpected error during OCR processing")
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {str(e)}")
