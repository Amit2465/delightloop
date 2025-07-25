import asyncio
import logging

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Content, Email, Mail, To

from app.core.config import settings

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def text_to_html(text: str) -> str:
    """
    Converts a plain text email body (with `\n`) into HTML using <br> tags.
    """
    escaped = text.replace("\n", "<br>")
    return f"<html><body>{escaped}</body></html>"


async def send_email_async(
    to_email: str,
    subject: str,
    content: str,
) -> dict:
    html_version = text_to_html(content)

    message = Mail(
        from_email=Email(settings.email),
        to_emails=To(to_email),
        subject=subject,
        plain_text_content=Content("text/plain", content),
        html_content=Content("text/html", html_version),
    )

    try:
        sg = SendGridAPIClient(api_key=settings.sendgrid_api_key)

        # Proper async wrapping for sync call
        response = await asyncio.to_thread(sg.send, message)

        logger.info(f"SendGrid Status: {response.status_code}")
        logger.info(f"SendGrid Response Body: {getattr(response, 'body', None)}")
        logger.debug(f"Headers: {response.headers}")

        return {
            "status_code": response.status_code,
            "message_id": response.headers.get("X-Message-Id", None),
            "body": getattr(response, 'body', None),
        }

    except Exception as e:
        logger.error(f"SendGrid error occurred: {str(e)}", exc_info=True)
        return {"status_code": 500, "error": f"Email failed to send: {str(e)}"}
