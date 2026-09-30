"""Authentication, authorisation and abuse protection.

* Stateless HMAC-SHA256 signed bearer tokens with expiry (no third-party JWT lib).
* The signing key comes from TTG_SECRET_KEY; if unset, a random key is generated
  per process (tokens simply stop working after a restart). Nothing secret is
  ever committed to the repository.
* Every protected route derives the acting user from the token - never from the
  request body - which prevents identity spoofing and IDOR.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import threading
import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

log = logging.getLogger("ttg.security")

TOKEN_TTL_SECONDS = int(os.getenv("TTG_TOKEN_TTL_SECONDS", str(8 * 3600)))
_SECRET = os.getenv("TTG_SECRET_KEY") or secrets.token_urlsafe(48)
if not os.getenv("TTG_SECRET_KEY"):
    log.warning("TTG_SECRET_KEY not set - using an ephemeral random signing key.")
if len(_SECRET) < 32:
    raise RuntimeError("TTG_SECRET_KEY must be at least 32 characters long.")
_KEY = _SECRET.encode()


def demo_login_enabled() -> bool:
    """Passwordless demo login is OFF unless explicitly enabled for local demos."""
    return os.getenv("TTG_DEMO_LOGIN", "false").lower() in ("1", "true", "yes")


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def issue_token(user_id: str) -> str:
    payload = {"sub": user_id, "exp": int(time.time()) + TOKEN_TTL_SECONDS, "jti": secrets.token_hex(8)}
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    sig = _b64(hmac.new(_KEY, body.encode(), hashlib.sha256).digest())
    return f"{body}.{sig}"


def verify_token(token: str) -> str:
    try:
        body, sig = token.split(".", 1)
        expected = _b64(hmac.new(_KEY, body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected):
            raise ValueError("bad signature")
        payload = json.loads(_unb64(body))
        if not isinstance(payload, dict) or int(payload.get("exp", 0)) < time.time():
            raise ValueError("expired")
        sub = payload.get("sub")
        if not isinstance(sub, str):
            raise ValueError("bad subject")
        return sub
    except Exception:  # noqa: BLE001 - never leak why a token failed
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token",
                            headers={"WWW-Authenticate": "Bearer"}) from None


_bearer = HTTPBearer(auto_error=False)


def current_user_id(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> str:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required",
                            headers={"WWW-Authenticate": "Bearer"})
    return verify_token(creds.credentials)


class RateLimiter:
    """Sliding-window limiter keyed by (action, user)."""

    def __init__(self) -> None:
        self._hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, action: str, key: str, limit: int, window_s: int) -> None:
        now = time.monotonic()
        with self._lock:
            q = self._hits[(action, key)]
            while q and now - q[0] > window_s:
                q.popleft()
            if len(q) >= limit:
                raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many requests, slow down.")
            q.append(now)


rate_limiter = RateLimiter()
