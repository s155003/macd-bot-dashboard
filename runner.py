"""
Bot runner — same strategy as main.py, but logs every decision to SQLite
so the dashboard can show what's happening.

Can be invoked directly OR run as a background thread by the dashboard.
"""
import time
import threading
from datetime import datetime

import pandas as pd
import yfinance as yf

from bot.config import CONFIG
from bot.store import BotEvent, Store
from bot.strategy import detect_crossover, macd, wavelet_smooth


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def get_price_data(symbol: str, lookback_days: int = 100) -> pd.DataFrame:
    df = yf.download(
        symbol, period=f"{lookback_days}d", interval="1d",
        progress=False, auto_adjust=False,
    )
    if df.empty:
        raise ValueError(f"YFinance returned no data for symbol: {symbol}")
    if "Close" not in df.columns:
        raise ValueError(f"'Close' column missing for symbol: {symbol}")
    return df[["Close"]].dropna()


def get_position(api, symbol: str) -> int:
    try:
        pos = api.get_position(symbol)
        return int(pos.qty)
    except Exception:
        return 0


def place_trade(api, symbol: str, side: str, qty: int) -> bool:
    try:
        api.submit_order(
            symbol=symbol, qty=qty, side=side,
            type="market", time_in_force="gtc",
        )
        return True
    except Exception as e:
        print(f"[{_now_iso()}] Trade failed: {e}")
        return False


def run_one_cycle(api, store: Store) -> BotEvent:
    """Run a single strategy iteration and log the result."""
    symbol = CONFIG.symbol
    try:
        df = get_price_data(symbol, CONFIG.lookback_days)
        macd_line, signal_line = macd(df["Close"])
        macd_line = pd.Series(macd_line)
        signal_line = pd.Series(signal_line)
        smooth = wavelet_smooth(macd_line)

        cross = detect_crossover(smooth, signal_line)
        last_price = float(df["Close"].iloc[-1])
        position = get_position(api, symbol) if api else 0

        event = BotEvent(
            timestamp=_now_iso(),
            kind="check",
            symbol=symbol,
            message="",
            macd_value=float(macd_line.iloc[-1]),
            signal_value=float(signal_line.iloc[-1]),
            smooth_macd_value=float(smooth.iloc[-1]),
            price=last_price,
            crossover=cross,
        )

        if cross == "bullish" and position == 0:
            ok = place_trade(api, symbol, "buy", CONFIG.qty) if api else False
            event.kind = "trade"
            event.side = "buy"
            event.qty = CONFIG.qty
            event.message = (f"BUY {CONFIG.qty} {symbol} @ ~${last_price:.2f}"
                             if ok else "BUY signal but order failed")
        elif cross == "bearish" and position > 0:
            ok = place_trade(api, symbol, "sell", CONFIG.qty) if api else False
            event.kind = "trade"
            event.side = "sell"
            event.qty = CONFIG.qty
            event.message = (f"SELL {CONFIG.qty} {symbol} @ ~${last_price:.2f}"
                             if ok else "SELL signal but order failed")
        else:
            event.message = (
                f"No action — crossover={cross}, position={position}"
            )

        store.log_event(event)
        return event

    except Exception as e:
        err = BotEvent(
            timestamp=_now_iso(), kind="error", symbol=symbol,
            message=f"{type(e).__name__}: {e}",
        )
        store.log_event(err)
        return err


def _make_api():
    """Build an Alpaca client if configured, otherwise return None."""
    if not CONFIG.is_configured():
        return None
    try:
        from alpaca_trade_api.rest import REST
        return REST(CONFIG.api_key, CONFIG.secret_key, CONFIG.base_url)
    except Exception as e:
        print(f"Could not create Alpaca client: {e}")
        return None


class BotRunner:
    """Runs the strategy loop in a background thread."""

    def __init__(self, store: Store, interval_sec: int = None):
        self.store = store
        self.interval_sec = interval_sec or CONFIG.trade_interval_sec
        self._stop = threading.Event()
        self._thread: threading.Thread = None
        self.api = _make_api()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _loop(self) -> None:
        while not self._stop.is_set():
            run_one_cycle(self.api, self.store)
            # Sleep in small chunks so stop() responds quickly
            for _ in range(self.interval_sec):
                if self._stop.is_set():
                    return
                time.sleep(1)


def main() -> None:
    """Standalone bot runner — same behavior as the original main.py
    but with persistent logging."""
    store = Store(CONFIG.db_path)
    api = _make_api()
    if api is None:
        print("⚠️  ALPACA_API_KEY / ALPACA_SECRET_KEY not set — running in dry mode "
              "(strategy will compute, but no orders will be placed).")
    print(f"Starting bot for {CONFIG.symbol}, interval={CONFIG.trade_interval_sec}s")
    while True:
        ev = run_one_cycle(api, store)
        print(f"[{ev.timestamp}] {ev.kind.upper()}: {ev.message}")
        time.sleep(CONFIG.trade_interval_sec)


if __name__ == "__main__":
    main()
