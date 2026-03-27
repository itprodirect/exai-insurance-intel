"""Auth, rate limiting, and boundary controls for the pilot API.

Configuration via environment variables:

    PILOT_API_KEY              Shared secret for bearer auth. If unset, auth is disabled.
    PILOT_USERS                JSON mapping of user_id → api_key for multi-user mode.
                               Example: {"alice": "key-alice", "bob": "key-bob"}
                               Takes precedence over PILOT_API_KEY when set.
    PILOT_OPS_USERS            Comma-separated user_ids allowed to access ops/admin
                               surfaces like /api/runs and /api/ops/summary.
                               Defaults to "pilot".
    PILOT_RATE_LIMIT_PER_MIN   Max requests per minute per client (default: 60).
    PILOT_ALLOW_LIVE_MODE      Set to "1" to allow live/auto modes (default: smoke only).
    PILOT_MAX_RESULTS          Max num_results per request (default: 25).
    PILOT_MAX_QUERY_LENGTH     Max query string length (default: 1000).
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from collections import defaultdict
from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger("exa_demo.api")

# ---------------------------------------------------------------------------
# Auth + user identity
# ---------------------------------------------------------------------------

VALID_MODES = frozenset({"smoke", "live", "auto"})

# Default user ID when auth is disabled or single-key mode is used.
DEFAULT_USER_ID = "pilot"


def _pilot_api_key() -> str:
    return os.environ.get("PILOT_API_KEY", "").strip()


def _pilot_users() -> dict[str, str]:
    """Parse PILOT_USERS env var (JSON: {"user_id": "api_key", ...}).

    Returns an empty dict when unset or invalid.
    """
    raw = os.environ.get("PILOT_USERS", "").strip()
    if not raw:
        return {}
    try:
        mapping = json.loads(raw)
        if isinstance(mapping, dict):
            return {str(k): str(v) for k, v in mapping.items()}
    except (json.JSONDecodeError, TypeError):
        logger.warning("PILOT_USERS is set but not valid JSON; ignoring")
    return {}


def require_api_key(request: Request) -> str | None:
    """FastAPI dependency.  Validates bearer token and resolves user identity.

    Multi-user mode (PILOT_USERS set):
        Looks up the bearer token in the user→key mapping.
        Sets ``request.state.user_id`` to the matched user.

    Single-key mode (only PILOT_API_KEY set):
        Validates token against the shared key.
        Sets ``request.state.user_id`` to DEFAULT_USER_ID ("pilot").

    No auth (neither set):
        Sets ``request.state.user_id`` to DEFAULT_USER_ID.
        Returns None.
    """
    users = _pilot_users()
    if users:
        # Multi-user mode: resolve user from per-user key.
        auth = request.headers.get("authorization", "")
        if not auth.lower().startswith("bearer "):
            raise HTTPException(
                status_code=401,
                detail="Missing or invalid Authorization header. "
                "Use: Authorization: Bearer <api-key>",
            )
        token = auth[7:].strip()
        # Reverse lookup: find user_id by key.
        key_to_user = {v: k for k, v in users.items()}
        user_id = key_to_user.get(token)
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid API key")
        request.state.user_id = user_id
        return token

    # Single-key mode.
    expected = _pilot_api_key()
    if not expected:
        request.state.user_id = DEFAULT_USER_ID
        return None

    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid Authorization header. "
            "Use: Authorization: Bearer <api-key>",
        )

    token = auth[7:].strip()
    if token != expected:
        raise HTTPException(status_code=401, detail="Invalid API key")

    request.state.user_id = DEFAULT_USER_ID
    return token


def get_current_user(request: Request) -> str:
    """Extract the resolved user_id from request state.

    Falls back to DEFAULT_USER_ID if not set (e.g. health endpoints).
    """
    return getattr(request.state, "user_id", DEFAULT_USER_ID)


def _pilot_ops_users() -> set[str]:
    """Return the explicit ops/admin allowlist."""
    raw = os.environ.get("PILOT_OPS_USERS", DEFAULT_USER_ID).strip()
    if not raw:
        return set()
    return {item.strip() for item in raw.split(",") if item.strip()}


def user_can_access_ops(user_id: str) -> bool:
    """Return whether *user_id* may access ops/admin surfaces."""
    return user_id in _pilot_ops_users()


def require_ops_access(request: Request) -> str:
    """FastAPI dependency/helper for ops/admin-only endpoints."""
    user_id = get_current_user(request)
    if not user_can_access_ops(user_id):
        raise HTTPException(
            status_code=403,
            detail="Ops access is not enabled for this user.",
        )
    return user_id


def require_owner_or_ops_access(
    request: Request,
    owner_user_id: str | None,
    *,
    not_found_detail: str = "Record not found",
) -> str:
    """Allow access to the owner of a record or any ops user.

    Non-owners receive a 404 so single-record lookups do not reveal whether a
    record exists for another user.
    """
    user_id = get_current_user(request)
    if user_can_access_ops(user_id):
        return user_id
    if owner_user_id and owner_user_id == user_id:
        return user_id
    raise HTTPException(status_code=404, detail=not_found_detail)


# ---------------------------------------------------------------------------
# Rate limiting (in-memory, per-IP)
# ---------------------------------------------------------------------------


class RateLimiter:
    """Sliding-window rate limiter suitable for a single-process pilot."""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._timestamps: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str) -> tuple[bool, int]:
        """Return (allowed, remaining) for *key*."""
        now = time.monotonic()
        cutoff = now - self.window_seconds
        bucket = [t for t in self._timestamps[key] if t > cutoff]

        if len(bucket) >= self.max_requests:
            self._timestamps[key] = bucket
            return False, 0

        bucket.append(now)
        self._timestamps[key] = bucket
        return True, self.max_requests - len(bucket)


def _rate_limit_per_min() -> int:
    try:
        return int(os.environ.get("PILOT_RATE_LIMIT_PER_MIN", "60"))
    except ValueError:
        return 60


# Module-level instance; tests can replace via monkeypatch.
rate_limiter = RateLimiter(max_requests=_rate_limit_per_min())


def check_rate_limit(request: Request) -> None:
    """FastAPI dependency.  Enforces per-client rate limiting."""
    client_key = request.client.host if request.client else "unknown"
    allowed, remaining = rate_limiter.check(client_key)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Try again shortly.",
            headers={"Retry-After": str(rate_limiter.window_seconds)},
        )


# ---------------------------------------------------------------------------
# Mode and boundary validation helpers
# ---------------------------------------------------------------------------


def _live_mode_allowed() -> bool:
    return os.environ.get("PILOT_ALLOW_LIVE_MODE", "0").strip() == "1"


def _pilot_max_results() -> int:
    try:
        return int(os.environ.get("PILOT_MAX_RESULTS", "25"))
    except ValueError:
        return 25


def _pilot_max_query_length() -> int:
    try:
        return int(os.environ.get("PILOT_MAX_QUERY_LENGTH", "1000"))
    except ValueError:
        return 1000


def validate_mode(mode: str) -> str:
    """Raise 400/403 for invalid or disallowed modes."""
    if mode not in VALID_MODES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode '{mode}'. Must be one of: {', '.join(sorted(VALID_MODES))}",
        )
    if mode in ("live", "auto") and not _live_mode_allowed():
        raise HTTPException(
            status_code=403,
            detail="Live mode is not enabled for this pilot. "
            "Set PILOT_ALLOW_LIVE_MODE=1 to enable.",
        )
    return mode


def validate_query(query: str) -> str:
    """Raise 400 for queries that exceed pilot length limits."""
    max_len = _pilot_max_query_length()
    if len(query) > max_len:
        raise HTTPException(
            status_code=400,
            detail=f"Query too long ({len(query)} chars). Maximum: {max_len}.",
        )
    return query


def clamp_num_results(num_results: int) -> int:
    """Clamp to pilot maximum without error."""
    return min(num_results, _pilot_max_results())


# ---------------------------------------------------------------------------
# Request-logging middleware
# ---------------------------------------------------------------------------


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Adds ``X-Request-ID`` and logs each request with timing."""

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        request_id = uuid.uuid4().hex[:8]
        request.state.request_id = request_id
        start = time.monotonic()

        response: Response = await call_next(request)

        duration_ms = (time.monotonic() - start) * 1000
        response.headers["X-Request-ID"] = request_id

        logger.info(
            "request_id=%s method=%s path=%s status=%d duration_ms=%.1f",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response
