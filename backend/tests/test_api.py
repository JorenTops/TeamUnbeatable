import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    import app.main as m
    importlib.reload(m)  # fresh graph per test
    return TestClient(m.app)


def login(c, uid):
    r = c.post("/api/auth/demo-login", json={"user_id": uid})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_requires_auth(client):
    assert client.post("/api/query", json={"query": "holiday pay", "country": "BE"}).status_code == 401
    assert client.get("/api/notifications", headers={"Authorization": "Bearer abc.def"}).status_code == 401


def test_tampered_token_rejected(client):
    h = login(client, "emp-greet")
    tok = h["Authorization"].split()[1]
    body, sig = tok.split(".")
    bad = {"Authorization": f"Bearer {body}x.{sig}"}
    assert client.get("/api/me", headers=bad).status_code == 401


def test_country_filter_is_strict(client):
    h = login(client, "emp-greet")
    r = client.post("/api/query", json={"query": "holiday pay", "country": "BE"}, headers=h).json()
    ids = [x["document"]["id"] for x in r["results"]]
    assert "doc-nl-holiday" not in ids
    assert r["excluded_other_country"] >= 1
    assert r["top"]["document"]["id"] == "doc-be-holiday-2026"
    for n in r["subgraph"]["nodes"]:
        assert n["id"] not in ("country:NL", "emp-bram")


def test_contradicted_and_unowned_doc_is_low_trust(client):
    h = login(client, "emp-greet")
    r = client.post("/api/query", json={"query": "holiday pay", "country": "BE"}, headers=h).json()
    legacy = next(x for x in r["results"] if x["document"]["id"] == "doc-be-holiday-legacy")
    codes = {w["code"] for w in legacy["trust"]["warnings"]}
    assert {"NO_OWNER", "CONTRADICTED"} <= codes
    assert legacy["trust"]["band"] == "low"
    assert legacy["trust"]["components"]["contradiction_factor"] < 1


def test_unauthorised_country_forbidden(client):
    h = login(client, "emp-greet")  # BE only
    assert client.post("/api/query", json={"query": "holiday", "country": "NL"}, headers=h).status_code == 403
    assert client.get("/api/documents/doc-nl-holiday?country=NL", headers=h).status_code == 403
    # doc from another country via an allowed country -> 404, no enumeration
    assert client.get("/api/documents/doc-nl-holiday?country=BE", headers=h).status_code == 404


def test_flag_conflict_decays_trust_and_notifies_owner(client):
    h = login(client, "emp-greet")
    r = client.post("/api/documents/doc-be-meal/conflicts", headers=h,
                    json={"country": "BE", "channel": "#benefits-be", "text": "The face value changed in the last royal decree."})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["trust"]["score"] < body["score_before"]
    assert body["notified"] == ["emp-anna"]
    # reporter cannot read owner's notifications
    assert client.get("/api/notifications", headers=h).json() == []
    anna = login(client, "emp-anna")
    notes = client.get("/api/notifications", headers=anna).json()
    assert len(notes) == 1
    # IDOR: greet cannot mark anna's notification as read
    assert client.post(f"/api/notifications/{notes[0]['id']}/read", headers=h).status_code == 404
    assert client.post(f"/api/notifications/{notes[0]['id']}/read", headers=anna).status_code == 200


def test_flag_spam_blocked(client):
    h = login(client, "emp-greet")
    payload = {"country": "BE", "channel": "#benefits-be", "text": "This is wrong according to the client."}
    assert client.post("/api/documents/doc-be-meal/conflicts", headers=h, json=payload).status_code == 201
    assert client.post("/api/documents/doc-be-meal/conflicts", headers=h, json=payload).status_code == 409


def test_reporter_cannot_be_spoofed(client):
    h = login(client, "emp-greet")
    r = client.post("/api/documents/doc-be-meal/conflicts", headers=h,
                    json={"country": "BE", "channel": "#x", "text": "0123456789", "reporter": "emp-anna"})
    assert r.status_code == 422


def test_orphan_flag_routes_to_country_experts(client):
    h = login(client, "emp-hugo")
    r = client.post("/api/documents/doc-be-remote/conflicts", headers=h,
                    json={"country": "BE", "channel": "#tax-be", "text": "Ceiling was indexed again this year."}).json()
    assert "emp-frank" not in r["notified"]
    assert "emp-anna" in r["notified"] and "emp-ines" in r["notified"]


def test_verify_permissions_and_resolution(client):
    greet = login(client, "emp-greet")  # consultant
    assert client.post("/api/documents/doc-be-holiday-legacy/verify", headers=greet,
                       json={"country": "BE", "reviewed_contradictions": True}).status_code == 403
    bram = login(client, "emp-bram")  # NL expert
    assert client.post("/api/documents/doc-be-holiday-legacy/verify", headers=bram,
                       json={"country": "BE", "reviewed_contradictions": True}).status_code == 403
    anna = login(client, "emp-anna")
    assert client.post("/api/documents/doc-be-holiday-legacy/verify", headers=anna,
                       json={"country": "BE", "reviewed_contradictions": False}).status_code == 400
    r = client.post("/api/documents/doc-be-holiday-legacy/verify", headers=anna,
                    json={"country": "BE", "reviewed_contradictions": True}).json()
    assert r["trust"]["score"] > r["score_before"]
    assert all(c["resolved_by_later_verification"] for c in r["trust"]["contradictions"])


def test_inactive_user_cannot_login(client):
    assert client.post("/api/auth/demo-login", json={"user_id": "emp-frank"}).status_code == 401


def test_owner_cannot_flag_own_doc(client):
    anna = login(client, "emp-anna")
    assert client.post("/api/documents/doc-be-meal/conflicts", headers=anna,
                       json={"country": "BE", "channel": "#b", "text": "0123456789ab"}).status_code == 400
