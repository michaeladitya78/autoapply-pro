"""
Email sending service via Resend API.

Replaces the aiosmtplib / Gmail SMTP approach.
Resend (resend.com) handles deliverability, SPF/DKIM/DMARC, and open tracking
automatically. Free tier: 3,000 emails/month.

Setup:
  1. Sign up at resend.com → get API key
  2. Add your domain → copy/paste the DNS records they provide (SPF, DKIM, DMARC)
  3. Set RESEND_API_KEY and RESEND_FROM_EMAIL in Railway env vars

No SMTP port, no OAuth flow, no Gmail app passwords — just one API call.
"""
import structlog
import httpx

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.outreach import EmailSequence, OutreachContact
from sqlalchemy import select
from datetime import datetime

log = structlog.get_logger()

RESEND_API_URL = "https://api.resend.com/emails"


async def _send_via_resend(
    to: str,
    subject: str,
    html_body: str,
    from_email: str | None = None,
) -> dict:
    """
    Send a single email via Resend REST API.
    Returns the Resend response dict.

    Raises on HTTP error (caller handles retry logic).
    """
    if not settings.resend_configured:
        log.warning("Resend not configured — email send skipped")
        return {"id": "skipped-no-api-key"}

    from_addr = from_email or settings.RESEND_FROM_EMAIL

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            RESEND_API_URL,
            headers={
                "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": from_addr,
                "to": [to],
                "subject": subject,
                "html": html_body,
            },
        )
        resp.raise_for_status()
        return resp.json()


async def send_sequence_email(sequence_id: str, user_id: str):
    """Send a single outreach email from a queued sequence step."""
    async with AsyncSessionLocal() as db:
        seq = await db.get(EmailSequence, sequence_id)
        if not seq or seq.status != "pending":
            return

        contact = await db.get(OutreachContact, seq.contact_id)
        if not contact:
            return

        subject = seq.subject or "Following up"
        body_html = seq.body or ""

        # Convert plain text to minimal HTML if needed
        if body_html and not body_html.strip().startswith("<"):
            body_html = "<br>".join(body_html.splitlines())

        try:
            result = await _send_via_resend(
                to=contact.email,
                subject=subject,
                html_body=body_html,
            )
            seq.status = "sent"
            seq.sent_at = datetime.utcnow()
            log.info("Email sent via Resend", sequence_id=sequence_id, resend_id=result.get("id"))

        except httpx.HTTPStatusError as e:
            log.error("Resend HTTP error", sequence_id=sequence_id, status=e.response.status_code, body=e.response.text[:200])
            seq.status = "error"

        except Exception as e:
            log.error("Email send failed", sequence_id=sequence_id, error=str(e))
            seq.status = "error"

        await db.commit()


async def send_transactional_email(
    to: str,
    subject: str,
    html_body: str,
    from_email: str | None = None,
) -> bool:
    """
    Send a one-off transactional email (notifications, alerts, etc.)
    Returns True on success.
    """
    try:
        await _send_via_resend(to=to, subject=subject, html_body=html_body, from_email=from_email)
        return True
    except Exception as e:
        log.error("Transactional email failed", to=to, error=str(e))
        return False
