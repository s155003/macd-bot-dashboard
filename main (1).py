import numpy as np
import pandas as pd
import pywt
import yfinance as yf
import time
import os
from datetime import datetime
from alpaca_trade_api.rest import REST

# === Load API Keys from Replit Secrets or .env ===
API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
BASE_URL = "https://paper-api.alpaca.markets"

# === Config ===
SYMBOL = 'SPY'  # Change to any valid symbol (e.g., 'AAPL', 'QQQ', etc.)
QTY = 1
TRADE_INTERVAL = 60 * 60 * 4  # every 4 hours

# === Alpaca Connection ===
api = REST(API_KEY, SECRET_KEY, BASE_URL)

# === Get price data from Yahoo Finance ===
def get_price_data(symbol='SPY', lookback_days=100):
    df = yf.download(symbol, period=f'{lookback_days}d', interval='1d', progress=False, auto_adjust=False)

    if df.empty:
        raise ValueError(f"❌ YFinance returned no data for symbol: {symbol}")

    if 'Close' not in df.columns:
        raise ValueError(f"❌ 'Close' column not found in data for symbol: {symbol}")

    df = df[['Close']].dropna()
    print(f"📊 Got {len(df)} days of data for {symbol}")
    return df

# === MACD Calculation (fixed to return Series) ===
def macd(df, fast=12, slow=26, signal=9):
    fast_ema = df['Close'].ewm(span=fast, adjust=False).mean()
    slow_ema = df['Close'].ewm(span=slow, adjust=False).mean()
    macd_line = (fast_ema - slow_ema).squeeze()
    signal_line = macd_line.ewm(span=signal, adjust=False).mean().squeeze()
    return macd_line, signal_line

# === Final Wavelet Smoothing ===
def wavelet_smooth(series, wavelet='db4'):
    if not isinstance(series, pd.Series):
        raise TypeError("Input to wavelet_smooth must be a pandas Series.")
    if series.isnull().any() or series.empty:
        raise ValueError("Invalid input series to wavelet_smooth.")

    coeffs = pywt.wavedec(series, wavelet)
    coeffs[1:] = [np.zeros_like(c) for c in coeffs[1:]]
    smooth = pywt.waverec(coeffs, wavelet)

    return pd.Series(smooth[:len(series)], index=series.index)

# === Get Current Position ===
def get_position(symbol):
    try:
        pos = api.get_position(symbol)
        return int(pos.qty)
    except:
        return 0

# === Place a Trade ===
def trade(symbol, side, qty):
    try:
        api.submit_order(
            symbol=symbol,
            qty=qty,
            side=side,
            type='market',
            time_in_force='gtc'
        )
        print(f"[{datetime.now()}] ✅ Executed {side.upper()} order for {qty} {symbol}")
    except Exception as e:
        print(f"❌ Trade failed: {e}")

# === Strategy Core ===
def run_strategy():
    print(f"[{datetime.now()}] Running strategy...")
    try:
        df = get_price_data(SYMBOL)
        macd_line, signal_line = macd(df)

        # Convert to Series just to be safe
        macd_line = pd.Series(macd_line)
        signal_line = pd.Series(signal_line)

        smooth_macd = wavelet_smooth(macd_line)

        prev_diff = smooth_macd.iloc[-2] - signal_line.iloc[-2]
        curr_diff = smooth_macd.iloc[-1] - signal_line.iloc[-1]

        position = get_position(SYMBOL)

        if prev_diff < 0 and curr_diff > 0 and position == 0:
            trade(SYMBOL, 'buy', QTY)

        elif prev_diff > 0 and curr_diff < 0 and position > 0:
            trade(SYMBOL, 'sell', QTY)

        else:
            print(f"[{datetime.now()}] 📉 No crossover. Holding...")

    except Exception as e:
        print(f"Runtime error: {e}")

# === Main Loop ===
if __name__ == '__main__':
    while True:
        run_strategy()
        time.sleep(TRADE_INTERVAL)
