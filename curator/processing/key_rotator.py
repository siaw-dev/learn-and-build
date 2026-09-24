"""
curator/processing/key_rotator.py

Manages automatic rotation across up to 8 Gemini API keys.
Keys are read from GEMINI_KEY_1 … GEMINI_KEY_8 environment variables
(as GitHub Secrets in CI, or as .env entries for local testing).

Rotation strategy:
  • Start with key 1 (index 0)
  • On 429 (rate limit) or 401/400 API key errors → advance to next key
  • On success → stay on the current key for the rest of the session
  • If all keys are exhausted → raise RuntimeError (triggers heuristic fallback)

API standard: google-genai SDK >= 2.3.0
Uses client.interactions.create() per gemini-api-dev skill.
"""

from __future__ import annotations

import time
from typing import Optional

from google import genai

from curator.config import GEMINI_API_KEYS


class GeminiKeyRotator:
    """
    Manages a pool of Gemini API clients, rotating on quota/auth errors.

    Usage:
        rotator = GeminiKeyRotator()
        result = rotator.with_retry(fn, *args, **kwargs)
        # fn must accept a genai.Client as its first argument
    """

    # Error substrings that indicate we should try the next key
    _ROTATE_SIGNALS = (
        "429",
        "quota",
        "rate limit",
        "resource exhausted",
        "api_key_invalid",
        "permission_denied",
        "401",
        "invalid api key",
        "not_found",  # model not found — likely deprecated model
        "503",
        "unavailable",
        "high demand",
        "service_unavailable",
    )

    def __init__(self, keys: Optional[list[str]] = None):
        self._keys = keys or GEMINI_API_KEYS
        if not self._keys:
            raise RuntimeError(
                "No Gemini API keys configured. "
                "Set GEMINI_KEY_1 (through GEMINI_KEY_8) in GitHub Secrets or .env."
            )
        self._index = 0
        self._clients: dict[int, genai.Client] = {}

    def get_client(self) -> genai.Client:
        """Return a genai.Client for the current active key."""
        if self._index not in self._clients:
            self._clients[self._index] = genai.Client(
                api_key=self._keys[self._index]
            )
        return self._clients[self._index]

    @property
    def current_key_label(self) -> str:
        return f"GEMINI_KEY_{self._index + 1}"

    def on_error(self, error: Exception) -> bool:
        """
        Call when an API call fails.
        Returns True  → a new key is available; caller should retry.
        Returns False → all keys exhausted; caller should use fallback.
        """
        error_str = str(error).lower()
        should_rotate = any(sig.lower() in error_str for sig in self._ROTATE_SIGNALS)

        if not should_rotate:
            # Non-quota error (e.g., bad prompt, network) — don't rotate
            return False

        next_index = self._index + 1
        if next_index >= len(self._keys):
            return False  # All keys exhausted

        print(
            f"  🔄 Key {self.current_key_label} hit limit. "
            f"Rotating to GEMINI_KEY_{next_index + 1}..."
        )
        self._index = next_index
        return True

    def with_retry(self, fn, *args, max_key_attempts: int = 8, **kwargs):
        """
        Execute fn(client, *args, **kwargs) with automatic key rotation on failure.

        Args:
            fn:               Callable that takes a genai.Client as first argument.
            max_key_attempts: Maximum number of keys to try (default: all 8).
            *args, **kwargs:  Forwarded to fn after client.

        Returns:
            The return value of fn on success.

        Raises:
            RuntimeError: If all keys fail with quota/auth errors.
        """
        attempts = 0
        last_error: Optional[Exception] = None

        while attempts < min(max_key_attempts, len(self._keys)):
            client = self.get_client()
            try:
                return fn(client, *args, **kwargs)
            except Exception as e:
                last_error = e
                rotated = self.on_error(e)
                if not rotated:
                    raise  # Non-rotatable error — propagate immediately
                attempts += 1
                time.sleep(0.5)  # Brief pause before retry

        raise RuntimeError(
            f"All {len(self._keys)} Gemini API keys exhausted. "
            f"Last error: {last_error}"
        )


# ── Module-level singleton (created once per process) ───────────────────────
# Lazy-initialized so import doesn't fail when no keys are configured yet.
_rotator: Optional[GeminiKeyRotator] = None


def get_rotator() -> GeminiKeyRotator:
    """Return the process-level key rotator, creating it on first call."""
    global _rotator
    if _rotator is None:
        _rotator = GeminiKeyRotator()
    return _rotator
