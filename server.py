"""
FastAPI server — REST API + WebSocket for live updates + static HTML dashboard.

Endpoints:
    GET  /                  → dashboard HTML
    GET  /api/account       → Alpaca account snapshot
    GET  /api/positions     → open positions
    GET  /api/orders        → recent orders
    GET  /api/equity        → equity curve
    GET  /api/chart         → price + MACD signals for charting
    GET  /api/events        → bot decision log from SQLite
    GET  /api/stats         → aggregate stats
    POST /api/bot/start     → start the strategy loop in-process
    POST /api/bot/stop      → stop it
    GET  /api/bot/status    → is it running?
    POST /api/bot/run-once  → run a single strategy iteration now
    WS   /ws                → push-based event stream
"""
import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse

from bot.config import CONFIG
from bot.runner import BotRunner, run_one_cycle, _make_api
from bot.store import Store
from dashboard.alpaca_client import (
    get_account,
    get_equity_history,
    get_positions,
    get_recent_orders,
)
from dashboard.chart_data import build_chart_data


# --- shared state ---
store = Store(CONFIG.db_path)
runner = BotRunner(store)


class ConnectionManager:
    """Tracks active WebSocket clients and broadcasts to them."""

    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, payload: dict):
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()
_last_event_id: int = 0


async def _poll_for_new_events():
    """Background task: notice when the bot writes a new event and push to clients."""
    global _last_event_id
    while True:
        try:
            events = store.recent_events(limit=5)
            if events:
                top_id = events[0]["id"]
                if top_id > _last_event_id:
                    new_events = [e for e in events if e["id"] > _last_event_id]
                    for e in reversed(new_events):
                        await manager.broadcast({"type": "event", "data": e})
                    _last_event_id = top_id
        except Exception:
            pass
        await asyncio.sleep(2)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _last_event_id
    events = store.recent_events(limit=1)
    if events:
        _last_event_id = events[0]["id"]
    poll_task = asyncio.create_task(_poll_for_new_events())
    yield
    poll_task.cancel()
    runner.stop()


app = FastAPI(title="MACD Bot Dashboard", lifespan=lifespan)


# --- HTML dashboard ---
@app.get("/")
async def index():
    return FileResponse(Path(__file__).parent / "static" / "index.html")


# --- Alpaca-backed endpoints ---
@app.get("/api/account")
async def api_account():
    return get_account()


@app.get("/api/positions")
async def api_positions():
    return get_positions()


@app.get("/api/orders")
async def api_orders(limit: int = 25):
    return get_recent_orders(limit=limit)


@app.get("/api/equity")
async def api_equity(period: str = "1M"):
    data = get_equity_history(period=period)
    if data is None:
        return JSONResponse({"available": False}, status_code=200)
    return {"available": True, **data}


# --- Strategy chart ---
@app.get("/api/chart")
async def api_chart(symbol: str = None, lookback_days: int = None):
    return build_chart_data(symbol=symbol, lookback_days=lookback_days)


# --- Bot event log (from SQLite) ---
@app.get("/api/events")
async def api_events(limit: int = 100):
    return store.recent_events(limit=limit)


@app.get("/api/stats")
async def api_stats():
    return store.stats()


@app.get("/api/config")
async def api_config():
    """Public-safe config snapshot — no secrets."""
    return {
        "symbol": CONFIG.symbol,
        "qty": CONFIG.qty,
        "interval_sec": CONFIG.trade_interval_sec,
        "lookback_days": CONFIG.lookback_days,
        "alpaca_configured": CONFIG.is_configured(),
        "base_url": CONFIG.base_url,
    }


# --- Bot control ---
@app.post("/api/bot/start")
async def api_bot_start():
    runner.start()
    return {"running": runner.is_running()}


@app.post("/api/bot/stop")
async def api_bot_stop():
    runner.stop()
    return {"running": runner.is_running()}


@app.get("/api/bot/status")
async def api_bot_status():
    return {"running": runner.is_running(), "interval_sec": runner.interval_sec}


@app.post("/api/bot/run-once")
async def api_bot_run_once():
    api = _make_api()
    event = run_one_cycle(api, store)
    return {"event": {
        "timestamp": event.timestamp,
        "kind": event.kind,
        "message": event.message,
        "crossover": event.crossover,
        "side": event.side,
    }}


# --- WebSocket ---
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        # Send initial snapshot
        await ws.send_json({
            "type": "snapshot",
            "data": {
                "stats": store.stats(),
                "events": store.recent_events(limit=20),
                "running": runner.is_running(),
            },
        })
        while True:
            await ws.receive_text()  # keepalive (ignore content)
    except WebSocketDisconnect:
        manager.disconnect(ws)


def main():
    """Entry point: `python -m dashboard.server` or `python run_dashboard.py`."""
    import uvicorn
    print("=" * 60)
    print("  MACD Bot Dashboard")
    print(f"  Symbol: {CONFIG.symbol}   Alpaca: "
          f"{'configured ✓' if CONFIG.is_configured() else 'NOT CONFIGURED'}")
    print(f"  Open in browser: http://127.0.0.1:8000")
    print("=" * 60)
    uvicorn.run("dashboard.server:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
