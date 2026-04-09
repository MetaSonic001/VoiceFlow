"""
AES-256-GCM credential encryption — Patent Claim 9.
Encrypts sensitive credentials (Twilio tokens, API keys) at rest.
Uses a 32-byte key from CREDENTIALS_ENCRYPTION_KEY env var.
"""
import os
import base64
import logging

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import settings

logger = logging.getLogger("voiceflow.credentials")

_KEY_BYTES: bytes | None = None


def _get_key() -> bytes:
    """Derive 32-byte AES key from hex env var, or generate a deterministic demo key."""
    global _KEY_BYTES
    if _KEY_BYTES is not None:
        return _KEY_BYTES

    raw = settings.CREDENTIALS_ENCRYPTION_KEY
    if raw and len(raw) >= 64:
        _KEY_BYTES = bytes.fromhex(raw[:64])
    else:
        # Deterministic fallback for development — NOT for production
        logger.warning("CREDENTIALS_ENCRYPTION_KEY not set; using dev-only fallback key")
        _KEY_BYTES = b"vf-dev-key-not-for-production"[:32].ljust(32, b"\x00")
    return _KEY_BYTES


def encrypt(plaintext: str) -> str:
    """Encrypt a string → base64-encoded 'nonce:ciphertext'."""
    if not plaintext:
        return ""
    key = _get_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # 96-bit nonce
    ct = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    combined = nonce + ct
    return base64.urlsafe_b64encode(combined).decode("ascii")


def decrypt(token: str) -> str:
    """Decrypt a base64-encoded 'nonce+ciphertext' back to plaintext."""
    if not token:
        return ""
    key = _get_key()
    aesgcm = AESGCM(key)
    combined = base64.urlsafe_b64decode(token)
    nonce = combined[:12]
    ct = combined[12:]
    return aesgcm.decrypt(nonce, ct, None).decode("utf-8")


def encrypt_if_needed(value: str) -> str:
    """Encrypt only if the value doesn't look already encrypted (base64 blob)."""
    if not value:
        return ""
    # Already encrypted values start with base64 URL-safe chars and are long
    if len(value) > 50 and not value.startswith("gsk_") and not value.startswith("AC"):
        try:
            decrypt(value)
            return value  # Already encrypted and decryptable
        except Exception:
            pass
    return encrypt(value)


def decrypt_safe(token: str) -> str:
    """Decrypt, returning empty string on failure instead of raising."""
    try:
        return decrypt(token)
    except Exception:
        # Might be a plaintext value from before encryption was added
        return token


def mask(value: str, prefix_len: int = 4, suffix_len: int = 4) -> str:
    """Return a masked version like 'gsk_••••••ab12'."""
    if not value or len(value) < prefix_len + suffix_len + 4:
        return "••••••••"
    return value[:prefix_len] + "••••••••" + value[-suffix_len:]
