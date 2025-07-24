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
    """
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=settings.gemini_api_key,
    )

    # Dynamically build info block
    info_block = f"Name: {name}\n"
    if extra_info:
        for key, value in extra_info.items():
            if value:
                info_block += f"{key.replace('_', ' ').title()}: {value}\n"

    prompt = (
        f"You are a helpful assistant writing personalized follow-up emails for a company.\n"
        f"Use the user's transcript and the provided information to craft a warm, thoughtful email.\n\n"
        f"Requirements:\n"
        f"- Start with: 'Hi {name},'\n"
        f"- Write 3–5 friendly, engaging sentences that reflect their experience\n"
        f"- Include references to their job title, company, or interests if available\n"
        f"- End with a kind sign-off like 'Warmly, The Team'\n"
        f"- Output must be plain text only. No HTML. No markdown. No subject line.\n\n"
        f"Context:\n{info_block}\nTranscript:\n\"{transcript}\"\n\n"
        f"Return only the email body text."
    )

    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        plain_text = response.content.strip()
        html_version = text_to_html(plain_text)

        return {
            "text": plain_text,
            "html": html_version
        }

    except Exception as e:
        logger.exception("Personalized email generation failed")
        fallback = f"Hi {name},\n\nThank you for your time. We’ll follow up with more details soon.\n\nWarmly,\nThe Team"
        return {
            "text": fallback,
            "html": text_to_html(fallback)
        }
