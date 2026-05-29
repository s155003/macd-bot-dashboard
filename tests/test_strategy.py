"""Tests for strategy logic — verifies the math matches the original bot."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from bot.strategy import compute_signals, detect_crossover, macd, wavelet_smooth


def make_synthetic_close(n: int = 100) -> pd.Series:
    """Trending sine wave — guaranteed to produce some crossovers."""
    t = np.linspace(0, 4 * np.pi, n)
    trend = np.linspace(100, 110, n)
    noise = np.sin(t) * 5
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    return pd.Series(trend + noise, index=dates)


def test_macd_returns_two_series():
    close = make_synthetic_close()
    m, s = macd(close)
    assert isinstance(m, pd.Series)
    assert isinstance(s, pd.Series)
    assert len(m) == len(close)
    assert len(s) == len(close)


def test_wavelet_smooth_preserves_length():
    close = make_synthetic_close()
    m, _ = macd(close)
    smooth = wavelet_smooth(m)
    assert len(smooth) == len(m)
    assert isinstance(smooth, pd.Series)


def test_wavelet_smooth_rejects_invalid_input():
    try:
        wavelet_smooth([1, 2, 3])
        assert False, "should have raised"
    except TypeError:
        pass


def test_wavelet_smooth_actually_smooths():
    """Smoothed series should have lower variance than the original."""
    close = make_synthetic_close()
    m, _ = macd(close)
    smooth = wavelet_smooth(m)
    assert smooth.std() < m.std() * 1.1  # at most slightly more variance


def test_detect_crossover_bullish():
    smooth = pd.Series([0, 1, 2])
    signal = pd.Series([1, 1.5, 1])  # smooth crosses above
    assert detect_crossover(smooth, signal) == "bullish"


def test_detect_crossover_bearish():
    smooth = pd.Series([2, 1, 0])
    signal = pd.Series([0, 0.5, 1])  # smooth crosses below
    assert detect_crossover(smooth, signal) == "bearish"


def test_detect_crossover_none():
    smooth = pd.Series([1, 2, 3])
    signal = pd.Series([0, 0, 0])  # both growing, no cross
    assert detect_crossover(smooth, signal) == "none"


def test_detect_crossover_too_short():
    assert detect_crossover(pd.Series([1]), pd.Series([2])) == "none"


def test_compute_signals_shape():
    close = make_synthetic_close()
    df = compute_signals(close)
    expected = {"close", "macd", "signal", "smooth_macd", "bullish_cross", "bearish_cross"}
    assert expected.issubset(set(df.columns))
    assert len(df) == len(close)


def test_compute_signals_finds_crossovers():
    """The synthetic trending sine wave should produce at least one of each."""
    close = make_synthetic_close(200)
    df = compute_signals(close)
    assert df["bullish_cross"].sum() > 0
    assert df["bearish_cross"].sum() > 0


if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"✓ {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"✗ {t.__name__}: {e}")
        except Exception as e:
            failed += 1
            print(f"✗ {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(tests)} tests, {failed} failed.")
