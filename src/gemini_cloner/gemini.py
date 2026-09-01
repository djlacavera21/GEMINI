from __future__ import annotations

import json
from typing import Any

import httpx

from gemini_cloner.config import Settings


class GeminiError(RuntimeError):
    pass


ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def generate(settings: Settings, prompt: str, timeout: float = 60.0) -> str:
    if not settings.api_key:
        raise GeminiError(
            "GEMINI_API_KEY is not set. Copy .env.example to .env and add a public Gemini API key."
        )
    url = ENDPOINT.format(model=settings.model)
    payload: dict[str, Any] = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 4096},
    }
    with httpx.Client(timeout=timeout) as client:
        response = client.post(url, params={"key": settings.api_key}, json=payload)
    if response.status_code >= 400:
        raise GeminiError(f"Gemini API {response.status_code}: {response.text[:500]}")
    data = response.json()
    try:
        parts = data["candidates"][0]["content"]["parts"]
        text = "".join(part.get("text", "") for part in parts)
    except (KeyError, IndexError, TypeError) as exc:
        raise GeminiError(f"Unexpected Gemini payload: {json.dumps(data)[:400]}") from exc
    if not text.strip():
        raise GeminiError("Gemini returned an empty candidate")
    return text.strip()
