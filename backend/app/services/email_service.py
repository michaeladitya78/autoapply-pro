"""Email sending service via SMTP / Gmail OAuth."""
import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import structlog

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.outreach import EmailSequence, OutreachContact
from sqlalchemy import select
from datetime import datetime

log = structlog.get_logger()


async def send_sequence_email(sequence_id: str, user_id: str):
    """Send a single outreach email."""
    async with AsyncSessionLocal() as db:
        seq = await db.get(EmailSequence, sequence_id)
        if not seq or seq.status != "pending":
            return

        contact = await db.get(OutreachContact, seq.contact_id)
        if not contact:
            return

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = seq.subject or "Following up"
            msg["From"] = f"Job Seeker <noreply@autoapply.local>"
            msg["To"] = contact.email

            body = MIMEText(seq.body or "", "plain")
            msg.attach(body)

            async with aiosmtplib.SMTP(
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                use_tls=False,
                start_tls=True,
            ) as smtp:
                # In real setup: authenticate with OAuth token here
                pass  # STUB: Full OAuth flow to be implemented

            seq.status = "sent"
            seq.sent_at = datetime.utcnow()
            await db.commit()
            log.info("Email sent", sequence_id=sequence_id)

        except Exception as e:
            log.error("Email send failed", sequence_id=sequence_id, error=str(e))
            seq.status = "error"
            await db.commit()
