"""Smoke tests for the FastAPI server — uses TestClient (no real network)."""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Use isolated DB so tests don't pollute real state
_tmp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
_tmp_db.close()
os.environ["BOT_DB_PATH"] = _tmp_db.name

from fastapi.testclient import TestClient

from dashboard.server import app


client = TestClient(app)


def test_index_serves_html():
    r = client.get("/")
    assert r.status_code == 200
    assert "macd" in r.text.lower()


def test_config_endpoint():
    r = client.get("/api/config")
    assert r.status_code == 200
    body = r.json()
    assert "symbol" in body
    assert "alpaca_configured" in body
    # Without env vars set, should be False
    assert body["alpaca_configured"] is False


def test_account_unconfigured():
    """When no API key set, should return configured: False — not crash."""
    r = client.get("/api/account")
    assert r.status_code == 200
    body = r.json()
    assert body["configured"] is False


def test_positions_returns_list():
    r = client.get("/api/positions")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_orders_returns_list():
    r = client.get("/api/orders")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_events_initially_empty():
    r = client.get("/api/events")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_stats_endpoint():
    r = client.get("/api/stats")
    assert r.status_code == 200
    body = r.json()
    assert "total_events" in body


def test_bot_status():
    r = client.get("/api/bot/status")
    assert r.status_code == 200
    assert "running" in r.json()


def test_equity_unconfigured_returns_unavailable():
    r = client.get("/api/equity")
    assert r.status_code == 200
    body = r.json()
    assert body.get("available") is False


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
