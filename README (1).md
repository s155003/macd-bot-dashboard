# 📈 MACD Wavelet Trading Bot · with Live Dashboard

The original Replit-ready trading bot, **plus a full web dashboard** to visualize what it's doing on Alpaca Markets — price charts with MACD signals, real-time decision log, account state, P&L, positions, and open orders.

## What's new

```
.
├── main.py                       # ← original bot (untouched, still works)
├── pyproject.toml
│
├── bot/                          # ← strategy logic, refactored for reuse
│   ├── strategy.py               #   pure functions: macd, wavelet_smooth, crossover
│   ├── config.py                 #   env-driven config
│   ├── store.py                  #   SQLite event log
│   └── runner.py                 #   bot loop with persistent logging
│
├── dashboard/                    # ← NEW: FastAPI + Plotly web UI
│   ├── server.py                 #   REST + WebSocket endpoints
│   ├── alpaca_client.py          #   account / positions / orders / equity
│   ├── chart_data.py             #   price + MACD signals → JSON
│   └── static/index.html         #   single-file dashboard (Plotly + terminal aesthetic)
│
├── tests/
│   ├── test_strategy.py          #   strategy math
│   ├── test_store.py             #   SQLite layer
│   └── test_server.py            #   FastAPI endpoints
│
├── Dockerfile                    # ← deployment
├── docker-compose.yml
├── .env.example
├── requirements.txt
└── run_dashboard.py              #   `python run_dashboard.py` → http://localhost:8000
```

## Dashboard features

- **Live price chart** — Yahoo Finance close, with bullish (▲) / bearish (▼) crossover markers, exactly where the bot would have traded.
- **MACD panel** — raw MACD, wavelet-smoothed MACD, and signal line on a second axis.
- **Equity curve** — fetched from Alpaca's portfolio history endpoint.
- **Account stats** — equity, day P&L (with %), buying power, cash. Color-coded green/red.
- **Open positions table** — unrealized P&L per symbol.
- **Recent orders table** — submitted/filled status with timestamps and avg fill price.
- **Bot decision log** — every check, every trade, every error, persisted in SQLite. Shows the crossover state, price at decision time, and reason for action (or inaction).
- **Bot controls** — start/stop the strategy loop in-process, or run a single iteration on demand.
- **WebSocket live updates** — new events push to the browser without polling.

## Local run (no Docker)

```bash
pip install -r requirements.txt

# Copy and fill in your Alpaca paper trading keys
cp .env.example .env
# Edit .env — or just export ALPACA_API_KEY / ALPACA_SECRET_KEY

# Launch the dashboard (serves on http://localhost:8000)
python run_dashboard.py
```

The dashboard works **without** Alpaca configured — you'll see the price chart and strategy signals, just no account data. Hit "Run once" to compute a decision and log it.

## Docker deployment

```bash
cp .env.example .env       # fill in your API keys
docker compose up -d --build
```

Then open http://localhost:8000.

The SQLite database lives in `./data/bot_state.db` (mounted as a volume), so events persist across container restarts. A health check pings `/api/config` every 30s.

## Original bot — still works

The original `main.py` is unchanged — you can still run it directly:

```bash
python main.py
```

It just won't log to SQLite or be visible in the dashboard. To get the new persistent logging in CLI mode, use:

```bash
python -m bot.runner
```

## Tests

```bash
python tests/test_strategy.py
python tests/test_store.py
python tests/test_server.py
```

## Strategy reference

Same as the original bot — based on the January 2025 paper *Optimizing MACD Trading Strategies: A Dance of Finance, Wavelets, and Genetics* (https://arxiv.org/abs/2501.10808). The paper applies wavelet transforms to denoise MACD signals, uses MACD divergence analysis, and optimizes parameters via a genetic algorithm. Backtests showed a ~5% annual return improvement and better Sharpe ratio.

## Configuration

All configuration is via environment variables (or `.env`):

| Variable | Default | Description |
|----------|---------|-------------|
| `ALPACA_API_KEY` | — | Required for live trading & account data |
| `ALPACA_SECRET_KEY` | — | Required for live trading & account data |
| `ALPACA_BASE_URL` | `https://paper-api.alpaca.markets` | Use paper trading URL by default |
| `BOT_SYMBOL` | `SPY` | Symbol to trade |
| `BOT_QTY` | `1` | Shares per trade |
| `BOT_INTERVAL_SEC` | `14400` | Strategy check interval (4 hours) |
| `BOT_LOOKBACK_DAYS` | `100` | Days of history to fetch |
| `BOT_DB_PATH` | `bot_state.db` | SQLite path for event log |
