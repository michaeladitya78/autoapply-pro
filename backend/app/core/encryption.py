"""AES-256-GCM encryption utilities for session data and credentials."""
import base64
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from app.core.config import settings


def _get_key() -> bytes:
    """Always returns a 32-byte key."""
    return settings.aes_key_bytes


def encrypt(plaintext: str) -> str:
    """Encrypt a string with AES-256-GCM. Returns base64-encoded ciphertext."""
    nonce = os.urandom(12)
    aesgcm = AESGCM(_get_key())
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return base64.b64encode(nonce + ciphertext).decode()


def decrypt(encoded: str) -> str:
    """Decrypt an AES-256-GCM encrypted base64 string."""
    raw = base64.b64decode(encoded)
    nonce, ciphertext = raw[:12], raw[12:]
    aesgcm = AESGCM(_get_key())
    return aesgcm.decrypt(nonce, ciphertext, None).decode()
