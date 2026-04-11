"""
Career-Ops Service Bridge
=========================
Bridges the AutoApply Pro Python backend with the career-ops Node.js script layer.

Responsibilities:
  - Generate per-user config/profile.yml from the DB user record
  - Run career-ops .mjs scripts as async subprocesses
  - Parse data/applications.md ↔ sync to/from PostgreSQL
  - Provide typed result objects for all script outputs
"""
import asyncio
import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog
import yaml

log = structlog.get_logger(__name__)

# ─── Paths ────────────────────────────────────────────────────────────────────
# career-ops repo lives at d:\jobautomation\career-ops
CAREER_OPS_ROOT = Path(__file__).parents[3] / "career-ops"
# Per-user data lives at career-ops/users/{user_id}/
USERS_ROOT = CAREER_OPS_ROOT / "users"


def user_dir(user_id: str) -> Path:
    """Return (and create) the per-user career-ops directory."""
    d = USERS_ROOT / user_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "config").mkdir(exist_ok=True)
    (d / "data").mkdir(exist_ok=True)
    (d / "output").mkdir(exist_ok=True)
    (d / "reports").mkdir(exist_ok=True)
    (d / "jds").mkdir(exist_ok=True)
    (d / "interview-prep").mkdir(exist_ok=True)
    (d / "batch" / "tracker-additions").mkdir(parents=True, exist_ok=True)
    return d


def _ensure_static_links(uid: str) -> None:
    """Symlink (or copy) shared read-only assets into the user dir."""
    udir = user_dir(uid)
    shared_assets = [
        "modes",
        "templates",
        "fonts",
        "batch",
        "scan.mjs",
        "generate-pdf.mjs",
        "analyze-patterns.mjs",
        "followup-cadence.mjs",
        "merge-tracker.mjs",
        "dedup-tracker.mjs",
        "normalize-statuses.mjs",
        "verify-pipeline.mjs",
        "package.json",
        "node_modules",
    ]
    for asset in shared_assets:
        src = CAREER_OPS_ROOT / asset
        dst = udir / asset
        if src.exists() and not dst.exists():
            if src.is_dir():
                # Use a junction on Windows (no admin needed)
                try:
                    os.symlink(str(src), str(dst), target_is_directory=True)
                except (OSError, NotImplementedError):
                    # Junction fallback via mklink
                    os.system(f'mklink /J "{dst}" "{src}"')
            else:
                dst.symlink_to(src)


# ─── Profile YAML Generation ──────────────────────────────────────────────────

async def generate_profile_yml(user_id: str, user_data: dict) -> Path:
    """
    Write career-ops config/profile.yml for a user from their SaaS profile dict.

    `user_data` shape (all optional except full_name/email):
    {
        "full_name": str,
        "email": str,
        "phone": str,
        "location": str,
        "linkedin": str,
        "portfolio_url": str,
        "github": str,
        "job_titles": list[str],       # from UserPreferences
        "salary_min": int,
        "salary_max": int,
        "locations": list[str],
        "work_type": list[str],
        "headline": str,
    }
    """
    _ensure_static_links(user_id)
    udir = user_dir(user_id)
    profile_path = udir / "config" / "profile.yml"

    salary_min = user_data.get("salary_min", 0)
    salary_max = user_data.get("salary_max", 0)
    target_range = (
        f"${salary_min:,}-{salary_max:,}" if salary_min and salary_max else "Not specified"
    )

    profile = {
        "candidate": {
            "full_name": user_data.get("full_name", ""),
            "email": user_data.get("email", ""),
            "phone": user_data.get("phone", ""),
            "location": user_data.get("location", ""),
            "linkedin": user_data.get("linkedin", ""),
            "portfolio_url": user_data.get("portfolio_url", ""),
            "github": user_data.get("github", ""),
        },
        "target_roles": {
            "primary": user_data.get("job_titles", []),
            "archetypes": [
                {"name": t, "level": "Senior", "fit": "primary"}
                for t in user_data.get("job_titles", [])[:3]
            ],
        },
        "narrative": {
            "headline": user_data.get("headline", ""),
            "exit_story": "",
            "superpowers": [],
            "proof_points": [],
        },
        "compensation": {
            "target_range": target_range,
            "currency": "USD",
            "minimum": f"${salary_min:,}" if salary_min else "Not specified",
            "location_flexibility": ", ".join(user_data.get("work_type", [])),
        },
        "location": {
            "country": "",
            "city": user_data.get("location", ""),
            "timezone": "",
            "visa_status": "",
        },
        # AutoApply Pro integration metadata
        "autoapply": {
            "user_id": user_id,
            "synced_at": datetime.utcnow().isoformat(),
        },
    }

    with open(profile_path, "w", encoding="utf-8") as f:
        yaml.dump(profile, f, default_flow_style=False, allow_unicode=True)

    log.info("career-ops profile.yml written", user_id=user_id, path=str(profile_path))
    return profile_path


# ─── Script Runner ────────────────────────────────────────────────────────────

async def run_script(
    user_id: str,
    script: str,
    args: list[str] | None = None,
    timeout: int = 120,
) -> dict[str, Any]:
    """
    Run a career-ops .mjs script as a subprocess inside the user's directory.
    Returns {"stdout": str, "stderr": str, "returncode": int, "json": Any|None}.
    """
    udir = user_dir(user_id)
    _ensure_static_links(user_id)

    cmd = ["node", script] + (args or [])
    log.info("Running career-ops script", user_id=user_id, cmd=cmd, cwd=str(udir))

    try:
        proc = await asyncio.wait_for(
            asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(udir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, "CAREER_OPS_USER_ID": user_id},
            ),
            timeout=timeout,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        log.warning("career-ops script timed out", user_id=user_id, script=script)
        return {"stdout": "", "stderr": "timeout", "returncode": -1, "json": None}

    stdout_str = stdout.decode("utf-8", errors="replace").strip()
    stderr_str = stderr.decode("utf-8", errors="replace").strip()

    parsed_json = None
    try:
        parsed_json = json.loads(stdout_str)
    except (json.JSONDecodeError, ValueError):
        pass

    result = {
        "stdout": stdout_str,
        "stderr": stderr_str,
        "returncode": proc.returncode,
        "json": parsed_json,
    }

    if proc.returncode != 0:
        log.warning(
            "career-ops script failed",
            user_id=user_id,
            script=script,
            stderr=stderr_str[:500],
        )

    return result


# ─── Tracker Sync: applications.md → PostgreSQL ───────────────────────────────

# Maps career-ops canonical statuses → AutoApply Pro status strings
_STATUS_MAP = {
    "Evaluated": "applied",
    "Applied": "applied",
    "Responded": "viewed",
    "Interview": "interview",
    "Offer": "offer",
    "Rejected": "rejected",
    "Discarded": "withdrawn",
    "SKIP": "withdrawn",
}

_SCORE_TO_GRADE = {
    (4.5, 5.0): "A",
    (4.0, 4.5): "B",
    (3.0, 4.0): "C",
    (2.0, 3.0): "D",
    (0.0, 2.0): "F",
}


def _score_to_grade(score: float | None) -> str | None:
    if score is None:
        return None
    for (lo, hi), grade in _SCORE_TO_GRADE.items():
        if lo <= score <= hi:
            return grade
    return None


def _parse_applications_md(tracker_path: Path) -> list[dict]:
    """
    Parse career-ops applications.md table into a list of dicts.
    Table columns: # | Date | Company | Role | Score | Status | PDF | Report | Notes
    """
    if not tracker_path.exists():
        return []

    rows = []
    inside_table = False

    with open(tracker_path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip()
            if line.startswith("|") and "---|" in line:
                inside_table = True
                continue
            if inside_table and line.startswith("|"):
                cols = [c.strip() for c in line.split("|")[1:-1]]
                if len(cols) < 8:
                    continue
                try:
                    seq_str = cols[0].strip("#").strip()
                    seq = int(seq_str) if seq_str.isdigit() else None
                    date_str = cols[1]
                    company = cols[2]
                    role = cols[3]
                    score_str = cols[4].replace("/5", "").strip()
                    score = float(score_str) if score_str and score_str != "—" else None
                    status_raw = cols[5].replace("**", "").strip()
                    status = _STATUS_MAP.get(status_raw, "applied")
                    report_raw = cols[7]  # [###](reports/...)
                    report_match = re.search(r"\(([^)]+)\)", report_raw)
                    report_path = report_match.group(1) if report_match else None
                    notes = cols[8] if len(cols) > 8 else ""

                    rows.append(
                        {
                            "career_ops_seq": seq,
                            "applied_at": date_str,
                            "company": company,
                            "title": role,
                            "career_ops_score": score,
                            "career_ops_grade": _score_to_grade(score),
                            "status": status,
                            "career_ops_report_path": report_path,
                            "notes": notes,
                        }
                    )
                except (ValueError, IndexError) as exc:
                    log.debug("Skipping malformed tracker row", exc=str(exc), line=line)
            elif inside_table and not line.startswith("|"):
                inside_table = False

    return rows


async def sync_tracker_to_db(user_id: str, db_session) -> int:
    """
    Parse this user's applications.md and upsert into the PostgreSQL applications table.
    Returns number of rows upserted.
    """
    from sqlalchemy import select
    from app.models.job import Application

    tracker_path = user_dir(user_id) / "data" / "applications.md"
    rows = _parse_applications_md(tracker_path)
    upserted = 0

    for row in rows:
        seq = row.get("career_ops_seq")
        company = row.get("company", "")
        title = row.get("title", "")
        if not company or not title:
            continue

        # Find existing application by seq number or company+role
        existing = None
        if seq:
            existing = await db_session.scalar(
                select(Application).where(
                    Application.user_id == user_id,
                    Application.career_ops_seq == seq,
                )
            )
        if not existing:
            existing = await db_session.scalar(
                select(Application).where(
                    Application.user_id == user_id,
                    Application.company == company,
                    Application.title == title,
                )
            )

        if existing:
            existing.status = row.get("status", existing.status)
            existing.career_ops_score = row.get("career_ops_score")
            existing.career_ops_grade = row.get("career_ops_grade")
            existing.career_ops_report_path = row.get("career_ops_report_path")
            existing.notes = row.get("notes", existing.notes)
        else:
            app = Application(
                user_id=user_id,
                platform="career-ops",
                company=company,
                title=title,
                status=row.get("status", "applied"),
                career_ops_seq=seq,
                career_ops_score=row.get("career_ops_score"),
                career_ops_grade=row.get("career_ops_grade"),
                career_ops_report_path=row.get("career_ops_report_path"),
                notes=row.get("notes", ""),
            )
            db_session.add(app)
        upserted += 1

    await db_session.flush()
    log.info("career-ops tracker synced to DB", user_id=user_id, rows=upserted)
    return upserted


async def write_pipeline_url(user_id: str, url: str, note: str = "") -> None:
    """Append a job URL to this user's data/pipeline.md inbox."""
    pipeline_path = user_dir(user_id) / "data" / "pipeline.md"
    if not pipeline_path.exists():
        pipeline_path.write_text(
            "# Pipeline — Pending URLs\n\n"
            "<!-- Add job URLs below. One per line. -->\n\n",
            encoding="utf-8",
        )
    with open(pipeline_path, "a", encoding="utf-8") as f:
        entry = f"- {url}"
        if note:
            entry += f"  <!-- {note} -->"
        f.write(entry + "\n")
    log.info("URL added to pipeline", user_id=user_id, url=url)


async def read_pipeline_urls(user_id: str) -> list[str]:
    """Read pending URLs from this user's data/pipeline.md."""
    pipeline_path = user_dir(user_id) / "data" / "pipeline.md"
    if not pipeline_path.exists():
        return []
    urls = []
    with open(pipeline_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("- http"):
                url = line[2:].split("  ")[0].strip()
                urls.append(url)
    return urls


async def get_interview_prep(user_id: str, company: str) -> str | None:
    """Read interview prep markdown for a specific company."""
    udir = user_dir(user_id) / "interview-prep"
    slug = company.lower().replace(" ", "-")
    # Look for any file matching {company}*.md
    for f in udir.glob(f"{slug}*.md"):
        return f.read_text(encoding="utf-8")
    return None
