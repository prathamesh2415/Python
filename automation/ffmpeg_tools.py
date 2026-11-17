from __future__ import annotations

import logging
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_ffmpeg() -> str:
    """Return an ffmpeg executable path (PATH first, then imageio-ffmpeg bundle)."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg

        bundled = imageio_ffmpeg.get_ffmpeg_exe()
        if bundled and Path(bundled).exists():
            logger.info("Using bundled ffmpeg from imageio-ffmpeg: %s", bundled)
            return bundled
    except Exception as exc:  # noqa: BLE001
        logger.debug("imageio-ffmpeg unavailable: %s", exc)
    raise RuntimeError(
        "ffmpeg not found. Install it, or run: pip install imageio-ffmpeg\n"
        "Windows install: winget install Gyan.FFmpeg   then reopen the terminal."
    )


@lru_cache(maxsize=1)
def get_ffprobe() -> str | None:
    found = shutil.which("ffprobe")
    if found:
        return found
    # Bundled imageio-ffmpeg usually ships ffmpeg only; duration can be probed via ffmpeg.
    return None


def run_ffmpeg(args: list[str]) -> None:
    cmd = [get_ffmpeg(), *args]
    logger.info("Running: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            "ffmpeg failed:\n"
            f"cmd: {' '.join(cmd)}\n"
            f"stdout: {result.stdout[-2000:]}\n"
            f"stderr: {result.stderr[-4000:]}"
        )


def probe_duration(path: Path) -> float:
    ffprobe = get_ffprobe()
    if ffprobe:
        result = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return float(result.stdout.strip())

    # Fallback: ask ffmpeg itself
    result = subprocess.run(
        [
            get_ffmpeg(),
            "-i",
            str(path),
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
    )
    # Duration is printed on stderr like: Duration: 00:00:24.33
    import re

    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", result.stderr)
    if not match:
        raise RuntimeError(f"Could not probe duration for {path}")
    hours, minutes, seconds = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
