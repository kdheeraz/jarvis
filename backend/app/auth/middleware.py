from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.service import decode_token
from app.config import get_config

_bearer_scheme = HTTPBearer(auto_error=False)


def require_admin(credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme)):
    """FastAPI dependency that enforces admin authentication.

    When auth is disabled in config, all requests are allowed through.
    """
    config = get_config()
    if not config.auth.enabled:
        return {"sub": "anonymous", "role": "admin"}

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
        )

    payload = decode_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    if payload.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    return payload
