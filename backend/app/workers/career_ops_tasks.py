"""
Career-Ops Celery Tasks
=======================
Async background tasks for the career-ops automation layer.

Tasks:
  sync_career_ops_tracker   – Bi-directional markdown ↔ DB sync (every 15 min)
  run_portal_scan_task      – Trigger scan.mjs for a specific user
  analyze_patterns_task     – Run analyze-patterns.mjs for a user
  followup_cadence_task     – Daily follow-up cadence check for all active users
  generate_pdf_task         – Generate ATS-optimised PDF for an application
"""
import asyncio

import structlog
from celery import shared_task
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.user import User

log = structlog.get_logger(__name__)


def _run_async(coro):
    """Helper: run an async coroutine from a synchronous Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ─── Tracker Sync ─────────────────────────────────────────────────────────────


@shared_task(
    name="career_ops.sync_tracker",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="career_ops",
)
def sync_career_ops_tracker(self, user_id: str):
    """
    Parse this user's career-ops applications.md and upsert into PostgreSQL.
    Safe to run frequently — it upserts, never duplicates.
    """
    from app.services import career_ops_service as cos

    async def _sync():
        async with AsyncSessionLocal() as db:
            rows = await cos.sync_tracker_to_db(user_id, db)
            await db.commit()
            return rows

    try:
        rows = _run_async(_sync())
        log.info("Tracker sync complete", user_id=user_id, rows=rows)
        return {"user_id": user_id, "rows_upserted": rows}
    except Exception as exc:
        log.error("Tracker sync failed", user_id=user_id, exc=str(exc))
        raise self.retry(exc=exc)


# ─── Portal Scan ──────────────────────────────────────────────────────────────


@shared_task(
    name="career_ops.run_portal_scan",
    bind=True,
    max_retries=2,
    default_retry_delay=300,
    queue="career_ops",
    time_limit=600,
    soft_time_limit=540,
)
def run_portal_scan_task(self, user_id: str):
    """
    Run scan.mjs for this user — discovers new job listings matching their profile
    and adds them to data/pipeline.md.
    """
    from app.services import career_ops_service as cos

    async def _scan():
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select as sa_select
            from app.models.user import User, UserPreferences

            user = await db.get(User, user_id)
            prefs = await db.scalar(
                sa_select(UserPreferences).where(UserPreferences.user_id == user_id)
            )
            user_data = {
                "full_name": getattr(user, "full_name", "") or "",
                "email": getattr(user, "email", "") or "",
                "job_titles": getattr(prefs, "job_titles", []) if prefs else [],
                "salary_min": getattr(prefs, "salary_min", None) if prefs else None,
                "salary_max": getattr(prefs, "salary_max", None) if prefs else None,
                "work_type": getattr(prefs, "work_type", []) if prefs else [],
            }

        await cos.generate_profile_yml(user_id, user_data)
        result = await cos.run_script(user_id, "scan.mjs", timeout=480)
        return result

    try:
        result = _run_async(_scan())
        if result["returncode"] != 0:
            log.warning("Scan script returned non-zero", user_id=user_id, stderr=result["stderr"][:300])
        log.info("Portal scan complete", user_id=user_id, rc=result["returncode"])
        return {"user_id": user_id, "returncode": result["returncode"]}
    except Exception as exc:
        log.error("Portal scan failed", user_id=user_id, exc=str(exc))
        raise self.retry(exc=exc)


# ─── Pattern Analysis ─────────────────────────────────────────────────────────


@shared_task(
    name="career_ops.analyze_patterns",
    bind=True,
    max_retries=2,
    queue="career_ops",
    time_limit=120,
)
def analyze_patterns_task(self, user_id: str):
    """
    Run analyze-patterns.mjs for this user and return structured JSON.
    Typically triggered after each tracker sync.
    """
    from app.services import career_ops_service as cos

    try:
        result = _run_async(cos.run_script(user_id, "analyze-patterns.mjs", timeout=90))
        return {
            "user_id": user_id,
            "patterns": result.get("json"),
            "returncode": result["returncode"],
        }
    except Exception as exc:
        log.error("Pattern analysis failed", user_id=user_id, exc=str(exc))
        raise self.retry(exc=exc)


# ─── Follow-Up Cadence ────────────────────────────────────────────────────────


@shared_task(
    name="career_ops.followup_cadence",
    bind=True,
    max_retries=2,
    queue="career_ops",
    time_limit=120,
)
def followup_cadence_task(self, user_id: str):
    """
    Run followup-cadence.mjs for a user and return due follow-ups.
    Schedule this daily via Celery Beat.
    """
    from app.services import career_ops_service as cos

    try:
        result = _run_async(cos.run_script(user_id, "followup-cadence.mjs", timeout=90))
        followups = result.get("json") or {}
        due = followups.get("due", [])

        if due:
            log.info("Follow-ups due", user_id=user_id, count=len(due))
            # TODO: push WebSocket notification to user

        return {"user_id": user_id, "due_count": len(due), "followups": followups}
    except Exception as exc:
        log.error("Follow-up cadence failed", user_id=user_id, exc=str(exc))
        raise self.retry(exc=exc)


# ─── PDF Generation ───────────────────────────────────────────────────────────


@shared_task(
    name="career_ops.generate_pdf",
    bind=True,
    max_retries=2,
    queue="career_ops",
    time_limit=180,
    soft_time_limit=150,
)
def generate_pdf_task(self, user_id: str, app_id: str, company: str, role: str):
    """
    Generate an ATS-optimised PDF for a job application using generate-pdf.mjs.
    Updates the application record with the PDF path on success.
    """
    from app.services import career_ops_service as cos

    async def _gen():
        result = await cos.run_script(
            user_id,
            "generate-pdf.mjs",
            args=["--company", company, "--role", role],
            timeout=120,
        )
        if result["returncode"] == 0:
            udir = cos.user_dir(user_id)
            slug = company.lower().replace(" ", "-")
            pdfs = sorted(
                (udir / "output").glob(f"*{slug}*.pdf"),
                key=lambda p: p.stat().st_mtime,
            )
            if pdfs:
                pdf_rel = str(pdfs[-1].relative_to(udir))
                async with AsyncSessionLocal() as db:
                    from app.models.job import Application
                    app = await db.get(Application, app_id)
                    if app:
                        app.career_ops_pdf_path = pdf_rel
                        await db.commit()
                return pdf_rel
        return None

    try:
        pdf_path = _run_async(_gen())
        log.info("PDF generation complete", user_id=user_id, app_id=app_id, path=pdf_path)
        return {"user_id": user_id, "app_id": app_id, "pdf_path": pdf_path}
    except Exception as exc:
        log.error("PDF generation failed", user_id=user_id, app_id=app_id, exc=str(exc))
        raise self.retry(exc=exc)


# ─── Beat Schedule Helper ─────────────────────────────────────────────────────


def register_beat_tasks(beat_schedule: dict, user_ids: list[str]) -> dict:
    """
    Dynamically add per-user follow-up cadence tasks to the Celery Beat schedule.
    Call this at worker startup from celery_app.py.

    Usage in celery_app.py:
        from app.workers.career_ops_tasks import register_beat_tasks
        app.conf.beat_schedule.update(register_beat_tasks(app.conf.beat_schedule, ["uid1",...]))
    """
    for uid in user_ids:
        beat_schedule[f"followup_cadence_{uid}"] = {
            "task": "career_ops.followup_cadence",
            "schedule": 86400,  # daily
            "args": (uid,),
        }
        beat_schedule[f"sync_tracker_{uid}"] = {
            "task": "career_ops.sync_tracker",
            "schedule": 900,  # every 15 min
            "args": (uid,),
        }
    return beat_schedule
