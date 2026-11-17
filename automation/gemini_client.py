from __future__ import annotations

import base64
import logging
import os
from pathlib import Path
from typing import Any

from .ssl_util import make_async_client

logger = logging.getLogger(__name__)

# Current defaults (Nov 2026). gemini-2.5-pro is retired for many new API projects.
DEFAULT_TEXT_MODEL = "gemini-3.1-pro-preview"
DEFAULT_FAST_MODEL = "gemini-3.1-flash-lite"
DEFAULT_IMAGE_MODEL = "gemini-3.1-flash-lite-image"

# Old CLI/docs names → current model ids
MODEL_ALIASES = {
    "gemini-2.5-pro": "gemini-3.1-pro-preview",
    "gemini-2.0-pro": "gemini-3.1-pro-preview",
    "gemini-pro": "gemini-3.1-pro-preview",
    "gemini-1.5-pro": "gemini-3.1-pro-preview",
    "gemini-2.5-flash": "gemini-3.1-flash-lite",
    "gemini-2.0-flash": "gemini-3.1-flash-lite",
    "gemini-1.5-flash": "gemini-3.1-flash-lite",
    "gemini-flash": "gemini-3.1-flash-lite",
    "gemini-2.5-flash-image": "gemini-3.1-flash-lite-image",
}


def gemini_api_key() -> str | None:
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


def resolve_gemini_model(model: str | None, *, image: bool = False) -> str:
    raw = (model or "").strip()
    if not raw:
        if image:
            raw = os.getenv("GEMINI_IMAGE_MODEL", DEFAULT_IMAGE_MODEL)
        else:
            raw = os.getenv("GEMINI_TEXT_MODEL", DEFAULT_TEXT_MODEL)
    raw = raw.removeprefix("models/")
    resolved = MODEL_ALIASES.get(raw, raw)
    if resolved != raw:
        logger.info("Mapped retired Gemini model %s → %s", raw, resolved)
    return resolved


def _auth_headers(api_key: str) -> dict[str, str]:
    # Prefer header so the key is not printed in httpx URL logs.
    return {"x-goog-api-key": api_key}


async def gemini_generate_text(prompt: str, *, model: str | None = None) -> str:
    api_key = gemini_api_key()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY (or GOOGLE_API_KEY) is not set")

    model_name = resolve_gemini_model(model, image=False)
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model_name}:generateContent"
    )
    payload: dict[str, Any] = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "responseMimeType": "application/json",
        },
    }
    async with make_async_client(timeout=120) as client:
        resp = await client.post(url, headers=_auth_headers(api_key), json=payload)
        if resp.status_code >= 400:
            raise RuntimeError(
                f"Gemini text API error {resp.status_code}: {resp.text[:800]}"
            )
        data = resp.json()

    try:
        parts = data["candidates"][0]["content"]["parts"]
        texts = [p.get("text", "") for p in parts if p.get("text")]
        text = "\n".join(texts).strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected Gemini response: {data}") from exc
    if not text:
        raise RuntimeError("Gemini returned empty text")
    logger.info("Gemini text ok via model=%s", model_name)
    return text


async def gemini_generate_image(
    prompt: str,
    out_path: Path,
    *,
    model: str | None = None,
    aspect_ratio: str = "9:16",
) -> Path:
    """Generate one image with Gemini image model.

    Note: Google's image models often require billing even if the API key is free.
    """
    api_key = gemini_api_key()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY (or GOOGLE_API_KEY) is not set")

    model_name = resolve_gemini_model(model, image=True)
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model_name}:generateContent"
    )
    full_prompt = (
        f"{prompt}\n\n"
        f"Vertical Instagram Reel still, aspect ratio {aspect_ratio}, "
        "cinematic lighting, no watermark, no logos, no readable UI text, "
        "no celebrity likeness."
    )
    payload: dict[str, Any] = {
        "contents": [{"role": "user", "parts": [{"text": full_prompt}]}],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
        },
    }
    async with make_async_client(timeout=120) as client:
        resp = await client.post(url, headers=_auth_headers(api_key), json=payload)
        if resp.status_code >= 400:
            raise RuntimeError(
                f"Gemini image API error {resp.status_code}: {resp.text[:1000]}"
            )
        data = resp.json()

    inline_b64: str | None = None
    mime = "image/png"
    try:
        parts = data["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected Gemini image response: {data}") from exc

    for part in parts:
        inline = part.get("inlineData") or part.get("inline_data")
        if inline and inline.get("data"):
            inline_b64 = inline["data"]
            mime = inline.get("mimeType") or inline.get("mime_type") or mime
            break

    if not inline_b64:
        raise RuntimeError(
            "Gemini returned no image bytes. Image models may require billing "
            "on your Google AI Studio / Cloud project."
        )

    raw = base64.b64decode(inline_b64)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if "jpeg" in mime or "jpg" in mime:
        out_path = out_path.with_suffix(".jpg")
    else:
        out_path = out_path.with_suffix(".png")
    out_path.write_bytes(raw)
    logger.info("Wrote Gemini image %s (%s bytes) model=%s", out_path, len(raw), model_name)
    return out_path
