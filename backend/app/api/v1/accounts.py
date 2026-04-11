"""Connected accounts API — platform session management."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
import uuid

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.account import ConnectedAccount
from app.core.vault import delete_credential

router = APIRouter()

SUPPORTED_PLATFORMS = ["linkedin", "indeed", "naukri", "glassdoor", "wellfound", "dice", "ziprecruiter"]


class ConnectAccountRequest(BaseModel):
    platform: str
    auth_method: str = "browser_profile"  # browser_profile | vault_credential | oauth


@router.get("")
async def list_accounts(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    accounts = (await db.scalars(
        select(ConnectedAccount).where(ConnectedAccount.user_id == user_id)
    )).all()
    return [
        {
            "id": a.id,
            "platform": a.platform,
            "status": a.status,
            "auth_method": a.auth_method,
            "last_verified": a.last_verified,
            "applications_today": a.applications_today,
        }
        for a in accounts
    ]


@router.post("/connect")
async def connect_account(
    body: ConnectAccountRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.platform not in SUPPORTED_PLATFORMS:
        raise HTTPException(400, f"Platform {body.platform} not supported. Choose from: {SUPPORTED_PLATFORMS}")

    existing = await db.scalar(
        select(ConnectedAccount).where(
            ConnectedAccount.user_id == user_id,
            ConnectedAccount.platform == body.platform,
        )
    )
    if existing:
        return {"account_id": existing.id, "status": "already_connected"}

    account = ConnectedAccount(
        id=str(uuid.uuid4()),
        user_id=user_id,
        platform=body.platform,
        auth_method=body.auth_method,
        status="pending_login",
    )
    db.add(account)
    await db.flush()

    return {
        "account_id": account.id,
        "status": "pending_login",
        "next_step": f"Open sandboxed browser to login to {body.platform}",
    }


@router.delete("/{account_id}")
async def disconnect_account(
    account_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    account = await db.scalar(
        select(ConnectedAccount).where(
            ConnectedAccount.id == account_id,
            ConnectedAccount.user_id == user_id,
        )
    )
    if not account:
        raise HTTPException(404, "Account not found")

    # Destroy credentials from Vault
    if account.vault_ref:
        try:
            delete_credential(account.vault_ref)
        except Exception:
            pass

    # Clear session data
    account.session_encrypted = None
    account.oauth_token_encrypted = None
    account.status = "disconnected"
    account.profile_path = None

    return {"status": "disconnected", "platform": account.platform}


@router.get("/{account_id}/status")
async def get_account_status(
    account_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    account = await db.scalar(
        select(ConnectedAccount).where(
            ConnectedAccount.id == account_id,
            ConnectedAccount.user_id == user_id,
        )
    )
    if not account:
        raise HTTPException(404, "Account not found")

    return {
        "platform": account.platform,
        "status": account.status,
        "last_verified": account.last_verified,
        "applications_today": account.applications_today,
    }
