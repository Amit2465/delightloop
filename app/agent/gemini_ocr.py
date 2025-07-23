import base64
import json
import re

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings


def extract_card_data(image_bytes: bytes, mime_type: str) -> dict:
    base64_image = base64.b64encode(image_bytes).decode("utf-8")

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash", google_api_key=settings.gemini_api_key
    )

    response = llm.invoke(
        [
            HumanMessage(
                content=[
                    {
                        "type": "text",
                        "text": (
                            "You are an OCR and information extraction assistant for business and professional cards. "
                            "Extract all relevant information from the card and return it as a JSON object with key-value pairs. "
                            "Keys should be things like name, company, title, email, phone, address, website, etc. "
                            'If the image is not a card or no text is detected, return a JSON like {"message": "No card or text detected"}.'
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{base64_image}"},
                    },
                ]
            )
        ]
    )

    # Clean up JSON block
    raw = response.content.strip()
    cleaned = re.sub(r"^```json|^```|```$", "", raw, flags=re.MULTILINE).strip()

    try:
        parsed = json.loads(cleaned)
        return parsed
    except Exception:
        return {"raw_result": cleaned}
