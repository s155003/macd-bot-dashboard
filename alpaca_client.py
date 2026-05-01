"""
Pulls account state from Alpaca.

Returns plain dicts (JSON-friendly). All calls are wrapped to fail
gracefully — if Alpaca is unreachable or unconfigured, the dashboard
still renders.
"""
from typing import List, Optional

from bot.config import CONFIG


def _make_api():
    if not CONFIG.is_configured():
        return None
    try:
        from alpaca_trade_api.rest import REST
        return REST(CONFIG.api_key, CONFIG.secret_key, CONFIG.base_url)
    except Exception:
        return None


def get_account() -> dict:
    """Equity, buying power, cash, P&L for today."""
    api = _make_api()
    if api is None:
        return {"configured": False}
    try:
        a = api.get_account()
        equity = float(a.equity)
        last_equity = float(a.last_equity)
        return {
            "configured": True,
            "status": a.status,
            "equity": equity,
            "last_equity": last_equity,
            "cash": float(a.cash),
            "buying_power": float(a.buying_power),
            "day_pnl": equity - last_equity,
            "day_pnl_pct": ((equity - last_equity) / last_equity * 100)
                          if last_equity else 0.0,
            "currency": a.currency,
        }
    except Exception as e:
        return {"configured": True, "error": f"{type(e).__name__}: {e}"}


def get_positions() -> List[dict]:
    """Open positions with unrealized P&L."""
    api = _make_api()
    if api is None:
        return []
    try:
        positions = api.list_positions()
        out = []
        for p in positions:
            out.append({
                "symbol": p.symbol,
                "qty": float(p.qty),
                "side": p.side,
                "avg_entry_price": float(p.avg_entry_price),
                "current_price": float(p.current_price) if p.current_price else None,
                "market_value": float(p.market_value),
                "unrealized_pl": float(p.unrealized_pl),
                "unrealized_plpc": float(p.unrealized_plpc) * 100,
            })
        return out
    except Exception:
        return []


def get_recent_orders(limit: int = 25) -> List[dict]:
    """Recent orders (filled, pending, canceled)."""
    api = _make_api()
    if api is None:
        return []
    try:
        orders = api.list_orders(status="all", limit=limit)
        out = []
        for o in orders:
            out.append({
                "symbol": o.symbol,
                "side": o.side,
                "qty": float(o.qty),
                "filled_qty": float(o.filled_qty) if o.filled_qty else 0,
                "type": o.type,
                "status": o.status,
                "submitted_at": str(o.submitted_at) if o.submitted_at else None,
                "filled_avg_price": float(o.filled_avg_price)
                                    if o.filled_avg_price else None,
            })
        return out
    except Exception:
        return []


def get_equity_history(period: str = "1M") -> Optional[dict]:
    """Equity curve from portfolio history endpoint."""
    api = _make_api()
    if api is None:
        return None
    try:
        ph = api.get_portfolio_history(period=period, timeframe="1D")
        return {
            "timestamps": list(ph.timestamp) if ph.timestamp else [],
            "equity": list(ph.equity) if ph.equity else [],
            "profit_loss": list(ph.profit_loss) if ph.profit_loss else [],
        }
    except Exception:
        return None
