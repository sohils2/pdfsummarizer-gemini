"""Phase 0 helper: verify the Gemini key, model availability and Git tooling.

Run with::

    .venv\\Scripts\\python.exe validate_setup.py

The API key is read from ``.env`` and is never printed.
"""

from __future__ import annotations

import json
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request

from config import DEFAULT_MODEL, FALLBACK_MODELS, api_key_is_present, get_api_key, get_model

MODELS_URL = "https://generativelanguage.googleapis.com/v1beta/models"
REQUEST_TEXT = "Reply with exactly: OK"


def _url(path: str, key: str) -> str:
    return f"{path}?key={urllib.parse.quote(key)}"


def _get(url: str, timeout: int = 20) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.load(response)


def _post_generate(model: str, key: str, timeout: int = 30) -> str:
    payload = {"contents": [{"parts": [{"text": REQUEST_TEXT}]}]}
    request = urllib.request.Request(
        _url(f"{MODELS_URL}/{model}:generateContent", key),
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.load(response)
    parts = data["candidates"][0]["content"].get("parts", [])
    return "".join(part.get("text", "") for part in parts).strip()


def _status(message: str, ok: bool) -> bool:
    print(f"[{'OK' if ok else 'FAIL'}] {message}")
    return ok


def main() -> int:
    results: list[bool] = []
    key = get_api_key()

    results.append(_status("GEMINI_API_KEY is set and long enough", api_key_is_present()))
    if not key:
        return 1

    try:
        data = _get(_url(MODELS_URL, key))
        models = [
            item["name"].removeprefix("models/")
            for item in data.get("models", [])
            if "generateContent" in item.get("supportedGenerationMethods", [])
        ]
        results.append(_status(f"API key accepted ({len(models)} generateContent models visible)", True))
    except (urllib.error.URLError, ValueError, KeyError) as exc:
        results.append(_status(f"API key rejected or model listing failed: {exc}", False))
        return 1

    selected = get_model()
    candidates = [selected, *(model for model in (DEFAULT_MODEL, *FALLBACK_MODELS) if model != selected)]
    working: str | None = None
    for model in candidates:
        if model not in models:
            continue
        try:
            reply = _post_generate(model, key)
        except (urllib.error.URLError, ValueError, KeyError, IndexError) as exc:
            print(f"       {model}: unavailable ({exc})")
            continue
        working = model
        results.append(_status(f"Generation works with {model} (reply: {reply[:40]!r})", True))
        break

    if working is None:
        results.append(_status("No configured model could generate a response", False))
    elif working != selected:
        print(f"       Suggested GEMINI_MODEL in .env: {working}")

    for tool in ("git", "gh"):
        path = shutil.which(tool)
        results.append(_status(f"{tool} found at {path}" if path else f"{tool} not on PATH", bool(path)))

    passed = all(results)
    print("\nPhase 0:", "PASSED" if passed else "FAILED")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
