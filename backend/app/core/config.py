"""Application settings using Pydantic BaseSettings."""
from functools import lru_cache
from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Union
import json
import os


class Settings(BaseSettings):
    # App
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "AutoApplyPro2025DevSecretKey32!!"
    AES_ENCRYPTION_KEY: str = "AutoApplyPro2025SecretKey32Bytes"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://autoapply:supersecret_autoapply@localhost:5432/autoapply"
    SYNC_DATABASE_URL: str = "postgresql://autoapply:supersecret_autoapply@localhost:5432/autoapply"

    # Redis
    REDIS_URL: str = "redis://:redissecret_autoapply@localhost:6379/0"

    # ChromaDB
    CHROMA_HOST: str = "http://localhost:8000"

    # HashiCorp Vault
    VAULT_ADDR: str = "http://localhost:8200"
    VAULT_TOKEN: str = "myroot"

    # AI
    ANTHROPIC_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # Auth (Clerk)
    CLERK_SECRET_KEY: str = ""
    CLERK_WEBHOOK_SECRET: str = ""

    # Proxy (Brightdata) — optional, leave blank to skip proxy
    BRIGHTDATA_USERNAME: str = ""
    BRIGHTDATA_PASSWORD: str = ""
    BRIGHTDATA_HOST: str = "brd.superproxy.io"
    BRIGHTDATA_PORT: int = 22225

    # Email
    GMAIL_CLIENT_ID: str = ""
    GMAIL_CLIENT_SECRET: str = ""
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587

    # Contact Discovery
    HUNTER_API_KEY: str = ""
    APOLLO_API_KEY: str = ""

    # Storage (optional S3)
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_BUCKET_NAME: str = "autoapply-resumes"
    AWS_REGION: str = "us-east-1"

    # CORS — accepts JSON array string or Python list
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

    # Platform daily caps (anti-detection hard limits)
    LINKEDIN_DAILY_CAP: int = 25
    INDEED_DAILY_CAP: int = 40
    NAUKRI_DAILY_CAP: int = 30

    # Browser profile storage path (local dev uses relative path)
    BROWSER_PROFILES_PATH: str = "./browser_profiles"

    @property
    def proxy_configured(self) -> bool:
        """True if Brightdata credentials are set."""
        return bool(self.BRIGHTDATA_USERNAME and self.BRIGHTDATA_PASSWORD)

    @property
    def aes_key_bytes(self) -> bytes:
        """Return AES key as 32-byte value."""
        return self.AES_ENCRYPTION_KEY.encode()[:32].ljust(32, b"0")

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
