"""
Career-Ops API Endpoints
========================
Bridge between the Next.js dashboard and the career-ops Node.js automation layer.

Routes:
  POST /api/career-ops/pipeline          – Add a job URL to the user's pending inbox
  GET  /api/career-ops/pipeline          – List pending job URLs
  POST /api/career-ops/scan              – Trigger a portal scan (async)
  POST /api/career-ops/evaluate          – Evaluate a JD URL (async)
  POST /api/career-ops/pdf/{app_id}      – Generate ATS-optimised CV PDF
  GET  /api/career-ops/patterns          – Run rejection-pattern analysis
  GET  /api/career-ops/followups         – Follow-up cadence report
  GET  /api/career-ops/interview/{slug}  – Get interview prep file
  POST /api/career-ops/sync              – Force sync tracker ↔ DB
  GET  /api/career-ops/profile           – Get the user's profile.yml
  PUT  /api/career-ops/profile           – Update the user's profile.yml
"""
from pathlib import Path

import structlog
import yaml
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, HttpUrl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.job import Application
from app.models.user import User, UserPreferences, Resume
from app.services import career_ops_service as cos

log = structlog.get_logger(__name__)
router = APIRouter()

# ─── Helpers ──────────────────────────────────────────────────────────────────


async def _build_user_data(user_id: str, db: AsyncSession) -> dict:
    """Assemble user data dict for profile.yml generation."""
    user = await db.get(User, user_id)
    prefs = await db.scalar(
        select(UserPreferences).where(UserPreferences.user_id == user_id)
    )
    resume = await db.scalar(
        select(Resume).where(Resume.user_id == user_id, Resume.is_active == True)
    )
    return {
        "full_name": getattr(user, "full_name", "") or "",
        "email": getattr(user, "email", "") or "",
        "phone": getattr(user, "phone", "") or "",
        "location": getattr(prefs, "locations", [""])[0] if prefs else "",
        "headline": getattr(user, "headline", "") or "",
        "job_titles": getattr(prefs, "job_titles", []) if prefs else [],
        "salary_min": getattr(prefs, "salary_min", None) if prefs else None,
        "salary_max": getattr(prefs, "salary_max", None) if prefs else None,
        "work_type": getattr(prefs, "work_type", []) if prefs else [],
    }


# ─── Pipeline (URL inbox) ─────────────────────────────────────────────────────


class PipelineAddRequest(BaseModel):
    url: str
    note: str = ""


@router.post("/pipeline", status_code=201)
async def add_to_pipeline(
    body: PipelineAddRequest,
    user_id: str = Depends(get_current_user),
):
    """Add a job URL to the user's career-ops pipeline inbox."""
    await cos.write_pipeline_url(user_id, body.url, body.note)
    return {"added": True, "url": body.url}


@router.get("/pipeline")
async def get_pipeline(
    user_id: str = Depends(get_current_user),
):
    """Return the list of pending job URLs in the user's inbox."""
    urls = await cos.read_pipeline_urls(user_id)
    return {"urls": urls, "count": len(urls)}


# ─── Portal Scan ──────────────────────────────────────────────────────────────


@router.post("/scan")
async def trigger_scan(
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger an async portal scan (scan.mjs) for this user.
    The scan finds new job listings matching the user's profile and adds them
    to data/pipeline.md.
    """
    user_data = await _build_user_data(user_id, db)
    await cos.generate_profile_yml(user_id, user_data)

    async def _scan():
        result = await cos.run_script(user_id, "scan.mjs", timeout=300)
        log.info("Scan complete", user_id=user_id, rc=result["returncode"])

    background_tasks.add_task(_scan)
    return {"status": "scan_started", "message": "Portal scan queued. Check pipeline for results."}


# ─── Offer Evaluation ─────────────────────────────────────────────────────────


class EvaluateRequest(BaseModel):
    url: str
    save_to_pipeline: bool = True


@router.post("/evaluate")
async def evaluate_offer(
    body: EvaluateRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Queue an offer evaluation for the given JD URL.
    Adds the URL to pipeline.md so the Claude Code career-ops agent can process it.
    """
    if body.save_to_pipeline:
        await cos.write_pipeline_url(user_id, body.url, "queued_via_dashboard")

    return {
        "status": "queued",
        "url": body.url,
        "message": (
            "Job URL added to your career-ops pipeline. "
            "Open Claude Code in your career-ops workspace to evaluate it, "
            "or run /career-ops pipeline."
        ),
    }


# ─── PDF Generation ───────────────────────────────────────────────────────────


@router.post("/pdf/{app_id}")
async def generate_pdf(
    app_id: str,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate an ATS-optimised CV PDF for an application via generate-pdf.mjs.
    The PDF is saved to the user's output/ directory and the path is persisted to DB.
    """
    app = await db.scalar(
        select(Application).where(
            Application.id == app_id,
            Application.user_id == user_id,
        )
    )
    if not app:
        raise HTTPException(404, "Application not found")

    udir = cos.user_dir(user_id)
    report_slug = f"{app.company.lower().replace(' ', '-')}"

    async def _gen():
        result = await cos.run_script(
            user_id,
            "generate-pdf.mjs",
            args=["--company", app.company, "--role", app.title],
            timeout=120,
        )
        if result["returncode"] == 0:
            # Find the generated PDF
            output_dir = udir / "output"
            pdfs = sorted(output_dir.glob(f"*{report_slug}*.pdf"), key=lambda p: p.stat().st_mtime)
            if pdfs:
                pdf_path = str(pdfs[-1].relative_to(udir))
                app.career_ops_pdf_path = pdf_path
                await db.flush()
                log.info("PDF generated", user_id=user_id, app_id=app_id, path=pdf_path)

    background_tasks.add_task(_gen)
    return {"status": "pdf_generation_started", "app_id": app_id}


# ─── Pattern Analysis ─────────────────────────────────────────────────────────


@router.get("/patterns")
async def get_patterns(
    user_id: str = Depends(get_current_user),
):
    """Run analyze-patterns.mjs and return the JSON result."""
    result = await cos.run_script(user_id, "analyze-patterns.mjs", timeout=60)
    if result["returncode"] != 0:
        raise HTTPException(500, f"Pattern analysis failed: {result['stderr'][:300]}")
    return result["json"] or {"error": "No JSON output from analysis script"}


# ─── Follow-Up Cadence ────────────────────────────────────────────────────────


@router.get("/followups")
async def get_followups(
    user_id: str = Depends(get_current_user),
):
    """Run followup-cadence.mjs and return due follow-ups."""
    result = await cos.run_script(user_id, "followup-cadence.mjs", timeout=60)
    if result["returncode"] != 0:
        raise HTTPException(500, f"Follow-up analysis failed: {result['stderr'][:300]}")
    return result["json"] or {"followups": []}


# ─── Interview Prep ───────────────────────────────────────────────────────────


@router.get("/interview/{company_slug}")
async def get_interview_prep(
    company_slug: str,
    user_id: str = Depends(get_current_user),
):
    """Return the interview-prep markdown file for a specific company."""
    content = await cos.get_interview_prep(user_id, company_slug)
    if content is None:
        raise HTTPException(404, f"No interview prep found for '{company_slug}'")
    return {"company": company_slug, "content": content}


# ─── Tracker Sync ─────────────────────────────────────────────────────────────


@router.post("/sync")
async def sync_tracker(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Force-sync the user's career-ops applications.md tracker → PostgreSQL."""
    upserted = await cos.sync_tracker_to_db(user_id, db)
    return {"status": "synced", "rows_upserted": upserted}


# ─── Profile ──────────────────────────────────────────────────────────────────


@router.get("/profile")
async def get_profile(
    user_id: str = Depends(get_current_user),
):
    """Return the user's career-ops profile.yml as JSON."""
    profile_path = cos.user_dir(user_id) / "config" / "profile.yml"
    if not profile_path.exists():
        raise HTTPException(404, "Profile not set up yet. Call POST /api/career-ops/profile first.")
    with open(profile_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data


class ProfileUpdateRequest(BaseModel):
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    headline: str | None = None
    job_titles: list[str] | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    work_type: list[str] | None = None


@router.put("/profile", status_code=200)
async def update_profile(
    body: ProfileUpdateRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Regenerate the user's profile.yml from provided fields merged with DB data."""
    user_data = await _build_user_data(user_id, db)
    # Merge request overrides
    if body.full_name is not None:
        user_data["full_name"] = body.full_name
    if body.email is not None:
        user_data["email"] = body.email
    if body.phone is not None:
        user_data["phone"] = body.phone
    if body.location is not None:
        user_data["location"] = body.location
    if body.headline is not None:
        user_data["headline"] = body.headline
    if body.job_titles is not None:
        user_data["job_titles"] = body.job_titles
    if body.salary_min is not None:
        user_data["salary_min"] = body.salary_min
    if body.salary_max is not None:
        user_data["salary_max"] = body.salary_max
    if body.work_type is not None:
        user_data["work_type"] = body.work_type

    path = await cos.generate_profile_yml(user_id, user_data)
    return {"status": "updated", "profile_path": str(path)}
