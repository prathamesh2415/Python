"""Warren Buffett–style quality & valuation scoring.

Inspired by Berkshire's preference for:
- understandable businesses with durable economics (high ROE, margins, FCF)
- conservative balance sheets (low leverage)
- consistent owner earnings
- buying with a margin of safety vs intrinsic value
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class CriterionResult:
    key: str
    label: str
    value: float | str | None
    display: str
    score: float  # 0–10
    weight: float
    pass_fail: str  # PASS | WARN | FAIL | N/A
    note: str


@dataclass
class BuffettAnalysis:
    symbol: str
    name: str
    market: str
    currency: str
    price: float | None
    total_score: float  # 0–100
    grade: str
    verdict: str
    intrinsic_value: float | None
    margin_of_safety_pct: float | None
    criteria: list[CriterionResult] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


def _safe(v: Any) -> float | None:
    if v is None:
        return None
    try:
        f = float(v)
        if f != f:  # NaN
            return None
        return f
    except (TypeError, ValueError):
        return None


def _fmt_pct(v: float | None, digits: int = 1) -> str:
    if v is None:
        return "—"
    return f"{v * 100:.{digits}f}%" if abs(v) <= 5 else f"{v:.{digits}f}%"


def _fmt_num(v: float | None, digits: int = 2) -> str:
    if v is None:
        return "—"
    if abs(v) >= 1_000_000_000_000:
        return f"{v / 1_000_000_000_000:.{digits}f}T"
    if abs(v) >= 1_000_000_000:
        return f"{v / 1_000_000_000:.{digits}f}B"
    if abs(v) >= 1_000_000:
        return f"{v / 1_000_000:.{digits}f}M"
    return f"{v:.{digits}f}"


def _grade(score: float) -> str:
    if score >= 85:
        return "A+"
    if score >= 75:
        return "A"
    if score >= 65:
        return "B+"
    if score >= 55:
        return "B"
    if score >= 45:
        return "C"
    if score >= 35:
        return "D"
    return "F"


def _verdict(score: float, mos: float | None) -> str:
    undervalued = mos is not None and mos >= 20
    expensive = mos is not None and mos < -10
    if score >= 75 and undervalued:
        return "BUFFETT BUY ZONE — quality business at a discount"
    if score >= 75 and not expensive:
        return "QUALITY COMPOUNDERS — watch for better entry"
    if score >= 60 and undervalued:
        return "VALUE CANDIDATE — solid metrics, attractive price"
    if score >= 60:
        return "HOLD / RESEARCH — decent franchise, valuation mixed"
    if expensive:
        return "AVOID / WAIT — weak economics or stretched valuation"
    return "PASS FOR NOW — does not clear Buffett filters"


def estimate_intrinsic_value(
    eps: float | None,
    book_value: float | None,
    growth_rate: float | None,
    free_cash_flow: float | None,
    shares: float | None,
    aaa_yield: float = 0.045,
) -> float | None:
    """Blend of Graham number + owner-earnings capitalization + growth-adjusted EPS.

    Not a formal DCF — a pragmatic Buffett/Graham style sanity check.
    """
    candidates: list[float] = []

    g = growth_rate
    if g is not None:
        # Cap growth assumptions (Buffett hates heroic forecasts)
        g = max(min(g, 0.15), -0.05)

    if eps is not None and eps > 0:
        # Graham-style: EPS * (8.5 + 2g) * 4.4 / Y, with Y ~ corporate bond yield
        growth = g if g is not None else 0.05
        multiplier = (8.5 + 2 * (growth * 100)) * (4.4 / (aaa_yield * 100))
        # Soften extreme multipliers
        multiplier = min(max(multiplier, 8.0), 25.0)
        candidates.append(eps * multiplier)

    if book_value is not None and book_value > 0 and eps is not None and eps > 0:
        # Classic Graham number: sqrt(22.5 * EPS * BVPS)
        graham = (22.5 * eps * book_value) ** 0.5
        candidates.append(graham)

    if free_cash_flow is not None and shares is not None and shares > 0 and free_cash_flow > 0:
        # Owner earnings capitalized at required return ~9%
        fcf_ps = free_cash_flow / shares
        candidates.append(fcf_ps / 0.09)

    if not candidates:
        return None
    return sum(candidates) / len(candidates)


def score_stock(info: dict[str, Any], market: str = "US") -> BuffettAnalysis:
    symbol = str(info.get("symbol") or info.get("shortName") or "?")
    name = str(info.get("longName") or info.get("shortName") or symbol)
    currency = str(info.get("currency") or ("INR" if market == "IN" else "USD"))
    price = _safe(info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose"))

    roe = _safe(info.get("returnOnEquity"))
    roa = _safe(info.get("returnOnAssets"))
    profit_margin = _safe(info.get("profitMargins"))
    operating_margin = _safe(info.get("operatingMargins"))
    gross_margin = _safe(info.get("grossMargins"))
    debt_to_equity = _safe(info.get("debtToEquity"))
    # yfinance D/E is often percentage points (e.g. 50 = 0.5)
    if debt_to_equity is not None and debt_to_equity > 5:
        debt_to_equity = debt_to_equity / 100.0
    current_ratio = _safe(info.get("currentRatio"))
    pe = _safe(info.get("trailingPE") or info.get("forwardPE"))
    pb = _safe(info.get("priceToBook"))
    peg = _safe(info.get("pegRatio"))
    eps = _safe(info.get("trailingEps"))
    book = _safe(info.get("bookValue"))
    fcf = _safe(info.get("freeCashflow"))
    shares = _safe(info.get("sharesOutstanding"))
    earnings_growth = _safe(info.get("earningsGrowth") or info.get("earningsQuarterlyGrowth"))
    revenue_growth = _safe(info.get("revenueGrowth"))
    dividend_yield = _safe(info.get("dividendYield"))
    payout = _safe(info.get("payoutRatio"))
    beta = _safe(info.get("beta"))
    market_cap = _safe(info.get("marketCap"))
    enterprise_to_ebitda = _safe(info.get("enterpriseToEbitda"))
    target = _safe(info.get("targetMeanPrice"))

    criteria: list[CriterionResult] = []

    # 1. ROE — Buffett loves high returns on equity without leverage
    if roe is None:
        criteria.append(
            CriterionResult("roe", "Return on Equity", None, "—", 3.0, 1.5, "N/A", "Missing ROE data")
        )
    else:
        if roe >= 0.20:
            s, pf, note = 10.0, "PASS", "Excellent — compounding machine"
        elif roe >= 0.15:
            s, pf, note = 8.0, "PASS", "Meets Buffett 15%+ hurdle"
        elif roe >= 0.10:
            s, pf, note = 5.0, "WARN", "Average returns on equity"
        else:
            s, pf, note = 2.0, "FAIL", "Weak economic returns"
        criteria.append(
            CriterionResult("roe", "Return on Equity", roe, f"{roe * 100:.1f}%", s, 1.5, pf, note)
        )

    # 2. Debt / Equity — conservative balance sheet
    if debt_to_equity is None:
        criteria.append(
            CriterionResult("de", "Debt / Equity", None, "—", 4.0, 1.3, "N/A", "Missing leverage data")
        )
    else:
        if debt_to_equity <= 0.3:
            s, pf, note = 10.0, "PASS", "Fortress balance sheet"
        elif debt_to_equity <= 0.5:
            s, pf, note = 8.0, "PASS", "Conservative leverage"
        elif debt_to_equity <= 1.0:
            s, pf, note = 5.0, "WARN", "Moderate debt — dig into coverage"
        else:
            s, pf, note = 1.5, "FAIL", "Too leveraged for Buffett style"
        criteria.append(
            CriterionResult("de", "Debt / Equity", debt_to_equity, f"{debt_to_equity:.2f}", s, 1.3, pf, note)
        )

    # 3. Profit margin
    if profit_margin is None:
        criteria.append(
            CriterionResult("npm", "Net Profit Margin", None, "—", 3.0, 1.2, "N/A", "Missing margins")
        )
    else:
        if profit_margin >= 0.20:
            s, pf, note = 10.0, "PASS", "Wide margin — pricing power signal"
        elif profit_margin >= 0.10:
            s, pf, note = 8.0, "PASS", "Healthy profitability"
        elif profit_margin >= 0.05:
            s, pf, note = 5.0, "WARN", "Thin margins"
        else:
            s, pf, note = 2.0, "FAIL", "Poor profitability"
        criteria.append(
            CriterionResult(
                "npm",
                "Net Profit Margin",
                profit_margin,
                f"{profit_margin * 100:.1f}%",
                s,
                1.2,
                pf,
                note,
            )
        )

    # 4. Operating margin (moat proxy)
    if operating_margin is None:
        criteria.append(
            CriterionResult("opm", "Operating Margin", None, "—", 3.0, 1.0, "N/A", "Missing op. margin")
        )
    else:
        if operating_margin >= 0.25:
            s, pf, note = 10.0, "PASS", "Strong operating economics"
        elif operating_margin >= 0.15:
            s, pf, note = 8.0, "PASS", "Solid operating leverage"
        elif operating_margin >= 0.08:
            s, pf, note = 5.0, "WARN", "Average operations"
        else:
            s, pf, note = 2.0, "FAIL", "Weak operating returns"
        criteria.append(
            CriterionResult(
                "opm",
                "Operating Margin",
                operating_margin,
                f"{operating_margin * 100:.1f}%",
                s,
                1.0,
                pf,
                note,
            )
        )

    # 5. Current ratio — liquidity
    if current_ratio is None:
        criteria.append(
            CriterionResult("cr", "Current Ratio", None, "—", 4.0, 0.8, "N/A", "Missing liquidity data")
        )
    else:
        if current_ratio >= 2.0:
            s, pf, note = 9.0, "PASS", "Strong short-term liquidity"
        elif current_ratio >= 1.5:
            s, pf, note = 7.5, "PASS", "Adequate working capital"
        elif current_ratio >= 1.0:
            s, pf, note = 4.5, "WARN", "Tight liquidity"
        else:
            s, pf, note = 1.5, "FAIL", "Working-capital stress"
        criteria.append(
            CriterionResult("cr", "Current Ratio", current_ratio, f"{current_ratio:.2f}", s, 0.8, pf, note)
        )

    # 6. Free cash flow
    if fcf is None:
        criteria.append(
            CriterionResult("fcf", "Free Cash Flow", None, "—", 4.0, 1.3, "N/A", "Missing FCF")
        )
    else:
        if fcf > 0:
            # Scale by market cap when possible
            yield_ = (fcf / market_cap) if market_cap and market_cap > 0 else None
            if yield_ is not None and yield_ >= 0.05:
                s, pf, note = 10.0, "PASS", f"Owner earnings yield ~{yield_ * 100:.1f}%"
            elif yield_ is not None and yield_ >= 0.02:
                s, pf, note = 8.0, "PASS", f"Positive FCF yield ~{yield_ * 100:.1f}%"
            else:
                s, pf, note = 7.0, "PASS", "Positive free cash flow"
        else:
            s, pf, note = 1.0, "FAIL", "Cash burn — not owner-earnings friendly"
        criteria.append(
            CriterionResult("fcf", "Free Cash Flow", fcf, _fmt_num(fcf), s, 1.3, pf, note)
        )

    # 7. Earnings growth consistency
    if earnings_growth is None:
        criteria.append(
            CriterionResult("eg", "Earnings Growth", None, "—", 4.0, 1.0, "N/A", "Missing growth data")
        )
    else:
        if earnings_growth >= 0.12:
            s, pf, note = 9.0, "PASS", "Strong earnings trajectory"
        elif earnings_growth >= 0.05:
            s, pf, note = 7.0, "PASS", "Steady growth"
        elif earnings_growth >= 0:
            s, pf, note = 5.0, "WARN", "Flat / low growth"
        else:
            s, pf, note = 2.0, "FAIL", "Earnings contraction"
        criteria.append(
            CriterionResult(
                "eg",
                "Earnings Growth",
                earnings_growth,
                f"{earnings_growth * 100:.1f}%",
                s,
                1.0,
                pf,
                note,
            )
        )

    # 8. Valuation — P/E
    if pe is None or pe <= 0:
        criteria.append(
            CriterionResult("pe", "P/E (TTM)", pe, "—", 4.0, 1.2, "N/A", "No meaningful P/E")
        )
    else:
        # Prefer earnings yield vs bond; simple bands
        if pe <= 12:
            s, pf, note = 10.0, "PASS", "Cheap on earnings"
        elif pe <= 18:
            s, pf, note = 8.0, "PASS", "Reasonable multiple"
        elif pe <= 25:
            s, pf, note = 5.0, "WARN", "Full valuation"
        elif pe <= 40:
            s, pf, note = 3.0, "WARN", "Expensive — needs exceptional growth"
        else:
            s, pf, note = 1.0, "FAIL", "Speculative multiple"
        criteria.append(CriterionResult("pe", "P/E (TTM)", pe, f"{pe:.1f}x", s, 1.2, pf, note))

    # 9. Price / Book
    if pb is None or pb <= 0:
        criteria.append(
            CriterionResult("pb", "Price / Book", pb, "—", 4.0, 0.8, "N/A", "No P/B")
        )
    else:
        if pb <= 1.5:
            s, pf, note = 9.0, "PASS", "Close to tangible value"
        elif pb <= 3.0:
            s, pf, note = 7.0, "PASS", "Acceptable franchise premium"
        elif pb <= 6.0:
            s, pf, note = 4.5, "WARN", "High book premium"
        else:
            s, pf, note = 2.0, "FAIL", "Stretched vs book"
        criteria.append(CriterionResult("pb", "Price / Book", pb, f"{pb:.2f}x", s, 0.8, pf, note))

    # 10. ROA — asset efficiency
    if roa is None:
        criteria.append(
            CriterionResult("roa", "Return on Assets", None, "—", 3.0, 0.9, "N/A", "Missing ROA")
        )
    else:
        if roa >= 0.10:
            s, pf, note = 10.0, "PASS", "Highly productive assets"
        elif roa >= 0.06:
            s, pf, note = 7.5, "PASS", "Good asset returns"
        elif roa >= 0.03:
            s, pf, note = 5.0, "WARN", "Mediocre asset yield"
        else:
            s, pf, note = 2.0, "FAIL", "Low asset productivity"
        criteria.append(
            CriterionResult("roa", "Return on Assets", roa, f"{roa * 100:.1f}%", s, 0.9, pf, note)
        )

    total_weight = sum(c.weight for c in criteria)
    weighted = sum(c.score * c.weight for c in criteria)
    total_score = round((weighted / total_weight) * 10, 1) if total_weight else 0.0

    intrinsic = estimate_intrinsic_value(
        eps=eps,
        book_value=book,
        growth_rate=earnings_growth if earnings_growth is not None else revenue_growth,
        free_cash_flow=fcf,
        shares=shares,
    )
    mos = None
    if intrinsic is not None and price is not None and price > 0:
        mos = round(((intrinsic - price) / price) * 100, 1)
        # Slight score nudge for margin of safety
        if mos >= 25:
            total_score = min(100.0, round(total_score + 4, 1))
        elif mos >= 10:
            total_score = min(100.0, round(total_score + 2, 1))
        elif mos < -25:
            total_score = max(0.0, round(total_score - 4, 1))

    metrics = {
        "roe": roe,
        "roa": roa,
        "profitMargin": profit_margin,
        "operatingMargin": operating_margin,
        "grossMargin": gross_margin,
        "debtToEquity": debt_to_equity,
        "currentRatio": current_ratio,
        "pe": pe,
        "pb": pb,
        "peg": peg,
        "eps": eps,
        "bookValue": book,
        "freeCashflow": fcf,
        "earningsGrowth": earnings_growth,
        "revenueGrowth": revenue_growth,
        "dividendYield": dividend_yield,
        "payoutRatio": payout,
        "beta": beta,
        "marketCap": market_cap,
        "enterpriseToEbitda": enterprise_to_ebitda,
        "targetMeanPrice": target,
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "fiftyTwoWeekHigh": _safe(info.get("fiftyTwoWeekHigh")),
        "fiftyTwoWeekLow": _safe(info.get("fiftyTwoWeekLow")),
    }

    return BuffettAnalysis(
        symbol=symbol,
        name=name,
        market=market,
        currency=currency,
        price=price,
        total_score=total_score,
        grade=_grade(total_score),
        verdict=_verdict(total_score, mos),
        intrinsic_value=round(intrinsic, 2) if intrinsic is not None else None,
        margin_of_safety_pct=mos,
        criteria=criteria,
        metrics=metrics,
    )
