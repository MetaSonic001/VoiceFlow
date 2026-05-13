"""
PII redaction helpers for logs, exports, and audit details.

Enterprise deployments should combine this with:
  - TLS for encryption in transit (terminating proxy / HTTPS)
  - Database and object-store encryption at rest (platform operator responsibility)
  - tenant.settings + credential encryption via credentials.py
"""
from __future__ import annotations

import re
from typing import Optional

_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
_PHONE_RE = re.compile(
    r"\b(?:\+?\d{1,3}[\s\-]?)?(?:\(?\d{3}\)?[\s\-]?)?\d{3}[\s\-]?\d{4}\b"
)


def redact_email(text: str, placeholder: str = "[email]") -> str:
    return _EMAIL_RE.sub(placeholder, text)


def redact_phone(text: str, placeholder: str = "[phone]") -> str:
    return _PHONE_RE.sub(placeholder, text)


def redact_pii(text: str) -> str:
    """Best-effort masking for log snippets and CSV exports."""
    if not text:
        return text
    return redact_phone(redact_email(text))


def preview_masked(text: Optional[str], max_len: int = 120) -> Optional[str]:
    """Short preview safe for audit metadata (length-capped, PII-redacted)."""
    if text is None:
        return None
    s = text if len(text) <= max_len else text[: max_len - 3] + "..."
    return redact_pii(s)
