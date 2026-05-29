"""
Strategy logic — pure functions extracted from main.py.

These are imported by both the bot loop and the dashboard so the
chart shows EXACTLY what the bot is computing.
"""
from typing import Tuple

import numpy as np
import pandas as pd
import pywt


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
         ) -> Tuple[pd.Series, pd.Series]:
    """Compute MACD and signal line from a close-price series."""
    fast_ema = close.ewm(span=fast, adjust=False).mean()
    slow_ema = close.ewm(span=slow, adjust=False).mean()
    macd_line = (fast_ema - slow_ema).squeeze()
    signal_line = macd_line.ewm(span=signal, adjust=False).mean().squeeze()
    return macd_line, signal_line


def wavelet_smooth(series: pd.Series, wavelet: str = "db4") -> pd.Series:
    """Apply wavelet denoising — zeroes out detail coefficients."""
    if not isinstance(series, pd.Series):
        raise TypeError("Input to wavelet_smooth must be a pandas Series.")
    if series.isnull().any() or series.empty:
        raise ValueError("Invalid input series to wavelet_smooth.")

    # pywt requires a writable array — pandas Series can sometimes back to read-only buffers
    arr = np.asarray(series.values, dtype=float).copy()
    coeffs = pywt.wavedec(arr, wavelet)
    coeffs[1:] = [np.zeros_like(c) for c in coeffs[1:]]
    smooth = pywt.waverec(coeffs, wavelet)
    return pd.Series(smooth[:len(series)], index=series.index)


def detect_crossover(smooth_macd: pd.Series, signal_line: pd.Series) -> str:
    """
    Look at the last two bars and classify the crossover.
    Returns one of: 'bullish', 'bearish', 'none'.
    """
    if len(smooth_macd) < 2 or len(signal_line) < 2:
        return "none"
    prev_diff = smooth_macd.iloc[-2] - signal_line.iloc[-2]
    curr_diff = smooth_macd.iloc[-1] - signal_line.iloc[-1]
    if prev_diff < 0 and curr_diff > 0:
        return "bullish"
    if prev_diff > 0 and curr_diff < 0:
        return "bearish"
    return "none"


def compute_signals(close: pd.Series) -> pd.DataFrame:
    """
    Compute MACD, signal, smoothed MACD, and crossover markers across
    the whole series. Used by the dashboard for charting.
    """
    macd_line, signal_line = macd(close)
    smooth = wavelet_smooth(macd_line)
    diff = smooth - signal_line
    prev_diff = diff.shift(1)

    bullish = (prev_diff < 0) & (diff > 0)
    bearish = (prev_diff > 0) & (diff < 0)

    return pd.DataFrame({
        "close": close,
        "macd": macd_line,
        "signal": signal_line,
        "smooth_macd": smooth,
        "bullish_cross": bullish,
        "bearish_cross": bearish,
    })
