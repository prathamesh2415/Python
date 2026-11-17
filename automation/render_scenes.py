from __future__ import annotations

import logging
import math
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .models import ReelPackage, Scene

logger = logging.getLogger(__name__)

WIDTH = 1080
HEIGHT = 1920


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def _palette(index: int) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    palettes = [
        ((18, 24, 38), (196, 92, 54)),
        ((12, 32, 28), (72, 160, 120)),
        ((28, 18, 36), (160, 80, 140)),
        ((24, 20, 16), (210, 160, 70)),
        ((16, 28, 48), (70, 130, 200)),
    ]
    return palettes[index % len(palettes)]


def _gradient_base(top: tuple[int, int, int], accent: tuple[int, int, int]) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), top)
    pixels = img.load()
    assert pixels is not None
    for y in range(HEIGHT):
        t = y / HEIGHT
        color = (
            int(top[0] * (1 - t) + accent[0] * t * 0.4),
            int(top[1] * (1 - t) + accent[1] * t * 0.4),
            int(top[2] * (1 - t) + accent[2] * t * 0.4),
        )
        for x in range(WIDTH):
            pixels[x, y] = color
    return img


def _wrapped_lines(text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    words = text.split() or [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        if font.getlength(trial) <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def render_scene_image(scene: Scene, out_path: Path, niche: str) -> Path:
    top, accent = _palette(scene.number)
    base = _gradient_base(top, accent).convert("RGBA")

    glow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    for i in range(5):
        x = int((i + 1) * WIDTH / 6)
        y = int(HEIGHT * (0.25 + 0.08 * math.sin(i + scene.number)))
        r = 90 + 18 * i
        gdraw.ellipse((x - r, y - r, x + r, y + r), fill=(*accent, 32))
    img = Image.alpha_composite(base, glow).convert("RGB")
    draw = ImageDraw.Draw(img)

    badge_font = _font(26)
    body_font = _font(56)
    small_font = _font(22)

    draw.text((72, 110), niche.upper()[:40], font=badge_font, fill=(230, 220, 200))
    draw.text((72, 155), f"SCENE {scene.number:02d}", font=badge_font, fill=accent)

    lines = _wrapped_lines(scene.on_screen_text, body_font, WIDTH - 160)
    total_h = len(lines) * 78
    y = (HEIGHT - total_h) // 2
    for line in lines:
        # soft shadow
        draw.text((82, y + 3), line, font=body_font, fill=(0, 0, 0))
        draw.text((80, y), line, font=body_font, fill=(245, 240, 230))
        y += 78

    draw.rectangle((0, HEIGHT - 160, WIDTH, HEIGHT), fill=(8, 8, 10))
    hint = textwrap.shorten(scene.visual_prompt, width=64, placeholder="…")
    draw.text((72, HEIGHT - 95), hint, font=small_font, fill=(160, 160, 160))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, quality=95)
    return out_path


def render_all_scenes(package: ReelPackage, stills_dir: Path) -> list[Path]:
    paths: list[Path] = []
    for scene in package.scenes:
        path = stills_dir / f"{scene.number:02d}.png"
        render_scene_image(scene, path, package.niche)
        paths.append(path)
        logger.info("Rendered %s", path.name)
    return paths
