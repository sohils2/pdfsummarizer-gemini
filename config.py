"""Environment configuration for the PDF summarizer.

Secrets are read from the process environment (or a local ``.env`` file) and
are never hard-coded. The default model is one that has been verified against
a live Gemini API key during Phase 0.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = "gemini-3.5-flash-lite"
FALLBACK_MODELS: tuple[str, ...] = (
    "gemini-flash-lite-latest",
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
)
SUPPORTED_MODELS: tuple[str, ...] = (DEFAULT_MODEL, *FALLBACK_MODELS)
MIN_KEY_LENGTH = 20


def get_api_key() -> str | None:
    """Return the configured Gemini API key, or ``None`` when it is missing."""
    key = os.getenv("GEMINI_API_KEY", "").strip().strip('"').strip("'")
    return key or None


def get_model() -> str:
    """Return the configured model, falling back to the verified default."""
    configured = os.getenv("GEMINI_MODEL", "").strip()
    return configured or DEFAULT_MODEL


def model_options() -> list[str]:
    """Order the model list so the configured model appears first."""
    selected = get_model()
    return [selected, *(model for model in SUPPORTED_MODELS if model != selected)]


def api_key_is_present() -> bool:
    """Cheap structural check used by the UI before any network call."""
    key = get_api_key()
    return bool(key and len(key) >= MIN_KEY_LENGTH)
