"""Applications list and stats API."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import Optional

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.job import Application

router = APIRouter()


@router.get("")
async def list_applications(
    status: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Application).where(Application.user_id == user_id)
    if status:
        query = query.where(Application.status == status)
    if platform:
        query = query.where(Application.platform == platform)
    query = query.order_by(desc(Application.applied_at)).limit(limit).offset(offset)

    apps = (await db.scalars(query)).all()

    return [
        {
            "id": a.id,
            "company": a.company,
            "title": a.title,
            "platform": a.platform,
            "status": a.status,
            "applied_at": a.applied_at.isoformat(),
            "job_url": a.job_url,
        }
        for a in apps
    ]


@router.get("/{app_id}")
async def get_application(
    app_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    app = await db.scalar(
        select(Application).where(
            Application.id == app_id,
            Application.user_id == user_id,
        )
    )
    if not app:
        from fastapi import HTTPException
        raise HTTPException(404, "Application not found")

    return {
        "id": app.id,
        "company": app.company,
        "title": app.title,
        "platform": app.platform,
        "status": app.status,
        "applied_at": app.applied_at.isoformat(),
        "cover_letter": app.cover_letter,
        "notes": app.notes,
        "agent_log": app.agent_log,
    }
