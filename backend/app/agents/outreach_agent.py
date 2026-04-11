"""
Outreach Agent — Contact discovery and email drafting.
Uses Hunter.io for contact lookup and Claude for email generation.
"""
import httpx
import uuid
import structlog
from datetime import datetime, timedelta
from app.core.config import settings
from app.agents.llm import claude_draft_cold_email

log = structlog.get_logger()


class OutreachAgent:
    def __init__(self, user_id: str, preferences: dict, resume_content: str):
        self.user_id = user_id
        self.preferences = preferences
        self.resume_content = resume_content

    async def find_and_draft(self, applied_jobs: list) -> list:
        """Find contacts and draft cold emails for applied jobs."""
        contacts_with_emails = []

        for job in applied_jobs[:self.preferences.get("daily_email_limit", 10)]:
            try:
                company = job.get("company", "")
                if not company:
                    continue

                # Find contact via Hunter.io
                contact = await self._find_contact_hunter(company)
                if not contact:
                    contact = await self._find_contact_apollo(company)

                if not contact or not contact.get("email"):
                    continue

                # Draft email with Claude
                email_draft = await claude_draft_cold_email(
                    my_resume=self.resume_content,
                    contact_name=contact.get("name", "Hiring Manager"),
                    contact_title=contact.get("title", "Recruiter"),
                    company=company,
                    job_role=job.get("title", ""),
                )

                contacts_with_emails.append({
                    "contact": contact,
                    "email_draft": email_draft,
                    "job": job,
                })

            except Exception as e:
                log.error("Outreach contact failed", company=job.get("company"), error=str(e))

        return contacts_with_emails

    async def _find_contact_hunter(self, company: str) -> dict | None:
        """Look up hiring manager email via Hunter.io API."""
        if not settings.HUNTER_API_KEY:
            return None
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                # Get domain first
                domain_resp = await client.get(
                    "https://api.hunter.io/v2/domain-search",
                    params={
                        "company": company,
                        "api_key": settings.HUNTER_API_KEY,
                        "limit": 5,
                        "type": "personal",
                    },
                )
                data = domain_resp.json().get("data", {})
                emails = data.get("emails", [])
                if emails:
                    e = emails[0]
                    return {
                        "name": f"{e.get('first_name', '')} {e.get('last_name', '')}".strip(),
                        "email": e.get("value"),
                        "title": e.get("position", ""),
                        "found_via": "hunter",
                        "verified": e.get("verification", {}).get("status") == "valid",
                    }
        except Exception as e:
            log.warning("Hunter.io lookup failed", error=str(e))
        return None

    async def _find_contact_apollo(self, company: str) -> dict | None:
        """Fallback: look up via Apollo.io API."""
        if not settings.APOLLO_API_KEY:
            return None
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    "https://api.apollo.io/v1/mixed_people/search",
                    headers={"X-Api-Key": settings.APOLLO_API_KEY},
                    json={
                        "organization_name": company,
                        "person_titles": ["recruiter", "hiring manager", "talent", "engineering manager"],
                        "per_page": 3,
                    },
                )
                people = resp.json().get("people", [])
                if people:
                    p = people[0]
                    email = p.get("email") or p.get("email_status")
                    if email and "@" in str(email):
                        return {
                            "name": p.get("name", ""),
                            "email": email,
                            "title": p.get("title", ""),
                            "found_via": "apollo",
                            "verified": True,
                        }
        except Exception as e:
            log.warning("Apollo lookup failed", error=str(e))
        return None


async def process_scheduled_follow_ups():
    """Celery Beat task: send due follow-up emails."""
    from app.core.database import AsyncSessionLocal
    from app.models.outreach import EmailSequence
    from sqlalchemy import select, and_
    from sqlalchemy.orm import selectinload

    now = datetime.utcnow()
    async with AsyncSessionLocal() as db:
        due_sequences = (await db.scalars(
            select(EmailSequence).where(
                and_(
                    EmailSequence.status == "pending",
                    EmailSequence.approved == True,
                    EmailSequence.scheduled_at <= now,
                )
            )
        )).all()

        log.info("Processing follow-ups", count=len(due_sequences))

        for seq in due_sequences:
            try:
                from app.services.email_service import send_sequence_email
                await send_sequence_email(seq.id, seq.user_id)
            except Exception as e:
                log.error("Follow-up send failed", seq_id=seq.id, error=str(e))
