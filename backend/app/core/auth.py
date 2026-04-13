"""SAML 2.0 SSO authentication + JWT for service-to-service."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings

settings = get_settings()
security = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# JWT helpers (service-to-service & session tokens)
# ---------------------------------------------------------------------------

def create_jwt_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.JWT_EXPIRE_MINUTES))
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_jwt_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


DEV_USER = {"sub": "dev", "email": "dev@localhost", "name": "Developer"}


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """Extract user from JWT Bearer token. Returns user dict or raises 401."""
    if settings.DEV_MODE:
        return DEV_USER
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return decode_jwt_token(credentials.credentials)


# ---------------------------------------------------------------------------
# SAML 2.0 helpers
# ---------------------------------------------------------------------------

def get_saml_settings() -> dict:
    """Load SAML SP settings from JSON file."""
    path = Path(settings.SAML_SETTINGS_PATH)
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def prepare_saml_request(request: Request) -> dict:
    """Build the request dict expected by python3-saml from a FastAPI request."""
    return {
        "https": "on" if request.url.scheme == "https" else "off",
        "http_host": request.url.hostname,
        "script_name": str(request.url.path),
        "get_data": dict(request.query_params),
        "post_data": {},
    }
