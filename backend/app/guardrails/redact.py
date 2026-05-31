"""Redact sensitive information (API keys, Bearer tokens) from logs and error messages.

Inspired by competitorsmart's src/redact.py — prevents accidental leakage
of secrets in log output, SSE events, and API error responses.
"""

from __future__ import annotations

import re
from app.config import settings


def gather_secrets() -> list[str]:
    """Collect all non-empty secret values from settings."""
    secrets: list[str] = []
    for key in settings.llm_api_keys:
        if key:
            secrets.append(key)
    if settings.TAVILY_API_KEY:
        secrets.append(settings.TAVILY_API_KEY)
    return secrets


# Pre-compiled patterns for common secret formats
_BEARER_PATTERN = re.compile(r"Bearer\s+[A-Za-z0-9\-_.~+/]+=*", re.IGNORECASE)
_API_KEY_PATTERN = re.compile(r"(api[_-]?key|token|secret|password)\s*[=:]\s*\S+", re.IGNORECASE)


def redact_secrets(text: str, extra_secrets: list[str] | None = None) -> str:
    """Replace known secret values with [REDACTED] in the given text."""
    secrets = gather_secrets()
    if extra_secrets:
        secrets.extend(extra_secrets)

    for secret in secrets:
        if secret and secret in text:
            text = text.replace(secret, "[REDACTED]")

    # Redact Bearer tokens that may not be in the explicit secrets list
    text = _BEARER_PATTERN.sub("Bearer [REDACTED]", text)

    return text


def safe_error_message(exc: Exception) -> str:
    """Return a redacted version of an exception message."""
    return redact_secrets(str(exc))
