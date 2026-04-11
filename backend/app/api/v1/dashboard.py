"""Dashboard stats and activity feed API."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.job import Application
from app.models.agent import AgentAction, HumanFlag
from app.models.outreach import EmailSequence

router = APIRouter()


@router.get("/stats")
async def get_dashboard_stats(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return aggregated stats for the dashboard."""
    # Applications by status
    apps = (await db.scalars(
        select(Application).where(Application.user_id == user_id)
    )).all()

    by_status = {}
    for app in apps:
        by_status[app.status] = by_status.get(app.status, 0) + 1

    # This week applications
    week_ago = datetime.utcnow() - timedelta(days=7)
    week_apps = sum(1 for a in apps if a.applied_at >= week_ago)

    # Emails
    emails = (await db.scalars(
        select(EmailSequence).where(EmailSequence.user_id == user_id)
    )).all()

    email_stats = {
        "sent": sum(1 for e in emails if e.sent_at),
        "opened": sum(1 for e in emails if e.opened_at),
        "replied": sum(1 for e in emails if e.replied_at),
    }

    response_rate = 0
    if email_stats["sent"] > 0:
        response_rate = round(email_stats["replied"] / email_stats["sent"] * 100, 1)

    interview_rate = 0
    if len(apps) > 0:
        interviews = by_status.get("interview", 0) + by_status.get("offer", 0)
        interview_rate = round(interviews / len(apps) * 100, 1)

    # Pending human flags
    pending_flags = await db.scalar(
        select(func.count(HumanFlag.id)).where(
            HumanFlag.user_id == user_id,
            HumanFlag.status == "pending",
        )
    )

    return {
        "applications": {
            "total": len(apps),
            "this_week": week_apps,
            "by_status": by_status,
            "interview_rate": interview_rate,
        },
        "outreach": {
            **email_stats,
            "response_rate": response_rate,
        },
        "flags": {"pending": pending_flags or 0},
    }


@router.get("/activity-feed")
async def get_activity_feed(
    limit: int = 30,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Recent activity log for dashboard feed."""
    actions = (await db.scalars(
        select(AgentAction)
        .where(AgentAction.user_id == user_id)
        .order_by(desc(AgentAction.timestamp))
        .limit(limit)
    )).all()

    return [
        {
            "id": a.id,
            "type": a.action_type,
            "platform": a.platform,
            "details": a.details,
            "timestamp": a.timestamp.isoformat(),
            "requires_human": a.requires_human,
        }
        for a in actions
    ]
