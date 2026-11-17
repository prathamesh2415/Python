from __future__ import annotations

import logging
import re
from typing import Any

from .llm import chat_json, normalize_provider
from .models import ReelPackage, Scene

logger = logging.getLogger(__name__)

DEFAULT_DURATION_SECONDS = 30.0

STORY_BANK: list[dict[str, Any]] = [
    {
        "title": "The clerk who moved a rebellion",
        "hook": "He sorted the empire's mail — and hid a rebellion inside it.",
        "beats": [
            "In a quiet colonial post office, nobody watched the clerk.",
            "Ordinary envelopes carried coded plans between safe houses.",
            "When raids began, the mailbag moved first.",
            "History remembered the generals — not the man who carried the words.",
        ],
    },
    {
        "title": "The map that lied on purpose",
        "hook": "The most valuable map in the archive was drawn to deceive.",
        "beats": [
            "Explorers trusted a chart that had guided ships for decades.",
            "One coastline was shifted — not by mistake, but by design.",
            "Rivals followed it into empty water while the real route stayed secret.",
            "The lie on paper bought years of advantage.",
        ],
    },
    {
        "title": "The night the lighthouse went dark",
        "hook": "One dark night, a lighthouse saved a town by going silent.",
        "beats": [
            "Enemy ships used the beam as a landmark for attack.",
            "Keepers killed the light and lit false fires inland.",
            "The fleet aimed at empty cliffs.",
            "By dawn, the town still stood — and the secret stayed with the keepers.",
        ],
    },
]

_PACKAGE_PROMPT = """
You are an elite faceless Instagram Reels writer. Create ONE viral-ready story package.

Return pure JSON with keys:
title, hook, scenes (array of objects with on_screen_text, narration, visual_prompt, duration_seconds),
caption, hashtags (array), cta.

Niche: {niche}
Language: {language}
Story hint: {story}
Target total runtime: {duration_seconds:.0f} seconds (hard target)

STRUCTURE (must follow):
1) HOOK (first 1–2 seconds / scene 1): open loop, shock, or curiosity. No greeting. No "Once upon a time".
2) SETUP: who/when/stakes in plain words
3) ESCALATION: one concrete detail that raises tension
4) TWIST / TURN: the shareable reveal
5) PAYOFF: emotional ending
6) CTA: soft follow ask (last scene, short)

QUALITY RULES:
- Exactly 6 scenes
- Total narration length ≈ {word_target} words (for ~{duration_seconds:.0f}s spoken pace)
- Sum of duration_seconds MUST equal {duration_seconds:.0f}
- Scene 1 duration_seconds between 2.5 and 4.0 (hook punch)
- hook field = the exact first line viewers hear/read
- on_screen_text max 8 words, punchy, readable on mobile
- narration: vivid, specific nouns, zero fluff
- visual_prompt: cinematic still description, NO text in the image, no celebrity likeness
- Prefer shareable / saveable / emotional true-feeling stories
- No medical or financial advice, no hate, no copyrighted characters

Caption: line 1 = hook; then 2–4 short lines; soft CTA; 5–8 niche hashtags.

Return ONLY valid JSON (no markdown).
""".strip()


def _word_target(duration_seconds: float) -> int:
    # ~2.5 words/sec spoken pace for clear Reels narration
    return max(55, int(round(duration_seconds * 2.5)))


def _offline_package(
    niche: str,
    story: str | None,
    language: str,
    duration_seconds: float = DEFAULT_DURATION_SECONDS,
) -> ReelPackage:
    seed = STORY_BANK[hash((niche, story or "")) % len(STORY_BANK)]
    if story:
        title = story.strip()[:80]
        hook = f"Nobody expected this {niche} story to end like this."
        beats = [
            f"{title} starts with a detail most people ignore.",
            "At first, nothing looks dangerous — that is the trap.",
            "One decision flips who holds the power.",
            "The ending is why people still retell it.",
        ]
    else:
        title = seed["title"]
        hook = seed["hook"]
        beats = list(seed["beats"])

    # 6 scenes timed to target duration
    # hook slightly shorter punch, middle beats longer, CTA short
    weights = [3.0, 5.5, 5.5, 5.5, 6.0, 4.5]
    scale = duration_seconds / sum(weights)
    durations = [round(w * scale, 2) for w in weights]
    # fix rounding drift on last scene
    durations[-1] = round(duration_seconds - sum(durations[:-1]), 2)

    scenes: list[Scene] = [
        Scene(
            number=1,
            on_screen_text=_shorten(hook, 8),
            narration=hook,
            visual_prompt=f"Cinematic opening frame for {niche}: {title}, dramatic light, no text",
            duration_seconds=durations[0],
        )
    ]
    for i, beat in enumerate(beats, start=2):
        scenes.append(
            Scene(
                number=i,
                on_screen_text=_shorten(beat, 8),
                narration=beat,
                visual_prompt=f"Dramatic documentary still, {niche}, scene: {beat}, no text",
                duration_seconds=durations[i - 1],
            )
        )
    scenes.append(
        Scene(
            number=6,
            on_screen_text="Follow for more stories",
            narration="Follow for more stories like this.",
            visual_prompt=f"Simple closing cinematic card for a {niche} storytelling page, no text",
            duration_seconds=durations[5],
        )
    )

    caption = (
        f"{hook}\n\n"
        f"{title} — a {niche} story most people never heard.\n"
        "More forgotten stories daily."
    )
    package = ReelPackage(
        niche=niche,
        title=title,
        hook=hook,
        language=language,
        scenes=scenes,
        caption=caption,
        hashtags=[
            niche.replace(" ", "").lower()[:24] or "stories",
            "facelesspage",
            "storyreels",
            "viralreels",
        ],
        cta="Follow for more stories.",
    )
    return normalize_package_timing(package, duration_seconds)


def _shorten(text: str, max_words: int) -> str:
    words = re.findall(r"\S+", text)
    return " ".join(words[:max_words])


def _package_from_llm_json(data: dict[str, Any], niche: str, language: str) -> ReelPackage:
    scenes = [
        Scene(
            number=i + 1,
            on_screen_text=str(item.get("on_screen_text", ""))[:80],
            narration=str(item.get("narration", "")),
            visual_prompt=str(item.get("visual_prompt", "")),
            duration_seconds=float(item.get("duration_seconds", 4)),
        )
        for i, item in enumerate(data.get("scenes", []))
    ]
    if not scenes:
        raise RuntimeError("LLM returned no scenes")
    return ReelPackage(
        niche=niche,
        title=str(data.get("title", "Untitled")),
        hook=str(data.get("hook", scenes[0].narration)),
        language=language,
        scenes=scenes,
        caption=str(data.get("caption", "")),
        hashtags=[str(h) for h in data.get("hashtags", [])][:8],
        cta=str(data.get("cta", "Follow for more stories.")),
    )


def normalize_package_timing(
    package: ReelPackage,
    duration_seconds: float,
) -> ReelPackage:
    """Force scene durations to sum to target (keeps relative weights)."""
    if not package.scenes:
        return package
    weights = [max(0.5, s.duration_seconds) for s in package.scenes]
    total = sum(weights) or 1.0
    scaled: list[Scene] = []
    acc = 0.0
    for i, scene in enumerate(package.scenes):
        if i == len(package.scenes) - 1:
            dur = round(max(1.5, duration_seconds - acc), 2)
        else:
            dur = round(max(1.5, duration_seconds * (weights[i] / total)), 2)
            acc += dur
        scaled.append(scene.model_copy(update={"duration_seconds": dur}))
    return package.model_copy(update={"scenes": scaled})


async def generate_reel_package(
    niche: str,
    story: str | None = None,
    language: str = "en",
    provider: str = "auto",
    model: str | None = None,
    mode: str | None = None,
    duration_seconds: float = DEFAULT_DURATION_SECONDS,
) -> ReelPackage:
    """Generate a hook-led reel package aimed at duration_seconds (default 30)."""
    duration_seconds = float(duration_seconds)
    if duration_seconds < 15 or duration_seconds > 90:
        raise ValueError("duration_seconds must be between 15 and 90")

    resolved = normalize_provider(provider, mode)
    if resolved == "offline":
        return _offline_package(niche, story, language, duration_seconds)

    prompt = _PACKAGE_PROMPT.format(
        niche=niche,
        language=language,
        story=story or "invent a shareable true-feeling historical/mystery story with a strong twist",
        duration_seconds=duration_seconds,
        word_target=_word_target(duration_seconds),
    )
    try:
        data = await chat_json(prompt, provider=resolved, model=model)
        package = _package_from_llm_json(data, niche, language)
        return normalize_package_timing(package, duration_seconds)
    except Exception as exc:  # noqa: BLE001
        msg = str(exc)
        logger.warning("LLM package generation failed (%s); falling back offline", msg)
        if "CERTIFICATE_VERIFY_FAILED" in msg or "SSL" in msg:
            logger.warning(
                "Windows SSL tip: pip install -U certifi httpx  "
                "OR set FACELESS_SSL_INSECURE=1 in .env (last resort)"
            )
        if resolved != "auto":
            raise
        return _offline_package(niche, story, language, duration_seconds)
