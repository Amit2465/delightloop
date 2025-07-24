import base64
import json
import re
import logging

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings

logger = logging.getLogger(__name__)

# === Allowed fields that map to DB fields or parsed_fields ===
CORE_FIELDS = {"name", "email", "phone", "company", "job_title", "website", "address"}

# Normalize aliases used by LLM
FIELD_ALIASES = {
    "full name": "name",
    "fullname": "name",
    "emails": "email",
    "email address": "email",
    "mob": "phone",
    "mobile": "phone",
    "organization": "company",
    "org": "company",
    "site": "website",
    "location": "address",
    "title": "job_title",
    "designation": "job_title",
}

def normalize_key(key: str) -> str:
    key = key.strip().lower()
    return FIELD_ALIASES.get(key, key)

# === OCR Extractor Function ===

def extract_card_data(image_bytes: bytes, mime_type: str) -> dict:
    base64_image = base64.b64encode(image_bytes).decode("utf-8")

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=settings.gemini_api_key,
    )

    prompt = (
        "You are an expert at extracting structured data from business cards. "
        "Return only a JSON object with the following fields:\n"
        "- name\n- company\n- job_title\n- address\n- website\n- email\n- phone\n"
        "Any extra unknown information should go under 'custom_fields' as key-value pairs.\n\n"
        "If a field is missing, use an empty string. Always return this format:\n"
        "{\n"
        '  "name": "",\n'
        '  "company": "",\n'
        '  "job_title": "",\n'
        '  "address": "",\n'
        '  "website": "",\n'
        '  "email": "",\n'
        '  "phone": "",\n'
        '  "custom_fields": {"...": "..."}\n'
        "}\n\n"
        "If the image contains no text or no card, respond with:\n"
        '{"message": "No card or text detected"}\n\n'
        "Return only valid JSON. No markdown. No explanation."
    )

    response = llm.invoke([
        HumanMessage(content=[
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}}
        ])
    ])

    raw_output = response.content.strip()
    cleaned = re.sub(r"^```json|^```|```$", "", raw_output, flags=re.MULTILINE).strip()

    # Try to isolate the first valid JSON object
    match = re.search(r'\{[\s\S]*\}', cleaned)
    if match:
        cleaned = match.group(0)

    try:
        parsed = json.loads(cleaned)
    except Exception as e:
        logger.warning("OCR response not valid JSON: %s", e)
        return {"message": "Invalid JSON from OCR agent", "raw_result": cleaned}

    # Ensure base structure
    output = {field: "" for field in CORE_FIELDS}
    output["custom_fields"] = {}

    for raw_key, value in parsed.items():
        if not value:
            continue
        key = normalize_key(raw_key)

        if key in CORE_FIELDS:
            output[key] = value
        elif key == "custom_fields" and isinstance(value, dict):
            output["custom_fields"].update(value)
        else:
            output["custom_fields"][raw_key] = value

    # Guarantee custom_fields is a dict
    if not isinstance(output["custom_fields"], dict):
        output["custom_fields"] = {}

    return output
