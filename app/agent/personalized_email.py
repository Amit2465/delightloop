import logging
import re
from typing import Optional, Dict

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.config import settings

logger = logging.getLogger(__name__)

# === Utility: Convert plaintext to HTML ===
def text_to_html(text: str) -> str:
    """
    Converts plain text with `\n` into basic HTML with <br> tags.
    """
    lines = text.strip().splitlines()
    html_lines = [f"{line}<br>" for line in lines if line.strip()]
    return "<html><body>" + "\n".join(html_lines) + "</body></html>"


# === AI Agent: Generate personalized email ===
async def generate_email_body(
    name: str,
    transcript: str,
    extra_info: Optional[Dict[str, str]] = None
) -> dict:
    """
    Generate a personalized email using name, transcript, and optional extra info like job_title, company, etc.
    Returns both plain text and HTML versions of the email.
    Only return a generic fallback if ALL fields (name, transcript, extra_info) are empty or None.
    """
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=settings.gemini_api_key,
    )

    extra_info = extra_info or {}
    has_extra_info = any(v for v in extra_info.values())
    if not (name or transcript or has_extra_info):
        fallback = "Hi there,\n\nThank you for your time. We’ll follow up with more details soon.\n\nWarmly,\nThe Team"
        return {
            "text": fallback,
            "html": text_to_html(fallback)
        }

    info_block = f"Name: {name}\n" if name else ""
    for key, value in extra_info.items():
        if value:
            info_block += f"{key.replace('_', ' ').title()}: {value}\n"

    if transcript:
        prompt = (
            f"You are a helpful assistant writing personalized follow-up emails for a company.\n"
            f"Use the user's transcript and the provided information to craft a warm, thoughtful, and specific email.\n\n"
            f"Requirements:\n"
            f"- Start with: 'Hi {name},'\n" if name else "- Start with a friendly greeting.\n"
            f"- Write 3–5 friendly, engaging sentences that reflect their experience, company, or interests if available, and reference the transcript.\n"
            f"- End with a kind sign-off like 'Warmly, The Team'\n"
            f"- Output must be plain text only. No HTML. No markdown. No subject line.\n"
            f"- Never ask for more information, never reference missing data, and never mention the process.\n\n"
            f"Context:\n{info_block}\nTranscript:\n\"{transcript}\"\n\n"
            f"Return only the email body text."
        )
    else:
        prompt = (
            f"You are a helpful assistant writing outreach emails for a company.\n"
            f"The user may have shown interest in our product or service.\n\n"
            f"Requirements:\n"
            f"- Start with: 'Hi {name},'\n" if name else "- Start with a friendly greeting.\n"
            f"- Write 3–5 friendly, engaging sentences as if you noticed they might be interested in our product or service, and you want to reach out.\n"
            f"- If available, reference their company, job title, or name, but do not mention missing information.\n"
            f"- End with a kind sign-off like 'Warmly, The Team'\n"
            f"- Output must be plain text only. No HTML. No markdown. No subject line.\n"
            f"- Never ask for more information, never reference missing data, and never mention the process.\n\n"
            f"Context:\n{info_block}\n\n"
            f"Return only the email body text."
        )

    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        plain_text = response.content.strip() if response and response.content else ""
        if not plain_text:
            plain_text = "Hi there,\n\nThank you for your time. We’ll follow up with more details soon.\n\nWarmly,\nThe Team"
        html_version = text_to_html(plain_text)
        return {
            "text": plain_text,
            "html": html_version
        }

    except Exception as e:
        logger.exception("Personalized email generation failed")
        fallback = "Hi there,\n\nThank you for your time. We’ll follow up with more details soon.\n\nWarmly,\nThe Team"
        return {
            "text": fallback,
            "html": text_to_html(fallback)
        }
