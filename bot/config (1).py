"""Centralized config — read from env vars."""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    api_key: str = os.getenv("ALPACA_API_KEY", "")
    secret_key: str = os.getenv("ALPACA_SECRET_KEY", "")
    base_url: str = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
    symbol: str = os.getenv("BOT_SYMBOL", "SPY")
    qty: int = int(os.getenv("BOT_QTY", "1"))
    trade_interval_sec: int = int(os.getenv("BOT_INTERVAL_SEC", str(60 * 60 * 4)))
    lookback_days: int = int(os.getenv("BOT_LOOKBACK_DAYS", "100"))
    db_path: str = os.getenv("BOT_DB_PATH", "bot_state.db")

    def is_configured(self) -> bool:
        return bool(self.api_key and self.secret_key)


CONFIG = Config()
