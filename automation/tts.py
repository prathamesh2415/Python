from __future__ import annotations

import asyncio
import logging
import struct
import wave
from pathlib import Path

logger = logging.getLogger(__name__)

VOICE_MAP = {
    "en": "en-US-GuyNeural",
    "en-us": "en-US-GuyNeural",
    "en-gb": "en-GB-RyanNeural",
    "hi": "hi-IN-MadhurNeural",
    "hinglish": "en-IN-PrabhatNeural",
    "en-in": "en-IN-PrabhatNeural",
}


def _configure_ssl_certs() -> None:
    """Help Windows/Python find CA certs before Edge TTS connects."""
    from .ssl_util import configure_ssl_env

    configure_ssl_env()


async def _edge_tts_save(text: str, out_path: Path, voice_name: str) -> Path:
    import edge_tts

    _configure_ssl_certs()
    communicate = edge_tts.Communicate(text, voice_name)
    await communicate.save(str(out_path))
    return out_path


def _local_tts_save(text: str, out_path: Path) -> Path:
    """Offline TTS via Windows SAPI / system voices (pyttsx3)."""
    import pyttsx3

    wav_path = out_path.with_suffix(".wav")
    engine = pyttsx3.init()
    engine.setProperty("rate", 175)
    engine.save_to_file(text, str(wav_path))
    engine.runAndWait()
    if not wav_path.exists() or wav_path.stat().st_size < 100:
        raise RuntimeError("Local TTS produced an empty audio file")

    # Keep wav — ffmpeg (system or bundled) can mux it later.
    return wav_path


def _write_silent_wav(out_path: Path, seconds: float = 20.0) -> Path:
    """Pure-Python silent WAV (no ffmpeg required)."""
    out_path = out_path.with_suffix(".wav")
    sample_rate = 44100
    n_samples = max(1, int(seconds * sample_rate))
    with wave.open(str(out_path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        # Write in chunks to avoid huge memory spikes
        chunk = 44100
        silence = struct.pack("<h", 0) * min(chunk, n_samples)
        remaining = n_samples
        while remaining > 0:
            take = min(chunk, remaining)
            if take == chunk:
                handle.writeframes(silence)
            else:
                handle.writeframes(struct.pack("<h", 0) * take)
            remaining -= take
    return out_path


def _silent_audio(out_path: Path, seconds: float = 20.0) -> Path:
    """Silent track: try ffmpeg, else pure Python WAV."""
    seconds = max(1.0, float(seconds))
    try:
        from .ffmpeg_tools import run_ffmpeg

        mp3_path = out_path.with_suffix(".mp3")
        run_ffmpeg(
            [
                "-y",
                "-f",
                "lavfi",
                "-i",
                "anullsrc=r=44100:cl=mono",
                "-t",
                f"{seconds:.2f}",
                "-q:a",
                "9",
                "-acodec",
                "libmp3lame",
                str(mp3_path),
            ]
        )
        return mp3_path
    except Exception as exc:  # noqa: BLE001
        logger.warning("ffmpeg silent audio failed (%s); writing WAV instead", exc)
        return _write_silent_wav(out_path, seconds)


async def synthesize_voice(
    text: str,
    out_path: Path,
    language: str = "en",
    voice: str | None = None,
    engine: str = "auto",
    target_seconds: float | None = None,
) -> Path:
    """Create narration audio.

    engine:
      - auto: edge-tts → local pyttsx3 → silent
      - edge: Microsoft Edge online TTS only
      - local: pyttsx3 / Windows SAPI only
      - silent: no narration (silent audio bed)
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    engine = engine.lower().strip()
    chosen = voice or VOICE_MAP.get(language.lower(), VOICE_MAP["en"])
    approx_seconds = float(target_seconds) if target_seconds else max(8.0, len(text.split()) * 0.4)

    if engine == "silent":
        path = await asyncio.to_thread(_silent_audio, out_path, approx_seconds)
        logger.warning("Using silent audio (--tts silent). Add trending music in CapCut.")
        return path

    errors: list[str] = []

    if engine in {"auto", "edge"}:
        try:
            path = await _edge_tts_save(text, out_path, chosen)
            logger.info("Wrote voiceover via edge-tts (%s): %s", chosen, path)
            return path
        except Exception as exc:  # noqa: BLE001
            msg = f"edge-tts failed: {exc}"
            errors.append(msg)
            logger.warning(msg)
            if engine == "edge":
                raise RuntimeError(
                    "edge-tts SSL/network failed on this machine. "
                    "Try: pip install -U certifi edge-tts   "
                    "or run with --tts local   "
                    "or --tts silent"
                ) from exc

    if engine in {"auto", "local"}:
        try:
            path = await asyncio.to_thread(_local_tts_save, text, out_path)
            logger.info("Wrote voiceover via local TTS: %s", path)
            return path
        except Exception as exc:  # noqa: BLE001
            msg = f"local TTS failed: {exc}"
            errors.append(msg)
            logger.warning(msg)
            if engine == "local":
                raise RuntimeError(
                    "Local TTS failed. Install with: pip install pyttsx3   "
                    "On Windows this uses built-in SAPI voices."
                ) from exc

    fallback_seconds = float(target_seconds) if target_seconds else approx_seconds
    path = await asyncio.to_thread(_silent_audio, out_path, fallback_seconds)
    logger.warning(
        "All TTS engines failed (%s). Built silent audio instead. "
        "Add Instagram trending audio in CapCut before upload.",
        " | ".join(errors),
    )
    return path
