"""Human-in-the-loop flags API."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.agent import HumanFlag

router = APIRouter()


@router.get("")
async def list_flags(
    status: str = "pending",
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    flags = (await db.scalars(
        select(HumanFlag)
        .where(HumanFlag.user_id == user_id, HumanFlag.status == status)
        .order_by(desc(HumanFlag.created_at))
    )).all()

    return [
        {
            "id": f.id,
            "type": f.flag_type,
            "platform": f.platform,
            "description": f.description,
            "screenshot_url": f.screenshot_url,
            "created_at": f.created_at.isoformat(),
        }
        for f in flags
    ]


@router.post("/{flag_id}/resolve")
async def resolve_flag(
    flag_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    flag = await db.scalar(
        select(HumanFlag).where(HumanFlag.id == flag_id, HumanFlag.user_id == user_id)
    )
    if not flag:
        raise HTTPException(404, "Flag not found")

    flag.status = "resolved"
    flag.resolved_at = datetime.utcnow()

    return {"status": "resolved"}
