"""Agent control API — start, pause, resume, status."""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.agent import AgentRun
from app.models.user import User, UserPreferences, Resume
from app.models.account import ConnectedAccount
from app.core.config import settings

log = structlog.get_logger()
router = APIRouter()


class StartAgentRequest(BaseModel):
    run_type: str = "full"  # full | apply_only | outreach_only


@router.post("/start")
async def start_agent(
    request: StartAgentRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start the job application agent."""
    is_dev = settings.ENVIRONMENT == "development"

    # Upsert user record (auto-create in dev)
    user = await db.get(User, user_id)
    if not user:
        if is_dev:
            user = User(id=user_id, email=f"{user_id}@dev.local", plan="pro",
                        onboarding_complete=True, agent_active=False)
            db.add(user)
            await db.flush()
        else:
            raise HTTPException(400, "User not found — complete signup first")

    if not is_dev and not user.onboarding_complete:
        raise HTTPException(400, "Complete onboarding before starting agent")

    # Auto-create preferences in dev
    prefs = await db.scalar(select(UserPreferences).where(UserPreferences.user_id == user_id))
    if not prefs:
        if is_dev:
            import uuid as _uuid
            prefs = UserPreferences(
                id=str(_uuid.uuid4()), user_id=user_id,
                job_titles=["Software Engineer"],
                locations=["Remote"],
                work_type=["remote"],
                daily_application_limit=5,
                daily_email_limit=3,
                tos_agreed=True,
            )
            db.add(prefs)
            await db.flush()
        else:
            raise HTTPException(400, "Set preferences before starting agent")

    if not is_dev and not prefs.tos_agreed:
        raise HTTPException(400, "Must agree to Terms of Service first")

    # Check for already-running agent
    active_run = await db.scalar(
        select(AgentRun).where(
            AgentRun.user_id == user_id,
            AgentRun.status == "running",
        )
    )
    if active_run:
        raise HTTPException(409, "Agent is already running")

    # Get active resume
    resume = await db.scalar(
        select(Resume).where(Resume.user_id == user_id, Resume.is_active == True)
    )
    if not resume:
        if not is_dev:
            raise HTTPException(400, "Upload a resume before starting agent")
        # Dev: use placeholder
        resume_content = "Sample resume: Software Engineer with 3 years experience in Python, FastAPI, React."
    else:
        resume_content = resume.parsed_content or ""

    # Accounts check (relaxed in dev)
    accounts = (await db.scalars(
        select(ConnectedAccount).where(
            ConnectedAccount.user_id == user_id,
            ConnectedAccount.status == "active",
        )
    )).all()
    if not accounts and not is_dev:
        raise HTTPException(400, "Connect at least one job platform")

    # Build proxy config — only if Brightdata credentials are set
    proxy_config = None
    if settings.proxy_configured:
        proxy_config = {
            "host": settings.BRIGHTDATA_HOST,
            "port": settings.BRIGHTDATA_PORT,
            "username": f"{settings.BRIGHTDATA_USERNAME}-session-{user_id[:8]}",
            "password": settings.BRIGHTDATA_PASSWORD,
        }
    else:
        log.warning("No proxy configured — running without residential IP (higher detection risk)")

    # Create run record
    from app.workers.tasks import run_agent_task
    task = run_agent_task.apply_async(
        kwargs={
            "user_id": user_id,
            "preferences": {
                "job_titles": prefs.job_titles,
                "locations": prefs.locations,
                "work_type": prefs.work_type,
                "tech_stack": prefs.tech_stack,
                "salary_min": prefs.salary_min,
                "salary_max": prefs.salary_max,
                "daily_application_limit": prefs.daily_application_limit,
            },
            "resume_content": resume_content,
            "proxy_config": proxy_config,
        },
        queue="agent",
    )

    run = AgentRun(
        user_id=user_id,
        run_type=request.run_type,
        status="running",
        celery_task_id=task.id,
    )
    db.add(run)
    await db.flush()

    # Mark user agent as active
    user.agent_active = True

    log.info("Agent started", user_id=user_id, task_id=task.id)

    return {"status": "started", "run_id": run.id, "task_id": task.id}


@router.post("/pause")
async def pause_agent(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Pause the running agent."""
    run = await db.scalar(
        select(AgentRun).where(AgentRun.user_id == user_id, AgentRun.status == "running")
    )
    if not run:
        raise HTTPException(404, "No active agent run found")

    # Revoke Celery task
    from app.workers.celery_app import celery_app
    celery_app.control.revoke(run.celery_task_id, terminate=False)

    run.status = "paused"
    user = await db.get(User, user_id)
    if user:
        user.agent_active = False

    log.info("Agent paused", user_id=user_id)
    return {"status": "paused"}


@router.post("/resume")
async def resume_agent(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Resume a paused agent run."""
    run = await db.scalar(
        select(AgentRun).where(AgentRun.user_id == user_id, AgentRun.status == "paused")
    )
    if not run:
        raise HTTPException(404, "No paused agent run found")

    run.status = "running"
    user = await db.get(User, user_id)
    if user:
        user.agent_active = True

    log.info("Agent resumed", user_id=user_id)
    return {"status": "resumed"}


@router.get("/status")
async def get_agent_status(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current agent status and latest run summary."""
    run = await db.scalar(
        select(AgentRun).where(AgentRun.user_id == user_id)
        .order_by(AgentRun.started_at.desc())
    )

    if not run:
        return {"status": "idle", "run": None}

    return {
        "status": run.status,
        "run": {
            "id": run.id,
            "started_at": run.started_at,
            "applications": run.applications_submitted,
            "emails": run.emails_sent,
            "actions": run.actions_count,
        },
    }


@router.get("/logs")
async def get_agent_logs(
    limit: int = 50,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get recent agent action log."""
    from app.models.agent import AgentAction
    from sqlalchemy import desc

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
            "timestamp": a.timestamp,
            "requires_human": a.requires_human,
        }
        for a in actions
    ]
