"""
SQLite-backed storage for bot events and trades.

The bot writes to this; the dashboard reads from it. SQLite is fine
for one writer + many readers and means the dashboard works even
if the bot crashed — you still have history.
"""
import json
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class BotEvent:
    """A decision or action the bot took."""
    timestamp: str
    kind: str          # 'check', 'trade', 'error'
    symbol: str
    message: str
    macd_value: Optional[float] = None
    signal_value: Optional[float] = None
    smooth_macd_value: Optional[float] = None
    price: Optional[float] = None
    crossover: Optional[str] = None  # 'bullish', 'bearish', 'none'
    side: Optional[str] = None       # 'buy', 'sell', None
    qty: Optional[int] = None


SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    kind TEXT NOT NULL,
    symbol TEXT NOT NULL,
    message TEXT NOT NULL,
    macd_value REAL,
    signal_value REAL,
    smooth_macd_value REAL,
    price REAL,
    crossover TEXT,
    side TEXT,
    qty INTEGER
);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(timestamp);
CREATE INDEX IF NOT EXISTS idx_events_kind ON events(kind);
"""


class Store:
    def __init__(self, path: str):
        self.path = path
        self._init_db()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._conn() as c:
            c.executescript(SCHEMA)

    def log_event(self, event: BotEvent) -> int:
        with self._conn() as c:
            cur = c.execute(
                """INSERT INTO events
                   (timestamp, kind, symbol, message, macd_value, signal_value,
                    smooth_macd_value, price, crossover, side, qty)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (event.timestamp, event.kind, event.symbol, event.message,
                 event.macd_value, event.signal_value, event.smooth_macd_value,
                 event.price, event.crossover, event.side, event.qty),
            )
            return cur.lastrowid

    def recent_events(self, limit: int = 100) -> List[dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def trades(self, limit: int = 100) -> List[dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM events WHERE kind='trade' ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def stats(self) -> dict:
        """High-level counts for the dashboard summary."""
        with self._conn() as c:
            total = c.execute("SELECT COUNT(*) AS n FROM events").fetchone()["n"]
            buys = c.execute(
                "SELECT COUNT(*) AS n FROM events WHERE kind='trade' AND side='buy'"
            ).fetchone()["n"]
            sells = c.execute(
                "SELECT COUNT(*) AS n FROM events WHERE kind='trade' AND side='sell'"
            ).fetchone()["n"]
            errors = c.execute(
                "SELECT COUNT(*) AS n FROM events WHERE kind='error'"
            ).fetchone()["n"]
            last_check = c.execute(
                "SELECT timestamp FROM events WHERE kind='check' ORDER BY id DESC LIMIT 1"
            ).fetchone()
            return {
                "total_events": total,
                "buys": buys,
                "sells": sells,
                "errors": errors,
                "last_check": last_check["timestamp"] if last_check else None,
            }
