"""FastAPI application exposing the Temporal Trust Graph."""

from __future__ import annotations

import logging
import os
import re
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Path, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from . import mock_data
from .graph import TrustGraph
from .security import current_user_id, demo_login_enabled, issue_token, rate_limiter

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("ttg")

IS_DEV = os.getenv("TTG_ENV", "production").lower() == "development"
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("TTG_ALLOWED_ORIGINS", "http://localhost:3000").split(",") if o.strip()]

app = FastAPI(
    title="Temporal Trust Graph",
    version="1.0.0",
    docs_url="/docs" if IS_DEV else None,
    redoc_url=None,
    openapi_url="/openapi.json" if IS_DEV else None,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

GRAPH = TrustGraph.from_mock()

CountryCode = Literal["BE", "NL", "FR", "DE", "UK"]
ID_PATTERN = r"^[a-z0-9][a-z0-9\-]{1,63}$"
CHANNEL_RE = re.compile(r"^#[a-z0-9][a-z0-9\-_]{0,48}$")


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    return response


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):  # never leak stack traces
    log.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# ------------------------------------------------------------------ models
class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class LoginIn(StrictModel):
    user_id: str = Field(pattern=ID_PATTERN)


class QueryIn(StrictModel):
    query: str = Field(min_length=2, max_length=200)
    country: CountryCode


class ConflictIn(StrictModel):
    country: CountryCode
    channel: str = Field(min_length=2, max_length=50)
    text: str = Field(min_length=10, max_length=1000)

    @field_validator("channel")
    @classmethod
    def channel_format(cls, v: str) -> str:
        v = v.lower()
        if not CHANNEL_RE.match(v):
            raise ValueError("channel must look like #payroll-be")
        return v


class VerifyIn(StrictModel):
    country: CountryCode
    reviewed_contradictions: bool = Field(
        description="Verifier confirms they reviewed every open contradiction before re-verifying.")


# ------------------------------------------------------------ authorisation
def load_user(uid: str = Depends(current_user_id)) -> dict:
    if not GRAPH.is_type(uid, "Employee"):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unknown user")
    user = GRAPH.node(uid)
    if not user.get("active"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account disabled")
    return {"id": uid, **user}


def require_country(user: dict, country: str) -> None:
    if user["role"] != "admin" and country not in user["countries"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not authorised for this country")


def require_document_in_country(doc_id: str, country: str) -> None:
    # Same 404 for "does not exist" and "not in this country" to avoid ID enumeration.
    if not GRAPH.is_type(doc_id, "Document") or country not in GRAPH.node(doc_id)["countries"]:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")


def user_view(uid: str) -> dict:
    d = GRAPH.node(uid)
    return {"id": uid, "name": d["label"], "role": d["role"], "countries": d["countries"]}


# ------------------------------------------------------------------ routes
@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/auth/demo-users")
def demo_users():
    if not demo_login_enabled():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    return [user_view(e["id"]) for e in mock_data.EMPLOYEES if e["active"]]


@app.post("/api/auth/demo-login")
def demo_login(body: LoginIn, request: Request):
    """Passwordless login for the local demo only (disabled unless TTG_DEMO_LOGIN=true)."""
    if not demo_login_enabled():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    client = request.client.host if request.client else "unknown"
    rate_limiter.check("login", client, limit=20, window_s=60)
    if not GRAPH.is_type(body.user_id, "Employee") or not GRAPH.node(body.user_id).get("active"):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unknown user")
    return {"access_token": issue_token(body.user_id), "token_type": "bearer", "user": user_view(body.user_id)}


@app.get("/api/me")
def me(user: dict = Depends(load_user)):
    return user_view(user["id"])


@app.post("/api/query")
def query(body: QueryIn, user: dict = Depends(load_user)):
    require_country(user, body.country)
    rate_limiter.check("query", user["id"], limit=60, window_s=60)
    return GRAPH.query(body.query, body.country)


@app.get("/api/documents/{doc_id}")
def get_document(doc_id: str = Path(pattern=ID_PATTERN), country: CountryCode = Query(...),
                 user: dict = Depends(load_user)):
    require_country(user, country)
    require_document_in_country(doc_id, country)
    with GRAPH.lock:
        return {"document": GRAPH.document_view(doc_id), "trust": GRAPH.score_document(doc_id, country)}


@app.post("/api/documents/{doc_id}/conflicts", status_code=201)
def flag_conflict(body: ConflictIn, doc_id: str = Path(pattern=ID_PATTERN), user: dict = Depends(load_user)):
    require_country(user, body.country)
    require_document_in_country(doc_id, body.country)
    rate_limiter.check("flag", user["id"], limit=10, window_s=3600)
    with GRAPH.lock:
        # Business rule: one open flag per person per document, so a single user
        # cannot drive a document's trust to the floor by spamming flags.
        if GRAPH.has_open_flag_by(doc_id, user["id"]):
            raise HTTPException(status.HTTP_409_CONFLICT,
                                "You already have an open conflict on this document. "
                                "It closes when the owner re-verifies.")
        if GRAPH.owner_of(doc_id) == user["id"]:
            raise HTTPException(status.HTTP_400_BAD_REQUEST,
                                "Owners update their document instead of flagging it.")
        # The reporter is always the authenticated user, never a body field.
        return GRAPH.flag_conflict(doc_id, user["id"], body.text, body.channel, body.country)


@app.post("/api/documents/{doc_id}/verify")
def verify(body: VerifyIn, doc_id: str = Path(pattern=ID_PATTERN), user: dict = Depends(load_user)):
    require_country(user, body.country)
    require_document_in_country(doc_id, body.country)
    owner = GRAPH.owner_of(doc_id)
    is_owner = owner == user["id"]
    is_country_expert = user["role"] == "expert" and body.country in user["countries"]
    if not (is_owner or is_country_expert or user["role"] == "admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the owner or a country expert can verify")
    if not body.reviewed_contradictions:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Review open contradictions before verifying")
    rate_limiter.check("verify", user["id"], limit=30, window_s=3600)
    return GRAPH.verify(doc_id, user["id"], body.country)


@app.get("/api/notifications")
def notifications(user: dict = Depends(load_user)):
    with GRAPH.lock:
        mine = [n for n in GRAPH.notifications if n.recipient == user["id"]]
        return [{"id": n.id, "document_id": n.document_id, "message": n.message,
                 "created_at": n.created_at.isoformat(), "read": n.read}
                for n in sorted(mine, key=lambda n: n.created_at, reverse=True)]


@app.post("/api/notifications/{notification_id}/read")
def mark_read(notification_id: str = Path(pattern=r"^[a-f0-9]{32}$"), user: dict = Depends(load_user)):
    with GRAPH.lock:
        for n in GRAPH.notifications:
            if n.id == notification_id and n.recipient == user["id"]:  # ownership check (no IDOR)
                n.read = True
                return {"ok": True}
    raise HTTPException(status.HTTP_404_NOT_FOUND, "Notification not found")
