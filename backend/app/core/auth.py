"""JWT / RBAC authentication (Phase 4), flag-gated.

Disabled by default (``AUTH_REQUIRED=False``) so existing endpoints and tests keep
working. When enabled, protected routes require a Bearer JWT and, optionally, a
role. Tokens are HS256 signed with ``JWT_SECRET_KEY``; a start-up guard forbids the
placeholder secret whenever auth is actually required.

Usage:
    @router.get("/admin", dependencies=[Depends(require_role("admin"))])

The dependency is a no-op passthrough while auth is disabled, so the same code runs
in both modes.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings, get_settings
from app.core.exceptions import ForbiddenError, UnauthorizedError

ROLES = ("viewer", "operator", "admin")
_ROLE_RANK = {r: i for i, r in enumerate(ROLES)}
_PLACEHOLDER_SECRET = "change-me-in-production"

_bearer = HTTPBearer(auto_error=False)


def create_access_token(
    subject: str, role: str = "viewer", settings: Settings | None = None
) -> str:
    s = settings or get_settings()
    if role not in ROLES:
        raise ValueError(f"unknown role: {role}")
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=s.JWT_EXPIRATION_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, s.JWT_SECRET_KEY, algorithm=s.JWT_ALGORITHM)


def decode_token(token: str, settings: Settings | None = None) -> dict:
    s = settings or get_settings()
    try:
        return jwt.decode(token, s.JWT_SECRET_KEY, algorithms=[s.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedError("token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedError("invalid token") from exc


def _principal_from_request(
    request: Request,
    creds: HTTPAuthorizationCredentials | None,
    settings: Settings,
) -> dict | None:
    """Return the decoded principal, or None when auth is disabled."""
    if not settings.AUTH_REQUIRED:
        return None  # auth off: passthrough
    if settings.JWT_SECRET_KEY == _PLACEHOLDER_SECRET:
        # Never enforce auth against the shipped placeholder secret.
        raise UnauthorizedError("auth is enabled but JWT_SECRET_KEY is the placeholder default")
    if creds is None or not creds.credentials:
        raise UnauthorizedError("missing Bearer token")
    return decode_token(creds.credentials, settings)


def get_current_principal(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    settings: Settings = Depends(get_settings),
) -> dict | None:
    return _principal_from_request(request, creds, settings)


def require_role(min_role: str = "viewer"):
    """Dependency enforcing at least ``min_role`` when auth is enabled."""
    if min_role not in _ROLE_RANK:
        raise ValueError(f"unknown role: {min_role}")

    def _dep(principal: dict | None = Depends(get_current_principal)) -> dict | None:
        if principal is None:  # auth disabled
            return None
        role = principal.get("role", "viewer")
        if _ROLE_RANK.get(role, -1) < _ROLE_RANK[min_role]:
            raise ForbiddenError(f"role '{role}' lacks required '{min_role}'")
        return principal

    return _dep
