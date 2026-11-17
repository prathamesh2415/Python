from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path

from .assemble import assemble_reel
from .generate_content import generate_reel_package
from .images import render_stills
from .llm import normalize_provider
from .tts import synthesize_voice

logger = logging.getLogger(__name__)


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")[:48] or "reel"


async def run_pipeline(
    niche: str,
    story: str | None = None,
    language: str = "en",
    provider: str = "auto",
    model: str | None = None,
    mode: str | None = None,
    out_root: Path | None = None,
    voice: str | None = None,
    tts_engine: str = "auto",
    image_mode: str = "cards",
    duration_seconds: float = 30.0,
) -> Path:
    root = Path(__file__).resolve().parents[1]
    out_root = out_root or (root / "reels")
    stamp = datetime.now().strftime("%Y-%m-%d")
    resolved_provider = normalize_provider(provider, mode)

    package = await generate_reel_package(
        niche=niche,
        story=story,
        language=language,
        provider=resolved_provider,
        model=model,
        duration_seconds=duration_seconds,
    )
    folder = out_root / f"{stamp}-{_slugify(package.title)}"
    stills_dir = folder / "stills"
    clips_dir = folder / "clips"
    export_dir = folder / "export"
    for path in (stills_dir, clips_dir, export_dir):
        path.mkdir(parents=True, exist_ok=True)

    (folder / "package.json").write_text(package.model_dump_json(indent=2))
    caption = package.caption.strip()
    if package.hashtags:
        caption += "\n\n" + " ".join(
            h if h.startswith("#") else f"#{h}" for h in package.hashtags
        )
    (folder / "caption.txt").write_text(caption + "\n")
    (folder / "brief.md").write_text(
        "\n".join(
            [
                f"# {package.title}",
                "",
                f"Niche: {package.niche}",
                f"Hook: {package.hook}",
                f"Language: {package.language}",
                f"Provider: {resolved_provider}",
                f"Model: {model or '(provider default)'}",
                f"Images: {image_mode}",
                f"Target duration: {duration_seconds:.0f}s",
                "",
                "## Scenes",
                *[
                    f"{s.number}. ({s.duration_seconds:.1f}s) {s.on_screen_text} — {s.narration}"
                    for s in package.scenes
                ],
                "",
                "## Caption",
                caption,
                "",
            ]
        )
    )

    stills = await render_stills(package, stills_dir, image_mode=image_mode)
    voice_path = export_dir / "voice.mp3"
    voice_path = await synthesize_voice(
        package.full_narration,
        voice_path,
        language=language,
        voice=voice,
        engine=tts_engine,
        target_seconds=duration_seconds,
    )
    reel_path = assemble_reel(
        package,
        stills,
        voice_path,
        export_dir,
        target_seconds=duration_seconds,
    )

    manifest = {
        "folder": str(folder),
        "reel": str(reel_path),
        "caption_file": str(folder / "caption.txt"),
        "package": str(folder / "package.json"),
        "provider": resolved_provider,
        "model": model,
        "image_mode": image_mode,
        "duration_seconds": duration_seconds,
        "next_manual_steps": [
            "Open export/reel.mp4",
            "Optional: add Instagram trending audio in CapCut/Edits",
            "Paste caption.txt when uploading the Reel",
            "See RESOURCES.md for NotebookLM / Google Flow manual video paths",
        ],
    }
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2))
    logger.info("Pipeline complete: %s", reel_path)
    return folder
