"""JWT creation + verification + password check + login rate limiting."""
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from jwt.exceptions import InvalidTokenError
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import get_settings

_bearer   = HTTPBearer(auto_error=False)
ALGORITHM = "HS256"

# ── Login rate limiter (in-process sliding window) ────────────────────────────
# Single-admin auth model → 10 attempts per 60 seconds per IP is plenty.
_attempts:  dict[str, deque] = defaultdict(deque)
_WINDOW = 60    # seconds
_MAX    = 10    # max attempts per window


def rate_ok(key: str) -> bool:
    """Return True and record the attempt; False if the window is full."""
    now = time.monotonic()
    dq  = _attempts[key]
    while dq and dq[0] < now - _WINDOW:
        dq.popleft()
    if len(dq) >= _MAX:
        return False
    dq.append(now)
    return True


# ── Password ──────────────────────────────────────────────────────────────────
def check_password(plain: str) -> bool:
    return secrets.compare_digest(
        plain.encode(), get_settings().admin_password.encode()
    )


# ── JWT ───────────────────────────────────────────────────────────────────────
def create_token(sub: str = "admin") -> str:
    s   = get_settings()
    exp = datetime.now(timezone.utc) + timedelta(hours=s.jwt_expire_hours)
    return jwt.encode({"sub": sub, "exp": exp}, s.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(
            token, get_settings().secret_key, algorithms=[ALGORITHM]
        )
    except InvalidTokenError:
        return None


# ── FastAPI dependencies ──────────────────────────────────────────────────────
def require_auth(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> str:
    """Standard Bearer-header auth for JSON API endpoints."""
    if not creds:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing token")
    payload = decode_token(creds.credentials)
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    return payload["sub"]


def require_auth_or_query(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    token: Optional[str] = Query(None),
) -> str:
    """Bearer header OR ?token= query param.

    Used for endpoints that the browser hits via direct link (file downloads,
    CSV/JSON/XLSX exports) where the fetch API can't inject a custom header.
    """
    raw = (creds.credentials if creds else None) or token
    if not raw:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing token")
    payload = decode_token(raw)
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    return payload["sub"]
