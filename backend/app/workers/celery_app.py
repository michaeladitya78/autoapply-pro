"""Celery task queue — async bridge to orchestrator."""
from celery import Celery
import asyncio
import structlog

from app.core.config import settings

log = structlog.get_logger()

# Upstash Redis URL format:  rediss://default:[token]@[host].upstash.io:6380
# Note the "rediss://" (double-s) for TLS — required by Upstash.
# redis-py 5.x supports TLS natively, no extra config needed.
celery_app = Celery(
    "autoapply",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.workers.tasks",
        "app.workers.career_ops_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    result_expires=86400,  # 24 hours
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.workers.tasks.run_agent_task": {"queue": "agent"},
        "app.workers.tasks.send_email_task": {"queue": "email"},
        "app.workers.tasks.cleanup_sessions_task": {"queue": "maintenance"},
    },
    beat_schedule={
        "follow-up-emails": {
            "task": "app.workers.tasks.process_follow_ups",
            "schedule": 3600.0,  # Every hour
        },
        "session-health-check": {
            "task": "app.workers.tasks.check_session_health",
            "schedule": 1800.0,  # Every 30 min
        },
    },
)
