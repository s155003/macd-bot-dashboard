"""Tests for the SQLite event store."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bot.store import BotEvent, Store


def make_store():
    f = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    f.close()
    return Store(f.name), f.name


def test_log_and_read_event():
    store, _ = make_store()
    ev = BotEvent(
        timestamp="2026-01-01T12:00:00", kind="check", symbol="SPY",
        message="testing", crossover="none", price=400.0,
    )
    rid = store.log_event(ev)
    assert rid > 0
    events = store.recent_events(limit=10)
    assert len(events) == 1
    assert events[0]["symbol"] == "SPY"
    assert events[0]["price"] == 400.0


def test_recent_events_orders_newest_first():
    store, _ = make_store()
    for i in range(5):
        store.log_event(BotEvent(
            timestamp=f"2026-01-0{i+1}T00:00:00",
            kind="check", symbol="SPY", message=f"msg {i}",
        ))
    events = store.recent_events(limit=3)
    assert len(events) == 3
    assert events[0]["message"] == "msg 4"
    assert events[2]["message"] == "msg 2"


def test_trades_filter():
    store, _ = make_store()
    store.log_event(BotEvent(timestamp="t1", kind="check", symbol="SPY", message="x"))
    store.log_event(BotEvent(timestamp="t2", kind="trade", symbol="SPY",
                             message="bought", side="buy", qty=1))
    store.log_event(BotEvent(timestamp="t3", kind="error", symbol="SPY", message="oops"))

    trades = store.trades()
    assert len(trades) == 1
    assert trades[0]["side"] == "buy"


def test_stats():
    store, _ = make_store()
    store.log_event(BotEvent(timestamp="t1", kind="check", symbol="SPY", message=""))
    store.log_event(BotEvent(timestamp="t2", kind="trade", symbol="SPY", message="", side="buy"))
    store.log_event(BotEvent(timestamp="t3", kind="trade", symbol="SPY", message="", side="sell"))
    store.log_event(BotEvent(timestamp="t4", kind="error", symbol="SPY", message=""))

    s = store.stats()
    assert s["total_events"] == 4
    assert s["buys"] == 1
    assert s["sells"] == 1
    assert s["errors"] == 1
    assert s["last_check"] == "t1"


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
