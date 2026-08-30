"""Smoke tests for critical routes via FastAPI TestClient."""
import pytest
from unittest.mock import AsyncMock, patch


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("DATABASE_URL",   "postgresql://u:p@h:5432/db")
    monkeypatch.setenv("SECRET_KEY",     "s" * 32)
    monkeypatch.setenv("ADMIN_PASSWORD", "testpw")
    from app.config import get_settings
    get_settings.cache_clear()

    with (
        patch("app.database.Database.connect",        new_callable=AsyncMock),
        patch("app.database.Database.disconnect",     new_callable=AsyncMock),
        patch("app.database.Database._init_schema",   new_callable=AsyncMock),
        patch("app.bot_manager.BotManager.start_all", new_callable=AsyncMock),
        patch("app.bot_manager.BotManager.stop_all",  new_callable=AsyncMock),
        patch("app.database.Database.get_active_bots",
              new_callable=AsyncMock, return_value=[]),
    ):
        from fastapi.testclient import TestClient
        import app.main as m
        yield TestClient(m.app, raise_server_exceptions=False)


# ── helpers ───────────────────────────────────────────────────────────────────
def _login(client) -> str:
    resp = client.post("/api/auth/login", json={"password": "testpw"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── tests ─────────────────────────────────────────────────────────────────────
def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "bots" in data


def test_docs_accessible(client):
    resp = client.get("/api/docs")
    assert resp.status_code == 200


def test_login_wrong_password(client):
    resp = client.post("/api/auth/login", json={"password": "wrong"})
    assert resp.status_code == 401


def test_login_correct_password(client):
    resp = client.post("/api/auth/login", json={"password": "testpw"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_protected_endpoint_without_token(client):
    resp = client.get("/api/bots")
    assert resp.status_code == 401


def test_protected_endpoint_with_bad_token(client):
    resp = client.get("/api/bots", headers={"Authorization": "Bearer garbage"})
    assert resp.status_code == 401


def test_protected_endpoint_with_good_token(client):
    token = _login(client)
    with patch("app.database.Database.get_all_bots",
               new_callable=AsyncMock, return_value=[]):
        resp = client.get("/api/bots", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json() == []


def test_stats_authenticated(client):
    token = _login(client)
    with patch("app.database.Database.get_all_stats",
               new_callable=AsyncMock,
               return_value={"total": 0, "texts": 0, "media": 0,
                             "chats": 0, "active_bots": 0, "mtproto_imported": 0}):
        resp = client.get("/api/stats", headers=_auth(token))
        assert resp.status_code == 200
        assert "total" in resp.json()


def test_rate_limit_on_login(client):
    # After 10 failed attempts the 11th should be 429
    for _ in range(10):
        client.post("/api/auth/login", json={"password": "wrong"})
    resp = client.post("/api/auth/login", json={"password": "testpw"})
    assert resp.status_code == 429


def test_spa_fallback_not_404_for_client_route(client):
    # No app/static in this test run, so main.py serves the JSON
    # "frontend not built yet" fallback for '/'. The important behavioral
    # guarantee — that an unmatched client-side route never 404s — is
    # exercised end-to-end (with real built assets) in the deploy validation
    # step; this test just guards against a regression to a hard 404 here.
    resp = client.get("/some/deep/link")
    assert resp.status_code != 404


def test_api_typo_still_404s(client):
    resp = client.get("/api/this-route-does-not-exist")
    assert resp.status_code == 404
