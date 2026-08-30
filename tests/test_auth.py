"""Auth module — JWT, password check, rate limiter."""
import pytest
from app.auth import create_token, decode_token, check_password, rate_ok


def _env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL",   "postgresql://u:p@h:5432/db")
    monkeypatch.setenv("SECRET_KEY",     "x" * 32)
    monkeypatch.setenv("ADMIN_PASSWORD", "adminpass")
    from app.config import get_settings
    get_settings.cache_clear()


def test_create_and_decode(monkeypatch):
    _env(monkeypatch)
    token = create_token("admin")
    assert isinstance(token, str) and len(token) > 20
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "admin"


def test_bad_token_returns_none(monkeypatch):
    _env(monkeypatch)
    assert decode_token("not.a.valid.jwt") is None
    assert decode_token("") is None


def test_expired_token_returns_none(monkeypatch):
    _env(monkeypatch)
    from datetime import datetime, timedelta, timezone
    import jwt as pyjwt
    from app.config import get_settings
    s = get_settings()
    expired = pyjwt.encode(
        {"sub": "admin", "exp": datetime.now(timezone.utc) - timedelta(hours=1)},
        s.secret_key, algorithm="HS256",
    )
    assert decode_token(expired) is None


def test_check_password_correct(monkeypatch):
    _env(monkeypatch)
    assert check_password("adminpass") is True


def test_check_password_wrong(monkeypatch):
    _env(monkeypatch)
    assert check_password("wrongpass") is False


def test_rate_limiter_passes_under_limit():
    key = f"test-unique-key-{id(test_rate_limiter_passes_under_limit)}"
    for _ in range(10):
        assert rate_ok(key) is True


def test_rate_limiter_blocks_over_limit():
    key = f"test-unique-key-{id(test_rate_limiter_blocks_over_limit)}"
    for _ in range(10):
        rate_ok(key)
    assert rate_ok(key) is False


def test_rate_limiter_different_keys_independent():
    k1 = "rate-key-alpha"
    k2 = "rate-key-beta"
    for _ in range(10):
        rate_ok(k1)
    # k1 is exhausted but k2 should still pass
    assert rate_ok(k2) is True
