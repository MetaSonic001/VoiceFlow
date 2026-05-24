"""
AES-256-GCM credential encryption — Patent Claim 9.
Encrypts sensitive credentials (Twilio tokens, API keys) at rest.
Uses a 32-byte key from CREDENTIALS_ENCRYPTION_KEY env var.

Platform Key Fallback
---------------------
For managed-plan tenants, VoiceFlow uses its own platform API keys instead of
requiring the customer to supply them. get_api_key() implements the lookup order:

  1. Tenant's own encrypted key in tenant.settings (BYOK)
  2. Platform key from environment variable (managed fallback)
  3. Returns None if neither is set

Provider key names in tenant.settings and their env-var counterparts:
  groqApiKey          → PLATFORM_GROQ_KEY
  sarvamApiKey        → PLATFORM_SARVAM_KEY
  openaiApiKey        → PLATFORM_OPENAI_KEY
  geminiApiKey        → PLATFORM_GEMINI_KEY
  twilioAccountSid    → PLATFORM_TWILIO_SID
  twilioAuthToken     → PLATFORM_TWILIO_TOKEN
  exotelApiKey        → PLATFORM_EXOTEL_KEY
  exotelApiToken      → PLATFORM_EXOTEL_TOKEN
"""
import os
import base64
import logging
from typing import Optional, TYPE_CHECKING

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import settings

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

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


# ── Platform key registry ─────────────────────────────────────────────────────
# Maps (provider_key_name_in_tenant_settings) → env var name
_PLATFORM_KEY_ENV_MAP: dict[str, str] = {
    "groqApiKey":       "PLATFORM_GROQ_KEY",
    "sarvamApiKey":     "PLATFORM_SARVAM_KEY",
    "openaiApiKey":     "PLATFORM_OPENAI_KEY",
    "geminiApiKey":     "PLATFORM_GEMINI_KEY",
    "twilioAccountSid": "PLATFORM_TWILIO_SID",
    "twilioAuthToken":  "PLATFORM_TWILIO_TOKEN",
    "exotelApiKey":     "PLATFORM_EXOTEL_KEY",
    "exotelApiToken":   "PLATFORM_EXOTEL_TOKEN",
}


def get_platform_key(provider_key: str) -> Optional[str]:
    """
    Return VoiceFlow's own platform API key for `provider_key`, or None.
    These are used for managed-plan tenants who don't supply their own keys.
    """
    env_var = _PLATFORM_KEY_ENV_MAP.get(provider_key)
    if not env_var:
        return None
    return os.getenv(env_var) or None


async def get_api_key(
    tenant_settings: dict,
    provider_key: str,
    plan_type: str = "byok",
) -> Optional[str]:
    """
    Resolve an API key for a tenant with BYOK-first, platform-fallback logic.

    Args:
        tenant_settings: The tenant.settings dict (may contain encrypted keys).
        provider_key:    Key name as stored in tenant.settings (e.g. "groqApiKey").
        plan_type:       "byok" | "managed" | "free".

    Returns the plaintext key, or None if unavailable.
    """
    # 1. Check tenant's own BYOK key first (regardless of plan type)
    raw = (tenant_settings or {}).get(provider_key, "")
    if raw:
        decrypted = decrypt_safe(raw)
        if decrypted:
            return decrypted

    # 2. For managed-plan tenants, fall back to platform key
    if plan_type == "managed":
        platform = get_platform_key(provider_key)
        if platform:
            return platform

    return None
