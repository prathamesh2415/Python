"""Market data via yfinance — US & India equities, indices, Buffett Indicator."""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import pandas as pd
import yfinance as yf

from .buffett_score import BuffettAnalysis, score_stock
from .universe import (
    INDIA_BLUE_CHIPS,
    INDIA_GDP_USD,
    INDIA_INDICES,
    US_BLUE_CHIPS,
    US_GDP_USD,
    US_INDICES,
    US_MARKET_FALLBACK,
    US_MARKET_PROXY,
    market_of,
    normalize_symbol,
)

logger = logging.getLogger(__name__)

# Simple TTL cache
_CACHE: dict[str, tuple[float, Any]] = {}
_TTL_QUOTE = 120.0
_TTL_INFO = 900.0
_TTL_SCREEN = 1800.0


def _cache_get(key: str) -> Any | None:
    hit = _CACHE.get(key)
    if not hit:
        return None
    expires, value = hit
    if time.time() > expires:
        _CACHE.pop(key, None)
        return None
    return value


def _cache_set(key: str, value: Any, ttl: float) -> None:
    _CACHE[key] = (time.time() + ttl, value)


def _ticker_info(symbol: str) -> dict[str, Any]:
    key = f"info:{symbol}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    t = yf.Ticker(symbol)
    info = dict(t.info or {})
    info["symbol"] = symbol
    # Fast info fallbacks
    try:
        fi = t.fast_info
        if info.get("currentPrice") is None:
            info["currentPrice"] = getattr(fi, "last_price", None) or getattr(fi, "lastPrice", None)
        if info.get("marketCap") is None:
            info["marketCap"] = getattr(fi, "market_cap", None) or getattr(fi, "marketCap", None)
        if info.get("currency") is None:
            info["currency"] = getattr(fi, "currency", None)
    except Exception:  # noqa: BLE001
        pass
    _cache_set(key, info, _TTL_INFO)
    return info


def fetch_quote(symbol: str) -> dict[str, Any]:
    key = f"quote:{symbol}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    info = _ticker_info(symbol)
    hist = yf.Ticker(symbol).history(period="5d")
    change = None
    change_pct = None
    if hist is not None and len(hist) >= 2:
        last = float(hist["Close"].iloc[-1])
        prev = float(hist["Close"].iloc[-2])
        change = last - prev
        change_pct = (change / prev) * 100 if prev else None
        price = last
    else:
        price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")

    out = {
        "symbol": symbol,
        "name": info.get("shortName") or info.get("longName") or symbol,
        "price": price,
        "change": change,
        "changePct": change_pct,
        "currency": info.get("currency"),
        "market": market_of(symbol),
    }
    _cache_set(key, out, _TTL_QUOTE)
    return out


def fetch_indices() -> dict[str, list[dict[str, Any]]]:
    key = "indices:all"
    cached = _cache_get(key)
    if cached is not None:
        return cached

    def one(sym: str, label: str) -> dict[str, Any]:
        q = fetch_quote(sym)
        q["label"] = label
        return q

    us: list[dict[str, Any]] = []
    india: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = {
            pool.submit(one, s, n): ("US", s) for s, n in US_INDICES.items()
        }
        futs.update({pool.submit(one, s, n): ("IN", s) for s, n in INDIA_INDICES.items()})
        for fut in as_completed(futs):
            region, _ = futs[fut]
            try:
                row = fut.result()
                (us if region == "US" else india).append(row)
            except Exception as exc:  # noqa: BLE001
                logger.warning("index fetch failed: %s", exc)

    # Stable order
    us_order = list(US_INDICES.keys())
    in_order = list(INDIA_INDICES.keys())
    us.sort(key=lambda x: us_order.index(x["symbol"]) if x["symbol"] in us_order else 99)
    india.sort(key=lambda x: in_order.index(x["symbol"]) if x["symbol"] in in_order else 99)
    out = {"us": us, "india": india}
    _cache_set(key, out, _TTL_QUOTE)
    return out


def _market_cap_from_proxy(symbol: str) -> float | None:
    info = _ticker_info(symbol)
    mc = info.get("marketCap")
    if mc:
        return float(mc)
    # For indices, approximate via related ETF
    return None


def buffett_market_indicator() -> dict[str, Any]:
    """Classic Buffett Indicator ≈ Total equity market cap / GDP.

    US: prefer Wilshire 5000 total market value; fall back to VTI * scaling.
    India: approximate via Nifty-linked total market proxies and listed caps.
    """
    key = "buffett_indicator"
    cached = _cache_get(key)
    if cached is not None:
        return cached

    us_cap = None
    us_source = US_MARKET_PROXY
    try:
        # Wilshire may not expose marketCap; use Yahoo quote on ^W5000 level * historical factor is fragile.
        # Practical approach: sum is hard; use VTI AUM / approx share of market (~50%+ of US) — better:
        # Use yfinance for ^W5000 last price as index level; Wilshire level ~ market cap in billions historically.
        # Convention: Wilshire 5000 index points ≈ US total market cap in billions.
        hist = yf.Ticker(US_MARKET_PROXY).history(period="5d")
        if hist is not None and len(hist):
            level = float(hist["Close"].iloc[-1])
            # Wilshire Full Cap: index value ≈ market cap in $ billions
            us_cap = level * 1_000_000_000
            us_source = f"{US_MARKET_PROXY} (index≈$B market)"
    except Exception as exc:  # noqa: BLE001
        logger.warning("Wilshire fetch failed: %s", exc)

    if us_cap is None:
        try:
            vti = _ticker_info(US_MARKET_FALLBACK)
            # VTI holds ~entire US market; marketCap of VTI is fund AUM not total market.
            # Use SPY * rough multiplier or fetch ^GSPC * average share — approximate with known ratio.
            # Fallback: use a basket of mega caps is wrong. Use Yahoo "total market" via VT? 
            # Practical fallback used by many dashboards: S&P 500 market cap * 1.25 ≈ total US.
            spx_parts = ["SPY"]
            spy_mc = _safe_mc("SPY")
            # SPY is ~10% of S&P market; better use info on ^GSPC — no marketCap.
            # Use curated approximation from top holdings — skip; use fixed scaling from VTI NAV * shares.
            # yfinance fast_info for VTI: total assets
            t = yf.Ticker(US_MARKET_FALLBACK)
            fi = t.fast_info
            total_assets = getattr(fi, "total_assets", None) or vti.get("totalAssets")
            if total_assets:
                # VTI covers ~100% of investable US market by design of CRSP index — AUM is NOT market cap.
                pass
            # Last-resort published-style estimate: S&P500 ~80% of US; get approximate via 500 * avg
            us_cap = _estimate_us_total_from_quotes()
            us_source = "estimated from major ETF/index proxies"
        except Exception as exc:  # noqa: BLE001
            logger.warning("US cap fallback failed: %s", exc)
            us_cap = 55_000_000_000_000  # soft placeholder
            us_source = "fallback estimate"

    india_cap = _estimate_india_market_cap()
    india_source = "NSE listed universe approximation (Nifty-heavy)"

    def band(ratio: float) -> str:
        # Buffett Indicator zones (historical heuristics)
        if ratio < 0.75:
            return "SIGNIFICANTLY UNDERVALUED"
        if ratio < 0.90:
            return "MODESTLY UNDERVALUED"
        if ratio < 1.15:
            return "FAIR VALUE"
        if ratio < 1.40:
            return "MODESTLY OVERVALUED"
        return "SIGNIFICANTLY OVERVALUED"

    us_ratio = (us_cap / US_GDP_USD) if us_cap else None
    in_ratio = (india_cap / INDIA_GDP_USD) if india_cap else None

    out = {
        "us": {
            "marketCap": us_cap,
            "gdp": US_GDP_USD,
            "ratio": round(us_ratio, 3) if us_ratio else None,
            "ratioPct": round(us_ratio * 100, 1) if us_ratio else None,
            "zone": band(us_ratio) if us_ratio else None,
            "source": us_source,
        },
        "india": {
            "marketCap": india_cap,
            "gdp": INDIA_GDP_USD,
            "ratio": round(in_ratio, 3) if in_ratio else None,
            "ratioPct": round(in_ratio * 100, 1) if in_ratio else None,
            "zone": band(in_ratio) if in_ratio else None,
            "source": india_source,
        },
        "methodology": (
            "Buffett Indicator = Total stock market capitalization ÷ GDP. "
            "Zones are historical heuristics popularized by Buffett's 'market value to GNP' remarks — "
            "not investment advice. GDP figures are recent annual estimates and may lag."
        ),
        "asOf": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    _cache_set(key, out, _TTL_QUOTE)
    return out


def _safe_mc(symbol: str) -> float | None:
    try:
        mc = _ticker_info(symbol).get("marketCap")
        return float(mc) if mc else None
    except Exception:  # noqa: BLE001
        return None


def _estimate_us_total_from_quotes() -> float:
    """Rough US total market: use SPY market relationship or known index level scaling."""
    # Try QQQ/SPY/IWM not good. Use ^GSPC history + typical S&P market cap from top stocks * 1/0.8
    # Sum market caps of S&P-heavy liquid names is incomplete.
    # Prefer: download ticker "IWV" (iShares Russell 3000) — still AUM.
    # Practical industry hack with yfinance: use Wilshire via stooq-like — already tried.
    # Use average of mega-cap sum scaled:
    sample = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "BRK-B", "LLY", "AVGO", "JPM"]
    total = 0.0
    for s in sample:
        mc = _safe_mc(s)
        if mc:
            total += mc
    # Top 10 ~ ~35% of US market in recent years — scale carefully
    if total > 0:
        return total / 0.32
    return 55_000_000_000_000


def _estimate_india_market_cap() -> float:
    """Estimate India listed equity market cap in USD from major NSE names + scale."""
    # Fetch a broad set of India blue chips and scale to total market (~top 50 ≈ 60%+ of NSE)
    caps: list[float] = []
    with ThreadPoolExecutor(max_workers=12) as pool:
        futs = {pool.submit(_safe_mc, s): s for s in INDIA_BLUE_CHIPS[:30]}
        for fut in as_completed(futs):
            mc = fut.result()
            if mc:
                caps.append(mc)
    if not caps:
        return 4_500_000_000_000  # soft fallback ~$4.5T
    # yfinance India marketCap is typically in INR
    # Convert INR → USD roughly (assume ~83.5 if currency INR)
    # Check one ticker currency
    info = _ticker_info("RELIANCE.NS")
    currency = (info.get("currency") or "INR").upper()
    raw_sum = sum(caps)
    if currency == "INR":
        usd_sum = raw_sum / 83.5
    else:
        usd_sum = raw_sum
    # Our 30 names ≈ ~55% of India market cap historically for large-caps heavy sample
    return usd_sum / 0.55


def _looks_thin(info: dict[str, Any]) -> bool:
    """True when Yahoo returned almost nothing useful for fundamentals."""
    if not info:
        return True
    keys = ("marketCap", "trailingPE", "returnOnEquity", "currentPrice", "regularMarketPrice")
    return sum(1 for k in keys if info.get(k) is not None) < 2


def analyze_symbol(raw: str, market_hint: str | None = None) -> dict[str, Any]:
    symbol = normalize_symbol(raw, market_hint)
    info = _ticker_info(symbol)

    # Auto-fallback: bare names that are thin on US tape often exist on NSE
    if (
        market_hint in {None, "auto"}
        and "." not in symbol
        and not symbol.startswith("^")
        and _looks_thin(info)
    ):
        nse = f"{symbol}.NS"
        nse_info = _ticker_info(nse)
        if not _looks_thin(nse_info):
            symbol, info = nse, nse_info

    mkt = market_of(symbol)
    analysis = score_stock(info, market=mkt)
    hist = _history_series(symbol, period="1y")
    return {
        "analysis": analysis.to_dict(),
        "history": hist,
        "quote": fetch_quote(symbol),
    }


def _history_series(symbol: str, period: str = "1y") -> list[dict[str, Any]]:
    key = f"hist:{symbol}:{period}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    try:
        df = yf.Ticker(symbol).history(period=period)
        if df is None or df.empty:
            return []
        out = []
        for idx, row in df.iterrows():
            out.append(
                {
                    "date": idx.strftime("%Y-%m-%d"),
                    "close": round(float(row["Close"]), 4),
                    "volume": int(row["Volume"]) if not pd.isna(row["Volume"]) else 0,
                }
            )
        _cache_set(key, out, _TTL_INFO)
        return out
    except Exception as exc:  # noqa: BLE001
        logger.warning("history failed for %s: %s", symbol, exc)
        return []


def screen_market(market: str = "both", limit: int = 40) -> list[dict[str, Any]]:
    key = f"screen:{market}:{limit}"
    cached = _cache_get(key)
    if cached is not None:
        return cached

    symbols: list[str] = []
    if market in {"us", "both"}:
        symbols.extend(US_BLUE_CHIPS)
    if market in {"india", "in", "both"}:
        symbols.extend(INDIA_BLUE_CHIPS)

    results: list[dict[str, Any]] = []

    def work(sym: str) -> dict[str, Any] | None:
        try:
            info = _ticker_info(sym)
            analysis = score_stock(info, market=market_of(sym))
            d = analysis.to_dict()
            return {
                "symbol": d["symbol"],
                "name": d["name"],
                "market": d["market"],
                "currency": d["currency"],
                "price": d["price"],
                "score": d["total_score"],
                "grade": d["grade"],
                "verdict": d["verdict"],
                "intrinsicValue": d["intrinsic_value"],
                "marginOfSafetyPct": d["margin_of_safety_pct"],
                "roe": d["metrics"].get("roe"),
                "debtToEquity": d["metrics"].get("debtToEquity"),
                "pe": d["metrics"].get("pe"),
                "profitMargin": d["metrics"].get("profitMargin"),
                "sector": d["metrics"].get("sector"),
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning("screen %s failed: %s", sym, exc)
            return None

    with ThreadPoolExecutor(max_workers=16) as pool:
        futs = [pool.submit(work, s) for s in symbols]
        for fut in as_completed(futs):
            row = fut.result()
            if row and row.get("price"):
                results.append(row)

    results.sort(key=lambda r: r.get("score") or 0, reverse=True)
    results = results[:limit]
    _cache_set(key, results, _TTL_SCREEN)
    return results


def search_symbols(query: str, market: str | None = None) -> list[dict[str, Any]]:
    q = query.strip().upper()
    if not q:
        return []
    pool = []
    if market in {None, "both", "us"}:
        pool.extend(US_BLUE_CHIPS)
    if market in {None, "both", "india", "in"}:
        pool.extend(INDIA_BLUE_CHIPS)
    # Also allow direct ticker
    hits = []
    for s in pool:
        if q in s.upper():
            hits.append(s)
    if normalize_symbol(query, market) not in hits:
        # try resolving via yfinance
        cand = normalize_symbol(query, market)
        try:
            info = _ticker_info(cand)
            if info.get("regularMarketPrice") or info.get("currentPrice") or info.get("marketCap"):
                hits.insert(0, cand)
        except Exception:  # noqa: BLE001
            pass
    out = []
    for s in hits[:15]:
        try:
            info = _ticker_info(s)
            out.append(
                {
                    "symbol": s,
                    "name": info.get("longName") or info.get("shortName") or s,
                    "market": market_of(s),
                    "sector": info.get("sector"),
                }
            )
        except Exception:  # noqa: BLE001
            out.append({"symbol": s, "name": s, "market": market_of(s)})
    return out
