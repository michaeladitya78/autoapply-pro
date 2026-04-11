"""Outreach contact and email sequence models."""
import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Text, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class OutreachContact(Base):
    __tablename__ = "outreach_contacts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=True)
    email: Mapped[str] = mapped_column(String, nullable=False)
    company: Mapped[str] = mapped_column(String, nullable=True)
    title: Mapped[str] = mapped_column(String, nullable=True)
    linkedin_url: Mapped[str] = mapped_column(String, nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    found_via: Mapped[str] = mapped_column(String, nullable=True)  # hunter | apollo | manual
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class EmailSequence(Base):
    __tablename__ = "email_sequences"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    contact_id: Mapped[str] = mapped_column(String, nullable=False)
    application_id: Mapped[str] = mapped_column(String, nullable=True)
    # Types: initial_outreach | follow_up_3d | follow_up_7d | follow_up_14d
    sequence_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending")  # pending | sent | replied | bounced | opted_out
    subject: Mapped[str] = mapped_column(String, nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=True)  # Claude-generated draft
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    replied_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    tracking_pixel_id: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
