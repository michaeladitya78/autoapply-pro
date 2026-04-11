"""User preferences API."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import UserPreferences
import uuid

router = APIRouter()


class PreferencesUpdate(BaseModel):
    job_titles: List[str] = []
    locations: List[str] = []
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    work_type: List[str] = []
    tech_stack: List[str] = []
    industries: List[str] = []
    daily_application_limit: int = 20
    daily_email_limit: int = 10
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    years_of_experience: Optional[int] = None
    exclude_companies: List[str] = []
    tos_agreed: bool = False


@router.get("/preferences")
async def get_preferences(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    prefs = await db.scalar(select(UserPreferences).where(UserPreferences.user_id == user_id))
    if not prefs:
        return {}
    return prefs.__dict__


@router.put("/preferences")
async def update_preferences(
    body: PreferencesUpdate,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    prefs = await db.scalar(select(UserPreferences).where(UserPreferences.user_id == user_id))
    if not prefs:
        prefs = UserPreferences(id=str(uuid.uuid4()), user_id=user_id)
        db.add(prefs)

    for key, val in body.model_dump().items():
        setattr(prefs, key, val)

    if body.tos_agreed and not prefs.tos_agreed_at:
        prefs.tos_agreed_at = datetime.utcnow()

    return {"status": "updated"}
