"""Stripe payment integration — checkout sessions and webhook handling."""
from __future__ import annotations

import structlog
from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.core.config import settings


log = structlog.get_logger()

router = APIRouter()


def _stripe():
    """Lazy-import stripe so the app starts without STRIPE_SECRET_KEY in dev."""
    import stripe as _stripe_lib
    _stripe_lib.api_key = settings.STRIPE_SECRET_KEY
    return _stripe_lib


@router.get("/checkout")
async def create_checkout_session(request: Request, plan: str = "pro"):
    """
    Create a Stripe Checkout session and redirect to it.
    Matches frontend usage: <a href="/api/billing/checkout?plan=pro">
    """
    if not settings.stripe_configured:
        raise HTTPException(status_code=503, detail="Payments not configured")

    # Since it's a GET, we use query parameters and default URLs
    success_url = "https://autoapplypro.com/dashboard?upgraded=1"
    cancel_url = "https://autoapplypro.com/pricing"

    price_id = (
        settings.STRIPE_PRO_PRICE_ID if plan == "pro"
        else settings.STRIPE_TEAM_PRICE_ID
    )

    if not price_id:
        raise HTTPException(status_code=400, detail=f"Price ID for {plan!r} not configured")

    stripe = _stripe()
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"plan": plan},
    )
    return RedirectResponse(url=session.url, status_code=303)


@router.post("/stripe-webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
    """
    Handle Stripe webhook events.
    Listens for checkout.session.completed to upgrade user plan in Supabase.
    """
    if not settings.stripe_configured:
        return JSONResponse({"received": True})

    stripe = _stripe()
    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        log.error("Stripe webhook signature invalid", error=str(e))
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        customer_email = session.get("customer_details", {}).get("email", "")
        plan = session.get("metadata", {}).get("plan", "pro")

        log.info("Stripe checkout completed", email=customer_email, plan=plan)

        # Update user plan in Supabase
        if settings.supabase_configured:
            import httpx
            async with httpx.AsyncClient() as client:
                # Find user by email via Supabase REST
                resp = await client.get(
                    f"{settings.SUPABASE_URL}/rest/v1/users",
                    headers={
                        "apikey": settings.SUPABASE_SERVICE_KEY,
                        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
                    },
                    params={"email": f"eq.{customer_email}", "select": "id"},
                )
                users = resp.json()
                if users:
                    user_id = users[0]["id"]
                    await client.patch(
                        f"{settings.SUPABASE_URL}/rest/v1/users?id=eq.{user_id}",
                        headers={
                            "apikey": settings.SUPABASE_SERVICE_KEY,
                            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
                            "Content-Type": "application/json",
                        },
                        json={"plan": plan},
                    )
                    log.info("User plan upgraded", user_id=user_id, plan=plan)

    return {"received": True}
