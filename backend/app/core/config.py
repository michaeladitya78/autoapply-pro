"""Application settings using Pydantic BaseSettings.

Cloud deployment targets:
  - PostgreSQL  → Supabase (DATABASE_URL)
  - Redis       → Upstash  (REDIS_URL, prefix with rediss://)
  - Vector DB   → Supabase pgvector (no separate service needed)
  - Secrets     → Supabase Vault REST (SUPABASE_URL + SUPABASE_SERVICE_KEY)
  - Email       → Resend API (RESEND_API_KEY)
  - Payments    → Stripe (STRIPE_SECRET_KEY)
  - LLM         → Anthropic Claude (ANTHROPIC_API_KEY)
  - Browser     → Playwright headless inside Railway worker
"""
from functools import lru_cache
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Union
import json


class Settings(BaseSettings):
    # ─── App ──────────────────────────────────────────────────────────────────
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "AutoApplyPro2025DevSecretKey32!!"
    AES_ENCRYPTION_KEY: str = "AutoApplyPro2025SecretKey32Bytes"

    # ─── Database (Supabase PostgreSQL) ───────────────────────────────────────
    # Cloud:  postgresql+asyncpg://postgres:[pw]@db.[ref].supabase.co:5432/postgres
    # Local:  postgresql+asyncpg://autoapply:supersecret_autoapply@localhost:5432/autoapply
    DATABASE_URL: str = "postgresql+asyncpg://autoapply:supersecret_autoapply@localhost:5432/autoapply"
    SYNC_DATABASE_URL: str = "postgresql://autoapply:supersecret_autoapply@localhost:5432/autoapply"

    # ─── Redis (Upstash — serverless, TLS) ────────────────────────────────────
    # Cloud:  rediss://default:[token]@[host].upstash.io:6380
    # Local:  redis://:redissecret_autoapply@localhost:6379/0
    REDIS_URL: str = "redis://:redissecret_autoapply@localhost:6379/0"

    # ─── Supabase (replaces ChromaDB + HashiCorp Vault) ───────────────────────
    SUPABASE_URL: str = ""           # https://[ref].supabase.co
    SUPABASE_SERVICE_KEY: str = ""   # Service role key (server-side only, never expose to browser)

    # ─── AI — Claude API only (Ollama removed) ────────────────────────────────
    ANTHROPIC_API_KEY: str = ""

    # ─── Auth (Clerk) ─────────────────────────────────────────────────────────
    CLERK_SECRET_KEY: str = ""
    CLERK_WEBHOOK_SECRET: str = ""

    # ─── Brightdata Web Unlocker API (REST) ───────────────────────────────────
    BRIGHTDATA_API_KEY: str = ""
    BRIGHTDATA_ZONE: str = "web_unlocker1"
    BRIGHTDATA_API_URL: str = "https://api.brightdata.com/request"

    # ─── Email (Resend — replaces aiosmtplib / Gmail SMTP) ───────────────────
    RESEND_API_KEY: str = ""
    RESEND_FROM_EMAIL: str = "agent@autoapplypro.com"

    # ─── Payments (Stripe) ────────────────────────────────────────────────────
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRO_PRICE_ID: str = ""    # price_... from Stripe dashboard
    STRIPE_TEAM_PRICE_ID: str = ""   # price_... from Stripe dashboard

    # ─── Contact Discovery ────────────────────────────────────────────────────
    HUNTER_API_KEY: str = ""
    APOLLO_API_KEY: str = ""

    # ─── Storage (optional S3) ────────────────────────────────────────────────
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_BUCKET_NAME: str = "autoapply-resumes"
    AWS_REGION: str = "us-east-1"

    # ─── CORS — accepts JSON array string or Python list ──────────────────────
    ALLOWED_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "https://autoapplypro.com",
    ]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, ValueError):
                return [o.strip() for o in v.split(",")]
        return v

    @field_validator("AES_ENCRYPTION_KEY", mode="before")
    @classmethod
    def pad_aes_key(cls, v):
        """Ensure AES key is exactly 32 bytes."""
        if isinstance(v, str):
            return v[:32].ljust(32, "0")
        return v

    # ─── Platform daily caps (anti-detection hard limits) ─────────────────────
    LINKEDIN_DAILY_CAP: int = 25
    INDEED_DAILY_CAP: int = 40
    NAUKRI_DAILY_CAP: int = 30

    # ─── Browser profile storage ──────────────────────────────────────────────
    # In production (Railway), sessions are stored in Supabase, not local disk.
    # This path is only used as a temporary scratch dir during a single run.
    BROWSER_PROFILES_PATH: str = "/tmp/browser_profiles"

    # ─── Computed properties ──────────────────────────────────────────────────

    @property
    def brightdata_configured(self) -> bool:
        """True if Brightdata Web Unlocker API key is set."""
        return bool(self.BRIGHTDATA_API_KEY)

    # Keep legacy alias for any code that still checks proxy_configured
    @property
    def proxy_configured(self) -> bool:
        return self.brightdata_configured

    @property
    def aes_key_bytes(self) -> bytes:
        """Return AES key as 32-byte value."""
        return self.AES_ENCRYPTION_KEY.encode()[:32].ljust(32, b"0")

    @property
    def supabase_configured(self) -> bool:
        """True if Supabase URL + service key are both set."""
        return bool(self.SUPABASE_URL and self.SUPABASE_SERVICE_KEY)

    @property
    def stripe_configured(self) -> bool:
        return bool(self.STRIPE_SECRET_KEY)

    @property
    def resend_configured(self) -> bool:
        return bool(self.RESEND_API_KEY)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
