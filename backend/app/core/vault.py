"""HashiCorp Vault integration — raw credential storage only."""
import hvac
import structlog
from app.core.config import settings

log = structlog.get_logger()


def _get_client() -> hvac.Client:
    client = hvac.Client(url=settings.VAULT_ADDR, token=settings.VAULT_TOKEN)
    assert client.is_authenticated(), "Vault authentication failed"
    return client


def store_credential(user_id: str, platform: str, username: str, password: str) -> str:
    """Store raw credentials in Vault. Returns vault path reference."""
    client = _get_client()
    path = f"secret/autoapply/{user_id}/{platform}"
    client.secrets.kv.v2.create_or_update_secret(
        path=path,
        secret={"username": username, "password": password},
    )
    log.info("Credential stored in Vault", user_id=user_id, platform=platform)
    return path


def retrieve_credential(vault_ref: str) -> dict:
    """Fetch credentials from Vault. Returns dict with username/password."""
    client = _get_client()
    result = client.secrets.kv.v2.read_secret_version(path=vault_ref)
    return result["data"]["data"]


def delete_credential(vault_ref: str) -> None:
    """Permanently destroy credentials from Vault."""
    client = _get_client()
    client.secrets.kv.v2.delete_metadata_and_all_versions(path=vault_ref)
    log.info("Credential destroyed from Vault", path=vault_ref)


def store_session_data(user_id: str, platform: str, session_json: str) -> str:
    """Store encrypted browser session in Vault."""
    client = _get_client()
    path = f"secret/autoapply/sessions/{user_id}/{platform}"
    client.secrets.kv.v2.create_or_update_secret(
        path=path,
        secret={"session": session_json},
    )
    return path


def retrieve_session_data(vault_ref: str) -> str:
    """Retrieve browser session JSON from Vault."""
    client = _get_client()
    result = client.secrets.kv.v2.read_secret_version(path=vault_ref)
    return result["data"]["data"]["session"]
