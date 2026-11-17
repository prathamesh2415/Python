from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from .gemini_client import gemini_api_key, gemini_generate_text
from .ssl_util import make_async_client

logger = logging.getLogger(__name__)

PROVIDERS = ("auto", "offline", "gemini", "groq", "openrouter", "openai")

DEFAULT_MODELS = {
    "gemini": os.getenv("GEMINI_TEXT_MODEL", "gemini-3.1-pro-preview"),
    "groq": os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
    "openrouter": os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free"),
    "openai": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
}

OPENAI_COMPAT = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "key_env": "GROQ_API_KEY",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "key_env": "OPENROUTER_API_KEY",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "key_env": "OPENAI_API_KEY",
    },
}

AUTO_ORDER = ("gemini", "groq", "openrouter", "openai")


def normalize_provider(provider: str | None, mode: str | None = None) -> str:
    """Map legacy --mode values onto --provider."""
    value = (provider or mode or os.getenv("LLM_PROVIDER") or "offline").lower().strip()
    if value not in PROVIDERS:
        raise ValueError(f"Unknown provider/mode: {value}. Choose from {PROVIDERS}")
    return value


def provider_has_key(provider: str) -> bool:
    if provider == "gemini":
        return bool(gemini_api_key())
    if provider == "offline":
        return True
    cfg = OPENAI_COMPAT.get(provider)
    if not cfg:
        return False
    return bool(os.getenv(cfg["key_env"]))


def available_providers() -> list[str]:
    return [p for p in AUTO_ORDER if provider_has_key(p)]


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    return json.loads(text)


async def _openai_compat_chat(
    provider: str,
    prompt: str,
    *,
    model: str | None = None,
) -> str:
    cfg = OPENAI_COMPAT[provider]
    api_key = os.getenv(cfg["key_env"])
    if not api_key:
        raise RuntimeError(f"{cfg['key_env']} is not set")

    model_name = model or DEFAULT_MODELS[provider]
    headers: dict[str, str] = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if provider == "openrouter":
        headers["HTTP-Referer"] = os.getenv("OPENROUTER_SITE_URL", "https://localhost")
        headers["X-Title"] = os.getenv("OPENROUTER_APP_NAME", "faceless-story-system")

    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": "You output only valid JSON."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
    }
    # Prefer JSON mode when the provider supports it
    if provider in {"openai", "groq"}:
        payload["response_format"] = {"type": "json_object"}

    url = f"{cfg['base_url'].rstrip('/')}/chat/completions"
    async with make_async_client(timeout=90) as client:
        resp = await client.post(url, headers=headers, json=payload)
        if resp.status_code >= 400:
            raise RuntimeError(
                f"{provider} API error {resp.status_code}: {resp.text[:800]}"
            )
        data = resp.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected {provider} response: {data}") from exc
    if not content:
        raise RuntimeError(f"{provider} returned empty content")
    return content


async def chat_text(
    prompt: str,
    *,
    provider: str,
    model: str | None = None,
) -> str:
    """Return raw text from a single provider."""
    provider = provider.lower().strip()
    if provider == "gemini":
        return await gemini_generate_text(prompt, model=model)
    if provider in OPENAI_COMPAT:
        return await _openai_compat_chat(provider, prompt, model=model)
    raise ValueError(f"Cannot chat with provider={provider}")


async def chat_json(
    prompt: str,
    *,
    provider: str = "auto",
    model: str | None = None,
) -> dict[str, Any]:
    """Call an LLM and parse JSON. Supports auto failover across free providers."""
    provider = normalize_provider(provider)
    model = model or os.getenv("LLM_MODEL") or None

    if provider == "offline":
        raise RuntimeError("offline provider has no chat endpoint")

    if provider != "auto":
        text = await chat_text(prompt, provider=provider, model=model)
        return _extract_json(text)

    errors: list[str] = []
    for candidate in AUTO_ORDER:
        if not provider_has_key(candidate):
            continue
        try:
            logger.info("Trying LLM provider=%s model=%s", candidate, model or DEFAULT_MODELS.get(candidate))
            text = await chat_text(prompt, provider=candidate, model=model)
            return _extract_json(text)
        except Exception as exc:  # noqa: BLE001
            msg = f"{candidate}: {exc}"
            errors.append(msg)
            logger.warning("Provider failed (%s)", msg)
    raise RuntimeError(
        "All configured LLM providers failed. "
        + (" | ".join(errors) if errors else "No API keys found.")
    )
