"""Connected Account and platform session models."""
import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class ConnectedAccount(Base):
    __tablename__ = "connected_accounts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    platform: Mapped[str] = mapped_column(String, nullable=False)
    # status: active | expired | needs_attention | suspended | captcha | 2fa
    status: Mapped[str] = mapped_column(String, default="active")
    # Method: browser_profile | vault_credential | oauth
    auth_method: Mapped[str] = mapped_column(String, default="browser_profile")
    # Vault reference path — never store actual credentials here
    vault_ref: Mapped[str] = mapped_column(String, nullable=True)
    # AES-encrypted serialized browser cookies/session (lightweight)
    session_encrypted: Mapped[str] = mapped_column(Text, nullable=True)
    # Path to persistent Chromium profile directory
    profile_path: Mapped[str] = mapped_column(String, nullable=True)
    # OAuth access/refresh token (encrypted) for supported platforms
    oauth_token_encrypted: Mapped[str] = mapped_column(Text, nullable=True)
    proxy_assigned: Mapped[str] = mapped_column(String, nullable=True)  # IP:port assignment
    last_verified: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    applications_today: Mapped[int] = mapped_column(String, default="0")
    connected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    notes: Mapped[dict] = mapped_column(JSON, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="accounts")
