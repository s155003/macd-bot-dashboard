"""Build Plotly-friendly chart payloads from price data + strategy signals."""
from typing import Dict

import pandas as pd
import yfinance as yf

from bot.config import CONFIG
from bot.strategy import compute_signals


def build_chart_data(symbol: str = None, lookback_days: int = None) -> Dict:
    """Fetch price history and compute MACD signals → JSON for Plotly."""
    symbol = symbol or CONFIG.symbol
    lookback_days = lookback_days or CONFIG.lookback_days

    df = yf.download(
        symbol, period=f"{lookback_days}d", interval="1d",
        progress=False, auto_adjust=False,
    )
    if df.empty:
        return {"error": f"No data for {symbol}", "symbol": symbol}

    # yfinance can return a MultiIndex column on newer versions
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]

    close = df["Close"].dropna()
    sig = compute_signals(close)

    dates = [d.strftime("%Y-%m-%d") for d in sig.index]

    bullish_idx = sig.index[sig["bullish_cross"]]
    bearish_idx = sig.index[sig["bearish_cross"]]

    return {
        "symbol": symbol,
        "lookback_days": lookback_days,
        "dates": dates,
        "close": [float(x) for x in sig["close"].tolist()],
        "macd": [float(x) for x in sig["macd"].tolist()],
        "signal": [float(x) for x in sig["signal"].tolist()],
        "smooth_macd": [float(x) for x in sig["smooth_macd"].tolist()],
        "bullish_dates": [d.strftime("%Y-%m-%d") for d in bullish_idx],
        "bullish_prices": [float(sig.loc[d, "close"]) for d in bullish_idx],
        "bearish_dates": [d.strftime("%Y-%m-%d") for d in bearish_idx],
        "bearish_prices": [float(sig.loc[d, "close"]) for d in bearish_idx],
        "current_price": float(close.iloc[-1]),
        "current_macd": float(sig["macd"].iloc[-1]),
        "current_signal": float(sig["signal"].iloc[-1]),
        "current_smooth": float(sig["smooth_macd"].iloc[-1]),
    }
