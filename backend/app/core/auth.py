"""
Auth helper — Clerk JWT validation.
In dev mode: accepts a simple 'dev-<user_id>' token for local testing without a full Clerk session.
In production: validates against Clerk API.
"""
import httpx
import structlog
from fastapi import Header, HTTPException
from app.core.config import settings

log = structlog.get_logger()

DEV_MODE = settings.ENVIRONMENT == "development"


async def get_current_user(authorization: str = Header(None)) -> str:
    """
    Validate Bearer token. Returns the Clerk user_id.

    Dev shortcut: Pass 'Bearer dev-<anything>' to skip Clerk validation locally.
    e.g., Authorization: Bearer dev-user123
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid authorization header")

    token = authorization.replace("Bearer ", "").strip()

    # ── Dev bypass ─────────────────────────────────────────────────────────
    if DEV_MODE and token.startswith("dev-"):
        user_id = token[4:] or "dev_user_001"
        log.debug("Dev auth bypass", user_id=user_id)
        return user_id

    # ── Production: validate against Clerk ─────────────────────────────────
    if not settings.CLERK_SECRET_KEY:
        raise HTTPException(503, "Auth not configured — set CLERK_SECRET_KEY")

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                "https://api.clerk.com/v1/tokens/verify",
                headers={
                    "Authorization": f"Bearer {settings.CLERK_SECRET_KEY}",
                    "Content-Type": "application/json",
                },
                json={"token": token},
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("sub") or data.get("user_id") or data["id"]
            log.warning("Clerk token invalid", status=resp.status_code)
            raise HTTPException(401, "Invalid or expired token")
    except HTTPException:
        raise
    except Exception as e:
        log.error("Token validation failed", error=str(e))
        raise HTTPException(401, "Token validation error")


async def get_current_user_ws(token: str) -> str | None:
    """WebSocket equivalent of get_current_user."""
    if DEV_MODE and token.startswith("dev-"):
        return token[4:] or "dev_user_001"
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(
                "https://api.clerk.com/v1/tokens/verify",
                headers={"Authorization": f"Bearer {settings.CLERK_SECRET_KEY}"},
                json={"token": token},
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("sub") or data.get("user_id")
    except Exception:
        pass
    return None
