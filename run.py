#!/usr/bin/env python3
"""Start Buffett Terminal."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import uvicorn


def main() -> None:
    # Platforms set PORT; bind all interfaces when hosted.
    port = int(os.environ.get("PORT", "8765"))
    host = os.environ.get("HOST") or ("0.0.0.0" if os.environ.get("PORT") else "127.0.0.1")
    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        reload=os.environ.get("RELOAD", "0") == "1",
        log_level="info",
    )


if __name__ == "__main__":
    main()
