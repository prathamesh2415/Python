# Buffett Terminal

Web-based value-investing desk inspired by Warren Buffett / Berkshire Hathaway principles.

## Features

- **Buffett Indicator** — Market Cap ÷ GDP for the US and India with valuation zones
- **Major indices** — S&P 500, Dow, Nasdaq, Russell, VIX, Nifty 50, Sensex, Nifty Bank, Nifty IT
- **Buffett Screener** — Scores US + NSE blue chips on ROE, leverage, margins, FCF, valuation
- **Stock Scorecard** — Checklist, intrinsic-value blend, margin of safety, 1Y chart

## Data

Fundamentals and quotes via [yfinance](https://github.com/ranaroussi/yfinance) (Yahoo Finance). Indian equities use NSE `.NS` symbols.

## Run locally

```bash
pip install -r requirements.txt
python run.py
```

Open http://127.0.0.1:8765

## API

| Endpoint | Description |
|----------|-------------|
| `GET /api/indices` | US & India index quotes |
| `GET /api/buffett-indicator` | Market Cap / GDP ratios |
| `GET /api/screen?market=both` | Ranked Buffett screen |
| `GET /api/analyze/{symbol}` | Full scorecard |
| `GET /api/search?q=` | Symbol search |

Not investment advice.
