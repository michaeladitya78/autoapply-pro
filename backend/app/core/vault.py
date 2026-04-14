"""
Supabase Secret Store — replaces HashiCorp Vault.

Credentials and browser session tokens are stored in Supabase using the
built-in `vault.secrets` table (Supabase Vault extension) via the REST API.

The Supabase Vault extension encrypts values at rest using a per-project
data-encryption key managed by Supabase. No self-managed HSM or Vault
instance is required.

When Supabase is not configured (local dev), falls back to AES-encrypted
storage in a simple in-memory dict so tests can run without any external deps.

API used:
  POST /rest/v1/vault/secrets        — create/update
  GET  /rest/v1/vault/secrets        — query by name
  DELETE /rest/v1/vault/secrets      — delete
"""
from __future__ import annotations

import json
from typing import Optional
import httpx
import structlog

from app.core.config import settings
from app.core.encryption import encrypt, decrypt

log = structlog.get_logger()

# ─── Fallback in-memory store (local dev only) ─────────────────────────────────
_LOCAL_STORE: dict[str, str] = {}


def _headers() -> dict:
    return {
        "apikey": settings.SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
    }


def _vault_url() -> str:
    return f"{settings.SUPABASE_URL}/rest/v1/vault/secrets"


def _secret_name(user_id: str, platform: str, kind: str = "credential") -> str:
    return f"autoapply_{kind}_{user_id}_{platform}"


# ─── Public API ────────────────────────────────────────────────────────────────


def store_credential(user_id: str, platform: str, username: str, password: str) -> str:
    """
    Encrypt and store platform credentials.
    Returns the secret name (used as a stable reference ID).
    """
    name = _secret_name(user_id, platform, "credential")
    payload = json.dumps({"username": username, "password": password})
    encrypted = encrypt(payload)

    if settings.supabase_configured:
        _upsert_vault_secret(name, encrypted)
    else:
        _LOCAL_STORE[name] = encrypted
        log.warning("Supabase not configured — credential stored in-memory (dev only)", name=name)

    log.info("Credential stored", user_id=user_id, platform=platform)
    return name


def retrieve_credential(vault_ref: str) -> dict:
    """Retrieve and decrypt platform credentials. vault_ref is the secret name."""
    if settings.supabase_configured:
        encrypted = _fetch_vault_secret(vault_ref)
    else:
        encrypted = _LOCAL_STORE.get(vault_ref, "")

    if not encrypted:
        raise KeyError(f"Secret not found: {vault_ref}")

    payload = decrypt(encrypted)
    return json.loads(payload)


def delete_credential(vault_ref: str) -> None:
    """Permanently delete credentials."""
    if settings.supabase_configured:
        _delete_vault_secret(vault_ref)
    else:
        _LOCAL_STORE.pop(vault_ref, None)
    log.info("Credential deleted", ref=vault_ref)


def store_session_data(user_id: str, platform: str, session_json: str) -> str:
    """Encrypt and store browser session state."""
    name = _secret_name(user_id, platform, "session")
    encrypted = encrypt(session_json)

    if settings.supabase_configured:
        _upsert_vault_secret(name, encrypted)
    else:
        _LOCAL_STORE[name] = encrypted

    log.info("Session stored", user_id=user_id, platform=platform)
    return name


def retrieve_session_data(vault_ref: str) -> str:
    """Retrieve and decrypt browser session state."""
    if settings.supabase_configured:
        encrypted = _fetch_vault_secret(vault_ref)
    else:
        encrypted = _LOCAL_STORE.get(vault_ref, "")

    if not encrypted:
        return ""
    return decrypt(encrypted)


# ─── Supabase Vault REST helpers ───────────────────────────────────────────────


def _upsert_vault_secret(name: str, value: str) -> None:
    """Create or overwrite a secret in Supabase Vault."""
    # Supabase Vault upsert: first try to update, then insert
    with httpx.Client(timeout=10) as client:
        # Check if exists
        resp = client.get(
            _vault_url(),
            headers=_headers(),
            params={"name": f"eq.{name}", "select": "id"},
        )
        existing = resp.json()

        if existing:
            # Update existing
            secret_id = existing[0]["id"]
            client.patch(
                f"{_vault_url()}?id=eq.{secret_id}",
                headers=_headers(),
                json={"secret": value},
            )
        else:
            # Insert new
            client.post(
                _vault_url(),
                headers=_headers(),
                json={"name": name, "secret": value},
            ).raise_for_status()


def _fetch_vault_secret(name: str) -> Optional[str]:
    """Retrieve a secret value from Supabase Vault by name."""
    with httpx.Client(timeout=10) as client:
        resp = client.get(
            _vault_url(),
            headers=_headers(),
            params={"name": f"eq.{name}", "select": "decrypted_secret"},
        )
        data = resp.json()
        if data:
            return data[0].get("decrypted_secret", "")
        return None


def _delete_vault_secret(name: str) -> None:
    """Delete a secret from Supabase Vault by name."""
    with httpx.Client(timeout=10) as client:
        client.delete(
            _vault_url(),
            headers=_headers(),
            params={"name": f"eq.{name}"},
        )
