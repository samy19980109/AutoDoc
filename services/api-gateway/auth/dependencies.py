"""Authentication and authorization dependencies for the API Gateway."""

from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer

from common.config import get_settings

settings = get_settings()

api_key_header_scheme = APIKeyHeader(name=settings.api_key_header, auto_error=False)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


def _get_valid_api_keys() -> list[str]:
    """Parse the comma-separated API keys from settings."""
    if not settings.api_keys:
        return []
    return [k.strip() for k in settings.api_keys.split(",") if k.strip()]


async def verify_api_key(
    api_key: Optional[str] = Depends(api_key_header_scheme),
    token: Optional[str] = Depends(oauth2_scheme),
) -> str:
    """Verify the request carries a valid API key or JWT token.

    Accepts either:
    - An API key via the X-API-Key header
    - A JWT bearer token via the Authorization header

    Returns the identity string (the API key or the JWT subject).
    """
    # Try API key first
    if api_key:
        valid_keys = _get_valid_api_keys()
        if valid_keys and api_key in valid_keys:
            return api_key
        if not valid_keys:
            # No keys configured -- open access (dev mode)
            return api_key

    # Try JWT bearer token
    if token:
        payload = verify_token(token)
        if payload is not None:
            return payload.get("sub", "dashboard-user")

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT access token."""
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {
        "sub": subject,
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(payload, settings.api_secret_key, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> Optional[dict]:
    """Decode and verify a JWT token. Returns the payload dict or None."""
    try:
        payload = jwt.decode(token, settings.api_secret_key, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None
