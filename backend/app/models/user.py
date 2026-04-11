"""User and preferences SQLAlchemy models."""
import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Integer, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # Clerk user ID
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=True)
    plan: Mapped[str] = mapped_column(String, default="free")  # free | pro | team | enterprise
    stripe_customer_id: Mapped[str] = mapped_column(String, nullable=True)
    onboarding_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    agent_active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    preferences: Mapped["UserPreferences"] = relationship("UserPreferences", back_populates="user", uselist=False)
    resumes: Mapped[list["Resume"]] = relationship("Resume", back_populates="user")
    accounts: Mapped[list["ConnectedAccount"]] = relationship("ConnectedAccount", back_populates="user")
    applications: Mapped[list["Application"]] = relationship("Application", back_populates="user")


class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    job_titles: Mapped[list] = mapped_column(JSON, default=list)
    locations: Mapped[list] = mapped_column(JSON, default=list)
    salary_min: Mapped[int] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[int] = mapped_column(Integer, nullable=True)
    work_type: Mapped[list] = mapped_column(JSON, default=list)  # ["remote", "hybrid", "onsite"]
    tech_stack: Mapped[list] = mapped_column(JSON, default=list)
    industries: Mapped[list] = mapped_column(JSON, default=list)
    daily_application_limit: Mapped[int] = mapped_column(Integer, default=20)
    daily_email_limit: Mapped[int] = mapped_column(Integer, default=10)
    linkedin_url: Mapped[str] = mapped_column(String, nullable=True)
    portfolio_url: Mapped[str] = mapped_column(String, nullable=True)
    years_of_experience: Mapped[int] = mapped_column(Integer, nullable=True)
    exclude_companies: Mapped[list] = mapped_column(JSON, default=list)
    tos_agreed: Mapped[bool] = mapped_column(Boolean, default=False)
    tos_agreed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="preferences")


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    file_url: Mapped[str] = mapped_column(String, nullable=False)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    parsed_content: Mapped[str] = mapped_column(Text, nullable=True)  # raw extracted text
    structured_data: Mapped[dict] = mapped_column(JSON, nullable=True)  # Claude-parsed JSON
    chroma_doc_id: Mapped[str] = mapped_column(String, nullable=True)  # embedding reference
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="resumes")
