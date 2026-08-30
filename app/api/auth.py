"""Authentication routes — login + rate limiting."""
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from app.auth import check_password, create_token, rate_ok

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request):
    # Rate-limit by client IP — prevents brute-force on the single admin password.
    ip = (request.client.host if request.client else None) or "unknown"
    if not rate_ok(f"login:{ip}"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please wait a minute.",
        )
    if not check_password(body.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password",
        )
    return TokenResponse(access_token=create_token())
