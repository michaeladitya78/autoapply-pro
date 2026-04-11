"""Clerk webhook handler — user creation/deletion events."""
from fastapi import APIRouter, Request, HTTPException, Header
import structlog
from svix.webhooks import Webhook, WebhookVerificationError
import json

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.user import User, UserPreferences
import uuid

log = structlog.get_logger()
router = APIRouter()


@router.post("/clerk")
async def clerk_webhook(
    request: Request,
    svix_id: str = Header(None, alias="svix-id"),
    svix_timestamp: str = Header(None, alias="svix-timestamp"),
    svix_signature: str = Header(None, alias="svix-signature"),
):
    """Handle Clerk user lifecycle events."""
    payload = await request.body()

    # Verify webhook signature
    try:
        wh = Webhook(settings.CLERK_WEBHOOK_SECRET)
        evt = wh.verify(payload, {
            "svix-id": svix_id,
            "svix-timestamp": svix_timestamp,
            "svix-signature": svix_signature,
        })
    except WebhookVerificationError:
        raise HTTPException(401, "Invalid webhook signature")

    event_type = evt.get("type")
    data = evt.get("data", {})

    async with AsyncSessionLocal() as db:
        if event_type == "user.created":
            user = User(
                id=data["id"],
                email=data["email_addresses"][0]["email_address"],
                name=f"{data.get('first_name', '')} {data.get('last_name', '')}".strip(),
                plan="free",
            )
            prefs = UserPreferences(id=str(uuid.uuid4()), user_id=data["id"])
            db.add(user)
            db.add(prefs)
            await db.commit()
            log.info("User created", user_id=data["id"])

        elif event_type == "user.deleted":
            user = await db.get(User, data["id"])
            if user:
                # Destroy all sessions and credentials
                from app.models.account import ConnectedAccount
                from sqlalchemy import select
                from app.core.vault import delete_credential
                accounts = (await db.scalars(
                    select(ConnectedAccount).where(ConnectedAccount.user_id == data["id"])
                )).all()
                for acc in accounts:
                    if acc.vault_ref:
                        try:
                            delete_credential(acc.vault_ref)
                        except Exception:
                            pass
                await db.delete(user)
                await db.commit()
                log.info("User deleted and credentials purged", user_id=data["id"])

    return {"status": "ok"}
