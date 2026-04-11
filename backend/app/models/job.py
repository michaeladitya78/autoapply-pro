"""Job listing and Application models."""
import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Text, Integer, JSON, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    platform: Mapped[str] = mapped_column(String, nullable=False)  # linkedin | indeed | etc.
    external_id: Mapped[str] = mapped_column(String, nullable=True)  # platform job ID
    title: Mapped[str] = mapped_column(String, nullable=False)
    company: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    salary_min: Mapped[int] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[int] = mapped_column(Integer, nullable=True)
    location: Mapped[str] = mapped_column(String, nullable=True)
    work_type: Mapped[str] = mapped_column(String, nullable=True)  # remote | hybrid | onsite
    industry: Mapped[str] = mapped_column(String, nullable=True)
    tech_stack: Mapped[list] = mapped_column(JSON, default=list)
    scraped_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    match_score: Mapped[float] = mapped_column(Float, nullable=True)  # semantic similarity 0-1


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    job_id: Mapped[str] = mapped_column(String, nullable=True)
    platform: Mapped[str] = mapped_column(String, nullable=False)
    company: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    job_url: Mapped[str] = mapped_column(String, nullable=True)
    # Status mirrors career-ops canonical states:
    # applied | viewed | interview | rejected | offer | withdrawn
    # |-> career-ops statuses: Evaluated | Applied | Responded | Interview | Offer | Rejected | Discarded | SKIP
    status: Mapped[str] = mapped_column(String, default="applied")
    applied_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resume_version_id: Mapped[str] = mapped_column(String, nullable=True)
    tailored_resume_content: Mapped[str] = mapped_column(Text, nullable=True)
    cover_letter: Mapped[str] = mapped_column(Text, nullable=True)
    agent_log: Mapped[list] = mapped_column(JSON, default=list)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    # ── career-ops integration fields ──────────────────────────────────────────
    # A-F score from oferta.md evaluation (0.0–5.0 scale)
    career_ops_score: Mapped[float] = mapped_column(Float, nullable=True)
    # Letter grade: A | B | C | D | F
    career_ops_grade: Mapped[str] = mapped_column(String, nullable=True)
    # Relative path to evaluation report markdown (reports/###-company-YYYY-MM-DD.md)
    career_ops_report_path: Mapped[str] = mapped_column(String, nullable=True)
    # Relative path or URL to generated ATS-optimised PDF
    career_ops_pdf_path: Mapped[str] = mapped_column(String, nullable=True)
    # Posting legitimacy tier from Block G in oferta.md (A/B/C/D/F)
    legitimacy_tier: Mapped[str] = mapped_column(String, nullable=True)
    # Sequential 3-digit report number used by career-ops tracker
    career_ops_seq: Mapped[int] = mapped_column(Integer, nullable=True)
    # Source portal / scan origin
    source_portal: Mapped[str] = mapped_column(String, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="applications")
