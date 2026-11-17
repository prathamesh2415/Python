"""Curated US and India equity universes for Buffett-style screening."""

from __future__ import annotations

US_BLUE_CHIPS: list[str] = [
    "AAPL",
    "MSFT",
    "BRK-B",
    "JNJ",
    "PG",
    "KO",
    "PEP",
    "WMT",
    "COST",
    "MCD",
    "V",
    "MA",
    "UNH",
    "JPM",
    "BAC",
    "XOM",
    "CVX",
    "HD",
    "DIS",
    "NKE",
    "AMD",
    "GOOGL",
    "AMZN",
    "META",
    "NVDA",
    "ORCL",
    "CRM",
    "IBM",
    "CSCO",
    "INTC",
    "T",
    "VZ",
    "PFE",
    "MRK",
    "ABBV",
    "LLY",
    "TMO",
    "ABT",
    "ACN",
    "TXN",
    "QCOM",
    "AVGO",
    "NEE",
    "DUK",
    "SO",
    "CAT",
    "DE",
    "GE",
    "BA",
    "UPS",
]

# NSE tickers — yfinance suffix .NS
INDIA_BLUE_CHIPS: list[str] = [
    "RELIANCE.NS",
    "TCS.NS",
    "INFY.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "HINDUNILVR.NS",
    "ITC.NS",
    "SBIN.NS",
    "BHARTIARTL.NS",
    "KOTAKBANK.NS",
    "LT.NS",
    "AXISBANK.NS",
    "BAJFINANCE.NS",
    "ASIANPAINT.NS",
    "MARUTI.NS",
    "SUNPHARMA.NS",
    "TITAN.NS",
    "WIPRO.NS",
    "HCLTECH.NS",
    "ULTRACEMCO.NS",
    "NESTLEIND.NS",
    "POWERGRID.NS",
    "NTPC.NS",
    "ONGC.NS",
    "TMPV.NS",  # Tata Motors (NSE)
    "TATASTEEL.NS",
    "JSWSTEEL.NS",
    "ADANIENT.NS",
    "ADANIPORTS.NS",
    "BAJAJFINSV.NS",
    "TECHM.NS",
    "CIPLA.NS",
    "DRREDDY.NS",
    "DIVISLAB.NS",
    "EICHERMOT.NS",
    "HEROMOTOCO.NS",
    "M&M.NS",
    "GRASIM.NS",
    "COALINDIA.NS",
    "BPCL.NS",
    "IOC.NS",
    "INDUSINDBK.NS",
    "HDFCLIFE.NS",
    "SBILIFE.NS",
    "BRITANNIA.NS",
    "DABUR.NS",
    "PIDILITIND.NS",
    "GODREJCP.NS",
    "HAVELLS.NS",
    "SIEMENS.NS",
]

US_INDICES: dict[str, str] = {
    "^GSPC": "S&P 500",
    "^DJI": "Dow Jones",
    "^IXIC": "Nasdaq Composite",
    "^RUT": "Russell 2000",
    "^VIX": "VIX Volatility",
}

INDIA_INDICES: dict[str, str] = {
    "^NSEI": "Nifty 50",
    "^BSESN": "Sensex",
    "^NSEBANK": "Nifty Bank",
    "^CNXIT": "Nifty IT",
}

# Approximate latest annual GDP (USD) for Buffett Indicator — updated periodically
US_GDP_USD: float = 28_780_000_000_000  # ~$28.78T (BEA 2024/25 ballpark)
INDIA_GDP_USD: float = 3_910_000_000_000  # ~$3.91T (IMF/World Bank ballpark)

# Proxy market-cap vehicles for total market approximation
US_MARKET_PROXY = "^W5000"  # Wilshire 5000 Full Cap (when available)
US_MARKET_FALLBACK = "VTI"  # Vanguard Total Stock Market ETF
INDIA_MARKET_PROXY = "^CRSLDX"  # Nifty 500 / Total Market proxies vary
INDIA_NIFTY50 = "^NSEI"


def normalize_symbol(raw: str, market: str | None = None) -> str:
    """Normalize user input to a yfinance symbol."""
    s = raw.strip().upper().replace(" ", "")
    if not s:
        return s
    if "." in s or s.startswith("^"):
        return s
    if market and market.lower() in {"in", "india", "nse", "bse"}:
        if not s.endswith(".NS") and not s.endswith(".BO"):
            return f"{s}.NS"
    return s


def market_of(symbol: str) -> str:
    if symbol.endswith(".NS") or symbol.endswith(".BO"):
        return "IN"
    if symbol.startswith("^NSE") or symbol.startswith("^BSE") or symbol.startswith("^CNX"):
        return "IN"
    return "US"
