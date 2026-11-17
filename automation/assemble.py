from __future__ import annotations

import logging
import shutil
from pathlib import Path

from .ffmpeg_tools import probe_duration, run_ffmpeg
from .models import ReelPackage

logger = logging.getLogger(__name__)


def _safe_concat_path(path: Path) -> str:
    # ffmpeg concat demuxer on Windows prefers forward slashes
    return path.resolve().as_posix().replace("'", r"'\''")


def make_clip_from_still(still: Path, out_clip: Path, duration: float) -> Path:
    """Reliable still→video clip (no fragile zoompan). Works on Windows bundled ffmpeg."""
    duration = max(1.5, float(duration))
    # Scale to fit 1080x1920, pad letterbox if needed, slight zoom via scale+crop optional later.
    vf = (
        "scale=1080:1920:force_original_aspect_ratio=decrease,"
        "pad=1080:1920:(ow-iw)/2:(oh-ih)/2,"
        "format=yuv420p"
    )
    run_ffmpeg(
        [
            "-y",
            "-loop",
            "1",
            "-i",
            str(still),
            "-vf",
            vf,
            "-t",
            f"{duration:.3f}",
            "-r",
            "30",
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(out_clip),
        ]
    )
    return out_clip


def stitch_stills_to_video(
    stills: list[Path],
    export_dir: Path,
    voice_path: Path | None = None,
    seconds_per_still: float = 3.5,
    output_name: str = "reel.mp4",
) -> Path:
    """Club still images into one vertical MP4. No OpenAI required."""
    if not stills:
        raise ValueError("No still images provided")

    export_dir.mkdir(parents=True, exist_ok=True)
    work = export_dir / "work"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    if voice_path and voice_path.exists():
        total = probe_duration(voice_path)
        each = max(1.8, total / len(stills))
        durations = [each] * len(stills)
    else:
        durations = [seconds_per_still] * len(stills)
        # Create short silent wav so mux always has an audio track length target
        from .tts import _write_silent_wav

        voice_path = _write_silent_wav(
            export_dir / "voice.wav",
            seconds=seconds_per_still * len(stills),
        )

    clip_paths: list[Path] = []
    for idx, (still, dur) in enumerate(zip(stills, durations)):
        clip = work / f"clip_{idx:02d}.mp4"
        make_clip_from_still(still, clip, dur)
        clip_paths.append(clip)

    list_file = work / "clips.txt"
    list_file.write_text(
        "\n".join(f"file '{_safe_concat_path(p)}'" for p in clip_paths) + "\n",
        encoding="utf-8",
    )

    silent = work / "silent.mp4"
    run_ffmpeg(
        [
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-c",
            "copy",
            str(silent),
        ]
    )

    out = export_dir / output_name
    run_ffmpeg(
        [
            "-y",
            "-i",
            str(silent),
            "-i",
            str(voice_path),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            "-movflags",
            "+faststart",
            str(out),
        ]
    )
    logger.info("Stitched %s stills → %s", len(stills), out)
    return out


def assemble_reel(
    package: ReelPackage,
    stills: list[Path],
    voice_path: Path,
    export_dir: Path,
    target_seconds: float | None = None,
) -> Path:
    if not stills:
        raise ValueError("No stills to assemble")

    voice_dur = probe_duration(voice_path)
    # Prefer spoken length when narration exists; otherwise hit the target runtime.
    timeline = voice_dur
    if target_seconds and voice_dur < max(5.0, float(target_seconds) * 0.6):
        timeline = float(target_seconds)
    elif target_seconds and abs(voice_dur - float(target_seconds)) <= 4.0:
        timeline = float(target_seconds)

    weights = [max(0.5, s.duration_seconds) for s in package.scenes]
    # Align count if stills/scenes differ
    n = min(len(stills), len(weights))
    stills = stills[:n]
    weights = weights[:n]
    weight_sum = sum(weights) or 1.0
    durations = [max(1.8, timeline * (w / weight_sum)) for w in weights]

    export_dir.mkdir(parents=True, exist_ok=True)
    work = export_dir / "work"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    clip_paths: list[Path] = []
    for idx, (still, dur) in enumerate(zip(stills, durations)):
        clip = work / f"clip_{idx:02d}.mp4"
        make_clip_from_still(still, clip, dur)
        clip_paths.append(clip)

    list_file = work / "clips.txt"
    list_file.write_text(
        "\n".join(f"file '{_safe_concat_path(p)}'" for p in clip_paths) + "\n",
        encoding="utf-8",
    )
    silent = work / "silent.mp4"
    run_ffmpeg(
        [
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-c",
            "copy",
            str(silent),
        ]
    )

    out = export_dir / "reel.mp4"
    run_ffmpeg(
        [
            "-y",
            "-i",
            str(silent),
            "-i",
            str(voice_path),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            "-movflags",
            "+faststart",
            str(out),
        ]
    )
    logger.info("Assembled %s", out)
    return out
