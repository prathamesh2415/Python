from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .gemini_client import gemini_generate_image
from .models import ReelPackage
from .render_scenes import render_all_scenes, render_scene_image

logger = logging.getLogger(__name__)


def _font(size: int) -> ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def _overlay_caption(image_path: Path, text: str) -> None:
    """Burn short on-screen text onto a generated image for readability."""
    img = Image.open(image_path).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font = _font(48 if img.width >= 900 else 32)
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if font.getlength(trial) <= img.width - 80:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    lines = lines[:3]

    block_h = 30 + len(lines) * 58
    top = img.height - block_h - 80
    draw.rectangle((0, top, img.width, img.height), fill=(0, 0, 0, 150))
    y = top + 24
    for line in lines:
        draw.text((40, y + 2), line, font=font, fill=(0, 0, 0, 200))
        draw.text((40, y), line, font=font, fill=(255, 255, 255, 255))
        y += 58
    Image.alpha_composite(img, overlay).convert("RGB").save(image_path)


async def render_stills(
    package: ReelPackage,
    stills_dir: Path,
    image_mode: str = "cards",
) -> list[Path]:
    """Render stills.

    image_mode:
      - cards: local gradient text cards (free, no API)
      - gemini: Gemini image API per scene (may require Google billing)
      - gemini-fallback: try Gemini, fall back to cards per scene
    """
    image_mode = image_mode.lower().strip()
    stills_dir.mkdir(parents=True, exist_ok=True)

    if image_mode == "cards":
        return render_all_scenes(package, stills_dir)

    paths: list[Path] = []
    for scene in package.scenes:
        out = stills_dir / f"{scene.number:02d}.png"
        try:
            if image_mode not in {"gemini", "gemini-fallback"}:
                raise ValueError(f"Unknown image mode: {image_mode}")
            path = await gemini_generate_image(scene.visual_prompt, out)
            if scene.on_screen_text.strip():
                _overlay_caption(path, scene.on_screen_text)
            paths.append(path)
            logger.info("Gemini still ready: %s", path.name)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Gemini image failed for scene %s (%s)", scene.number, exc
            )
            if image_mode == "gemini":
                raise
            path = render_scene_image(scene, out, package.niche)
            paths.append(path)
    return paths
