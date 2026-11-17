"""Buffett Terminal — FastAPI application."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import data_service
from .universe import INDIA_BLUE_CHIPS, US_BLUE_CHIPS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("buffett_terminal")

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"

app = FastAPI(
    title="Buffett Terminal",
    description="Warren Buffett–style equity screener & market indicator for US and Indian stocks",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=32)
    market: Literal["us", "india", "in"] | None = None


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "buffett-terminal"}


@app.get("/api/indices")
def indices() -> dict:
    try:
        return data_service.fetch_indices()
    except Exception as exc:  # noqa: BLE001
        logger.exception("indices")
        raise HTTPException(status_code=502, detail=f"Failed to load indices: {exc}") from exc


@app.get("/api/buffett-indicator")
def buffett_indicator() -> dict:
    try:
        return data_service.buffett_market_indicator()
    except Exception as exc:  # noqa: BLE001
        logger.exception("buffett indicator")
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/screen")
def screen(
    market: Literal["us", "india", "both"] = Query("both"),
    limit: int = Query(40, ge=5, le=100),
) -> dict:
    try:
        rows = data_service.screen_market(market=market, limit=limit)
        return {"count": len(rows), "results": rows}
    except Exception as exc:  # noqa: BLE001
        logger.exception("screen")
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/analyze/{symbol}")
def analyze(
    symbol: str,
    market: Literal["us", "india", "in"] | None = None,
) -> dict:
    try:
        return data_service.analyze_symbol(symbol, market_hint=market)
    except Exception as exc:  # noqa: BLE001
        logger.exception("analyze %s", symbol)
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/analyze")
def analyze_post(body: AnalyzeRequest) -> dict:
    return analyze(body.symbol, body.market)


@app.get("/api/search")
def search(
    q: str = Query(..., min_length=1, max_length=40),
    market: Literal["us", "india", "both"] | None = "both",
) -> dict:
    try:
        return {"results": data_service.search_symbols(q, market=market)}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/universe")
def universe() -> dict:
    return {
        "us": US_BLUE_CHIPS,
        "india": INDIA_BLUE_CHIPS,
        "usCount": len(US_BLUE_CHIPS),
        "indiaCount": len(INDIA_BLUE_CHIPS),
    }


@app.get("/api/quote/{symbol}")
def quote(symbol: str) -> dict:
    try:
        return data_service.fetch_quote(symbol)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc)) from exc


# Static frontend
if STATIC.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")


@app.get("/")
def index() -> FileResponse:
    index_path = STATIC / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Frontend not found")
    return FileResponse(index_path)
