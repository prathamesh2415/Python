from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

from .assemble import stitch_stills_to_video
from .llm import PROVIDERS, normalize_provider
from .pipeline import run_pipeline
from .ssl_util import configure_ssl_env


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="faceless-auto",
        description=(
            "Automate faceless Reel drafting: script → stills → voice → MP4. "
            "Supports offline templates plus Gemini/Groq/OpenRouter/OpenAI."
        ),
    )
    sub = parser.add_subparsers(dest="command")

    run_p = sub.add_parser("run", help="Generate a full draft reel")
    _add_run_args(run_p)

    stitch_p = sub.add_parser(
        "stitch",
        help="Club existing still images into one MP4",
    )
    stitch_p.add_argument("--stills", required=True, type=Path)
    stitch_p.add_argument("--out", type=Path, default=None)
    stitch_p.add_argument("--seconds", type=float, default=3.5)
    stitch_p.add_argument("--voice", type=Path, default=None)
    stitch_p.add_argument("-v", "--verbose", action="store_true")

    _add_run_args(parser)
    return parser


def _add_run_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--niche", help='e.g. "forgotten Indian history"')
    parser.add_argument("--story", default=None, help="Optional story title/hint")
    parser.add_argument("--language", default="en", help="en | hi | hinglish | en-in")
    parser.add_argument(
        "--provider",
        default=None,
        choices=list(PROVIDERS),
        help=(
            "LLM provider: auto|offline|gemini|groq|openrouter|openai. "
            "auto = Gemini → Groq → OpenRouter → OpenAI → offline"
        ),
    )
    parser.add_argument(
        "--mode",
        default=None,
        choices=list(PROVIDERS),
        help="Alias for --provider (kept for backward compatibility)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help=(
            "Model id override, e.g. gemini-3.1-pro-preview, "
            "openai/gpt-oss-120b, or an OpenRouter :free model id"
        ),
    )
    parser.add_argument(
        "--images",
        default="cards",
        choices=["cards", "gemini", "gemini-fallback"],
        help=(
            "cards=local text cards (free); "
            "gemini=Gemini image API; "
            "gemini-fallback=try Gemini then cards"
        ),
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=30.0,
        help="Target reel length in seconds (default 30). Scripts/hooks are written to fit.",
    )
    parser.add_argument("--out", type=Path, default=None, help="Output root (default ./reels)")
    parser.add_argument("--voice", default=None, help="Optional edge-tts voice name")
    parser.add_argument(
        "--tts",
        default="auto",
        choices=["auto", "edge", "local", "silent"],
        help="Voice engine (local recommended on Windows if Edge SSL fails)",
    )
    parser.add_argument("-v", "--verbose", action="store_true")


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    configure_ssl_env()
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if getattr(args, "verbose", False) else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    command = getattr(args, "command", None)

    if command == "stitch":
        stills_dir: Path = args.stills
        if not stills_dir.exists():
            print(f"Stills folder not found: {stills_dir}", file=sys.stderr)
            return 1
        patterns = ("*.png", "*.jpg", "*.jpeg", "*.webp")
        stills: list[Path] = []
        for pattern in patterns:
            stills.extend(sorted(stills_dir.glob(pattern)))
        if not stills:
            print(f"No images found in {stills_dir}", file=sys.stderr)
            return 1
        export_dir = args.out or (stills_dir.parent / "export")
        out = stitch_stills_to_video(
            stills=stills,
            export_dir=export_dir,
            voice_path=args.voice,
            seconds_per_still=args.seconds,
        )
        print(f"\nDone. Video:\n{out}")
        return 0

    if not getattr(args, "niche", None):
        parser.error("--niche is required (or use: python -m automation stitch --stills ...)")

    # Recommended product path: auto scripts (C) + free card stills (A)
    provider = normalize_provider(args.provider, args.mode or "auto")

    folder = asyncio.run(
        run_pipeline(
            niche=args.niche,
            story=args.story,
            language=args.language,
            provider=provider,
            model=args.model,
            out_root=args.out,
            voice=args.voice,
            tts_engine=args.tts,
            image_mode=args.images,
            duration_seconds=args.duration,
        )
    )
    print(f"\nDone. Output folder:\n{folder}")
    print(f"Video: {folder / 'export' / 'reel.mp4'}")
    print(f"Caption: {folder / 'caption.txt'}")
    print(f"Provider: {provider} | Images: {args.images} | Target: {args.duration:.0f}s")
    if provider in {"offline", "auto"} and args.images == "cards":
        print("\nFor high-quality 30s hooks: put GEMINI_API_KEY in .env, then:")
        print(
            'python -m automation --niche "forgotten Indian history" '
            "--provider gemini --model gemini-3.1-pro-preview "
            "--images cards --duration 30 --tts local"
        )
        print("See RESOURCES.md for free keys / NotebookLM / Flow.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
