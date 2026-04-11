"""Celery tasks — bridge between API and agent orchestrator."""
import asyncio
import uuid
from datetime import datetime
from app.workers.celery_app import celery_app
import structlog

log = structlog.get_logger()


def run_async(coro):
    """Utility to run async code inside Celery sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, name="app.workers.tasks.run_agent_task", max_retries=2)
def run_agent_task(self, user_id: str, preferences: dict, resume_content: str, proxy_config: dict):
    """Main agent task — called by POST /api/agent/start."""
    from app.agents.orchestrator import run_orchestrator
    from app.core.database import AsyncSessionLocal
    from app.models.agent import AgentRun

    run_id = self.request.id or str(uuid.uuid4())
    log.info("Agent task started", user_id=user_id, run_id=run_id)

    try:
        result = run_async(run_orchestrator(
            user_id=user_id,
            run_id=run_id,
            preferences=preferences,
            resume_content=resume_content,
            proxy_config=proxy_config,
        ))

        log.info(
            "Agent task completed",
            user_id=user_id,
            applied=len(result.get("jobs_applied", [])),
        )
        return result

    except Exception as exc:
        log.error("Agent task failed", error=str(exc), user_id=user_id)
        raise self.retry(exc=exc, countdown=300)  # Retry after 5 min


@celery_app.task(name="app.workers.tasks.process_follow_ups")
def process_follow_ups():
    """Hourly: send scheduled follow-up emails."""
    from app.agents.outreach_agent import process_scheduled_follow_ups
    run_async(process_scheduled_follow_ups())


@celery_app.task(name="app.workers.tasks.check_session_health")
def check_session_health():
    """Every 30 min: verify all active browser sessions are valid."""
    log.info("Running session health check")
    # TODO: iterate connected_accounts and verify sessions


@celery_app.task(name="app.workers.tasks.send_email_task")
def send_email_task(sequence_id: str, user_id: str):
    """Send a single queued outreach email."""
    from app.services.email_service import send_sequence_email
    run_async(send_sequence_email(sequence_id, user_id))
