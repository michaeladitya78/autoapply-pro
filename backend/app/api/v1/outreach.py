"""Outreach contacts and email sequences API."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.outreach import OutreachContact, EmailSequence

router = APIRouter()


@router.get("/contacts")
async def list_contacts(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    contacts = (await db.scalars(
        select(OutreachContact).where(OutreachContact.user_id == user_id)
        .order_by(desc(OutreachContact.created_at))
    )).all()
    return [
        {"id": c.id, "name": c.name, "email": c.email,
         "company": c.company, "title": c.title, "verified": c.verified}
        for c in contacts
    ]


@router.get("/emails")
async def list_email_sequences(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    seqs = (await db.scalars(
        select(EmailSequence).where(EmailSequence.user_id == user_id)
        .order_by(desc(EmailSequence.created_at))
        .limit(100)
    )).all()
    return [
        {
            "id": s.id,
            "contact_id": s.contact_id,
            "type": s.sequence_type,
            "status": s.status,
            "subject": s.subject,
            "approved": s.approved,
            "sent_at": s.sent_at.isoformat() if s.sent_at else None,
            "opened": bool(s.opened_at),
            "replied": bool(s.replied_at),
        }
        for s in seqs
    ]


@router.post("/approve-reply/{seq_id}")
async def approve_reply(
    seq_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    seq = await db.scalar(
        select(EmailSequence).where(EmailSequence.id == seq_id, EmailSequence.user_id == user_id)
    )
    if not seq:
        raise HTTPException(404, "Email sequence not found")

    seq.approved = True
    # Trigger send via Celery
    from app.workers.tasks import send_email_task
    send_email_task.apply_async(kwargs={"sequence_id": seq_id, "user_id": user_id})

    return {"status": "approved_and_queued"}
