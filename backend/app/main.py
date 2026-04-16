"""
AutoApply Pro — FastAPI Application Entry Point
"""
from contextlib import asynccontextmanager
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.core.websocket_manager import ws_manager
from app.api.v1 import (
    auth, users, accounts, agent, applications,
    outreach, dashboard, flags, resume, webhook,
    career_ops, stripe_payments,
)

log = structlog.get_logger()


import asyncio

startup_error = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    global startup_error
    log.info("Starting AutoApply Pro", env=settings.ENVIRONMENT)
    try:
        await init_db()
    except Exception as e:
        import traceback
        startup_error = traceback.format_exc()
        log.error("init_db failed", error=startup_error)
    
    pubsub_task = None
    try:
        # Start Redis Pub/Sub listener for WebSockets
        pubsub_task = asyncio.create_task(ws_manager.start_redis_listener())
    except Exception as e:
        import traceback
        if startup_error is None: startup_error = traceback.format_exc()
        else: startup_error += "\n\n" + traceback.format_exc()
        log.error("pubsub failed", error=str(e))
        
    yield
    
    log.info("Shutting down AutoApply Pro")
    if pubsub_task:
        pubsub_task.cancel()
        try:
            await pubsub_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="AutoApply Pro API",
    description="AI-powered autonomous job application engine",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# ─── Middleware ───────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ─── Routers ──────────────────────────────────────────────────────────────────
app.include_router(webhook.router, prefix="/api/webhooks", tags=["webhooks"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/user", tags=["user"])
app.include_router(resume.router, prefix="/api/resume", tags=["resume"])
app.include_router(accounts.router, prefix="/api/accounts", tags=["accounts"])
app.include_router(agent.router, prefix="/api/agent", tags=["agent"])
app.include_router(applications.router, prefix="/api/applications", tags=["applications"])
app.include_router(outreach.router, prefix="/api/outreach", tags=["outreach"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(flags.router, prefix="/api/flags", tags=["flags"])
app.include_router(career_ops.router, prefix="/api/career-ops", tags=["career-ops"])
app.include_router(stripe_payments.router, prefix="/api/billing", tags=["billing"])

# WebSocket for real-time updates
from fastapi import WebSocket, WebSocketDisconnect
from app.core.auth import get_current_user_ws

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await ws_manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            # ping-pong keepalive
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(user_id)


@app.get("/health")
async def health_check():
    global startup_error
    if startup_error:
        return {"status": "error", "service": "autoapply-pro", "error": startup_error}
    return {"status": "ok", "service": "autoapply-pro"}
