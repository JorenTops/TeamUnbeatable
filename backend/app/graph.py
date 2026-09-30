"""Temporal Trust Graph engine.

The knowledge landscape is a typed, directed multigraph (NetworkX MultiDiGraph):

  Node types : Document, Employee, Country, TeamsChat, Verification
  Edge types : Authored_By        Document   -> Employee
               Applies_To_Country Document   -> Country   (also TeamsChat -> Country)
               Based_In           Employee   -> Country
               Contradicted_By    Document   -> TeamsChat
               Posted_By          TeamsChat  -> Employee
               Verified_On        Document   -> Verification  (carries a timestamp)
               Verified_By        Verification -> Employee
               Endorsed_By        Document   -> Employee

Trust is computed on a *country-scoped* subgraph only, so a Dutch document can
never lend (or steal) trust from a Belgian question.
"""

from __future__ import annotations

import math
import re
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import networkx as nx

from . import mock_data

# ---- Tunable model parameters ------------------------------------------------
FRESHNESS_HALF_LIFE_DAYS = 180      # verification loses half its value every 6 months
STALE_AFTER_DAYS = 365
CONTRADICTION_LAMBDA = 0.7          # strength of one fully-weighted contradiction
CHAT_RECENCY_HALF_LIFE_DAYS = 30    # a contradiction from last week weighs more than one from last year
MIN_CONTRADICTION_FACTOR = 0.05     # trust never collapses to exactly zero
WEIGHTS = {"freshness": 0.35, "ownership": 0.35, "centrality": 0.30}
ROLE_WEIGHT = {"admin": 1.0, "expert": 1.0, "consultant": 0.7}

TOKEN_RE = re.compile(r"[a-z0-9]+")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _days_between(a: datetime, b: datetime) -> float:
    return max(0.0, (b - a).total_seconds() / 86400.0)


@dataclass
class Notification:
    id: str
    recipient: str
    document_id: str
    message: str
    created_at: datetime
    read: bool = False


@dataclass
class TrustGraph:
    g: nx.MultiDiGraph = field(default_factory=nx.MultiDiGraph)
    notifications: list[Notification] = field(default_factory=list)
    lock: threading.RLock = field(default_factory=threading.RLock)

    # ------------------------------------------------------------------ build
    @classmethod
    def from_mock(cls, now: datetime | None = None) -> "TrustGraph":
        now = now or utcnow()
        tg = cls()
        g = tg.g
        for code, name in mock_data.COUNTRIES.items():
            g.add_node(f"country:{code}", type="Country", code=code, label=name)

        for e in mock_data.EMPLOYEES:
            g.add_node(e["id"], type="Employee", label=e["name"], role=e["role"],
                       active=e["active"], countries=list(e["countries"]), expertise=list(e["expertise"]))
            for c in e["countries"]:
                g.add_edge(e["id"], f"country:{c}", key="Based_In", type="Based_In")

        for d in mock_data.DOCUMENTS:
            g.add_node(d["id"], type="Document", label=d["title"], tags=list(d["tags"]),
                       summary=d["summary"], countries=list(d["countries"]),
                       updated_at=now - timedelta(days=d["updated_days_ago"]))
            for c in d["countries"]:
                g.add_edge(d["id"], f"country:{c}", key="Applies_To_Country", type="Applies_To_Country")
            if d["author"]:
                g.add_edge(d["id"], d["author"], key="Authored_By", type="Authored_By")
            if d["verified_days_ago"] is not None:
                tg._add_verification(d["id"], d["author"], now - timedelta(days=d["verified_days_ago"]))

        for doc_id_emp in mock_data.ENDORSEMENTS:
            emp, doc = doc_id_emp
            g.add_edge(doc, emp, key=f"Endorsed_By:{emp}", type="Endorsed_By")

        for ch in mock_data.TEAMS_CHATS:
            tg._add_chat(ch["id"], ch["channel"], ch["author"], ch["text"], ch["countries"],
                         now - timedelta(days=ch["days_ago"]), ch["contradicts"], source="teams")
        return tg

    def _add_verification(self, doc_id: str, verifier: str | None, when: datetime) -> str:
        vid = f"verif:{doc_id}:{int(when.timestamp())}:{uuid.uuid4().hex[:6]}"
        self.g.add_node(vid, type="Verification", label=f"Verified {when.date().isoformat()}", at=when)
        self.g.add_edge(doc_id, vid, key="Verified_On", type="Verified_On", at=when)
        if verifier:
            self.g.add_edge(vid, verifier, key="Verified_By", type="Verified_By")
        return vid

    def _add_chat(self, chat_id, channel, author, text, countries, when, contradicts, source) -> str:
        self.g.add_node(chat_id, type="TeamsChat", label=channel, text=text, at=when,
                        countries=list(countries), source=source)
        self.g.add_edge(chat_id, author, key="Posted_By", type="Posted_By")
        for c in countries:
            self.g.add_edge(chat_id, f"country:{c}", key="Applies_To_Country", type="Applies_To_Country")
        if contradicts:
            self.g.add_edge(contradicts, chat_id, key="Contradicted_By", type="Contradicted_By", at=when)
        return chat_id

    # ---------------------------------------------------------------- helpers
    def node(self, nid: str) -> dict:
        return self.g.nodes[nid]

    def is_type(self, nid: str, t: str) -> bool:
        return nid in self.g and self.g.nodes[nid].get("type") == t

    def out_typed(self, nid: str, etype: str, g: nx.MultiDiGraph | None = None) -> list[str]:
        g = g if g is not None else self.g
        return [v for _, v, d in g.out_edges(nid, data=True) if d.get("type") == etype]

    def in_typed(self, nid: str, etype: str, g: nx.MultiDiGraph | None = None) -> list[str]:
        g = g if g is not None else self.g
        return [u for u, _, d in g.in_edges(nid, data=True) if d.get("type") == etype]

    def owner_of(self, doc_id: str) -> str | None:
        owners = self.out_typed(doc_id, "Authored_By")
        return owners[0] if owners else None

    def last_verified(self, doc_id: str) -> datetime | None:
        times = [self.g.nodes[v]["at"] for v in self.out_typed(doc_id, "Verified_On")]
        return max(times) if times else None

    # ------------------------------------------------------ country scoping
    def country_subgraph(self, country: str) -> nx.MultiDiGraph:
        """Strict regional scope.

        Keeps only Documents / TeamsChats that apply to `country`, Employees based
        in `country`, the country node itself and verification events of kept
        documents. Everything tied exclusively to other countries is dropped, so
        no trust can leak across borders.
        """
        cnode = f"country:{country}"
        keep: set[str] = {cnode}
        for nid, data in self.g.nodes(data=True):
            t = data.get("type")
            if t in ("Document", "TeamsChat", "Employee") and country in data.get("countries", []):
                keep.add(nid)
        for nid in list(keep):
            if self.is_type(nid, "Document"):
                keep.update(self.out_typed(nid, "Verified_On"))
        return self.g.subgraph(keep).copy()

    # -------------------------------------------------------- trust scoring
    def _centrality(self, sub: nx.MultiDiGraph) -> dict[str, float]:
        """Trust-weighted PageRank over the country subgraph.

        Trust flows *from* people and verification events *into* documents.
        Personalisation seeds the walk on active employees (weighted by role) and
        on verification events (weighted by freshness), so a document that is
        authored, endorsed and recently verified by active experts accumulates
        more topological trust than an orphaned one.
        """
        now = utcnow()
        flow = nx.DiGraph()
        flow.add_nodes_from(sub.nodes)
        seeds: dict[str, float] = {}
        for u, v, d in sub.edges(data=True):
            t = d.get("type")
            if t == "Authored_By":
                flow.add_edge(v, u, weight=1.0)
            elif t == "Endorsed_By":
                flow.add_edge(v, u, weight=0.6)
            elif t == "Verified_On":
                flow.add_edge(v, u, weight=1.0)
        for nid, data in sub.nodes(data=True):
            if data.get("type") == "Employee" and data.get("active"):
                seeds[nid] = ROLE_WEIGHT.get(data.get("role"), 0.5)
            elif data.get("type") == "Verification":
                seeds[nid] = 0.5 ** (_days_between(data["at"], now) / FRESHNESS_HALF_LIFE_DAYS)
        if not seeds or flow.number_of_edges() == 0:
            return {}
        pr = nx.pagerank(flow, alpha=0.85, personalization=seeds, weight="weight")
        docs = {n: s for n, s in pr.items() if sub.nodes[n].get("type") == "Document"}
        top = max(docs.values(), default=0.0)
        return {n: (s / top if top > 0 else 0.0) for n, s in docs.items()}

    def trust_for(self, doc_id: str, sub: nx.MultiDiGraph, centrality: dict[str, float]) -> dict:
        now = utcnow()
        warnings: list[dict] = []
        explanation: list[str] = []

        # 1. Freshness (temporal)
        lv = self.last_verified(doc_id)
        if lv is None:
            freshness, days_since = 0.0, None
            warnings.append({"code": "NEVER_VERIFIED", "severity": "high",
                             "message": "This document has never been verified."})
            explanation.append("Never verified: freshness contributes 0.")
        else:
            days_since = _days_between(lv, now)
            freshness = 0.5 ** (days_since / FRESHNESS_HALF_LIFE_DAYS)
            explanation.append(f"Last verified {days_since:.0f} days ago: freshness {freshness:.2f} "
                               f"(half-life {FRESHNESS_HALF_LIFE_DAYS} days).")
            if days_since > STALE_AFTER_DAYS:
                warnings.append({"code": "STALE", "severity": "medium",
                                 "message": f"Not verified for {days_since:.0f} days."})

        # 2. Ownership (topological: is there a path to an accountable, active person?)
        owner = self.owner_of(doc_id)
        owner_info = None
        if owner is None:
            ownership = 0.0
            warnings.append({"code": "NO_OWNER", "severity": "high",
                             "message": "Nobody owns this document. No one is accountable for keeping it correct."})
            explanation.append("No Authored_By edge: ownership contributes 0.")
        else:
            od = self.node(owner)
            owner_info = {"id": owner, "name": od["label"], "active": od["active"], "role": od["role"]}
            if od["active"]:
                ownership = 1.0
                explanation.append(f"Owned by {od['label']} (active {od['role']}).")
            else:
                ownership = 0.3
                warnings.append({"code": "OWNER_INACTIVE", "severity": "high",
                                 "message": f"Owner {od['label']} has left the organisation."})
                explanation.append(f"Owner {od['label']} is no longer active: ownership 0.3.")

        # 3. Topological centrality (country-scoped PageRank)
        cent = centrality.get(doc_id, 0.0)
        endorsers = [self.node(e)["label"] for e in self.out_typed(doc_id, "Endorsed_By", sub)]
        explanation.append(f"Trust centrality in the country graph: {cent:.2f}"
                           + (f" (endorsed by {', '.join(endorsers)})." if endorsers else "."))

        base = (WEIGHTS["freshness"] * freshness + WEIGHTS["ownership"] * ownership
                + WEIGHTS["centrality"] * cent)

        # 4. Contradiction decay: every Teams chat that contradicts the doc *after*
        #    its last verification multiplies trust by exp(-lambda * w).
        contradictions = []
        penalty = 0.0
        for chat in self.out_typed(doc_id, "Contradicted_By", sub):
            cd = self.node(chat)
            if cd.get("type") != "TeamsChat":
                continue
            resolved = lv is not None and cd["at"] <= lv
            posters = self.out_typed(chat, "Posted_By")
            poster = self.node(posters[0]) if posters else None
            author_w = ROLE_WEIGHT.get(poster["role"], 0.5) if poster else 0.5
            age = _days_between(cd["at"], now)
            recency_w = 0.5 ** (age / CHAT_RECENCY_HALF_LIFE_DAYS)
            w = 0.0 if resolved else author_w * max(recency_w, 0.25)
            penalty += w
            contradictions.append({
                "chat_id": chat, "channel": cd["label"], "text": cd["text"], "source": cd.get("source"),
                "posted_by": poster["label"] if poster else None, "days_ago": round(age, 1),
                "weight": round(w, 3), "resolved_by_later_verification": resolved,
            })
        factor = max(MIN_CONTRADICTION_FACTOR, math.exp(-CONTRADICTION_LAMBDA * penalty))
        open_contra = [c for c in contradictions if not c["resolved_by_later_verification"]]
        if open_contra:
            warnings.append({"code": "CONTRADICTED", "severity": "high",
                             "message": f"Contradicted by {len(open_contra)} Teams conversation(s) "
                                        "since the last verification."})
            explanation.append(f"{len(open_contra)} open contradiction(s): trust multiplied by {factor:.2f}.")

        score = round(100 * base * factor, 1)
        band = "high" if score >= 70 else "medium" if score >= 40 else "low"
        return {
            "score": score, "band": band,
            "components": {"freshness": round(freshness, 3), "ownership": round(ownership, 3),
                           "centrality": round(cent, 3), "base": round(base, 3),
                           "contradiction_factor": round(factor, 3)},
            "weights": WEIGHTS,
            "owner": owner_info,
            "last_verified_days_ago": None if days_since is None else round(days_since, 1),
            "endorsed_by": endorsers,
            "contradictions": contradictions,
            "warnings": warnings,
            "explanation": explanation,
        }

    def score_document(self, doc_id: str, country: str) -> dict:
        sub = self.country_subgraph(country)
        return self.trust_for(doc_id, sub, self._centrality(sub))

    # ----------------------------------------------------------------- query
    @staticmethod
    def _tokens(text: str) -> set[str]:
        return set(TOKEN_RE.findall(text.lower()))

    def relevance(self, doc_id: str, q_tokens: set[str]) -> float:
        d = self.node(doc_id)
        title = self._tokens(d["label"])
        tags = self._tokens(" ".join(d["tags"]))
        body = self._tokens(d["summary"])
        if not q_tokens:
            return 0.0
        hits = 3 * len(q_tokens & tags) + 2 * len(q_tokens & title) + len(q_tokens & body)
        return round(hits / (3 * len(q_tokens)), 3)

    def query(self, text: str, country: str) -> dict:
        with self.lock:
            sub = self.country_subgraph(country)
            cent = self._centrality(sub)
            q = self._tokens(text)
            results = []
            for nid, data in sub.nodes(data=True):
                if data.get("type") != "Document":
                    continue
                rel = self.relevance(nid, q)
                if rel <= 0:
                    continue
                results.append({"document": self.document_view(nid), "relevance": rel,
                                "trust": self.trust_for(nid, sub, cent)})
            results.sort(key=lambda r: (r["trust"]["score"] * (0.5 + r["relevance"])), reverse=True)

            # How many matching docs were excluded because they belong to other countries?
            excluded = [nid for nid, d in self.g.nodes(data=True)
                        if d.get("type") == "Document" and nid not in sub and self.relevance(nid, q) > 0]
            experts = [
                {"id": n, "name": d["label"], "role": d["role"], "expertise": d["expertise"]}
                for n, d in sub.nodes(data=True)
                if d.get("type") == "Employee" and d.get("active") and d.get("role") in ("expert", "admin")
                and q & self._tokens(" ".join(d["expertise"]))
            ]
            return {
                "query": text, "country": country,
                "top": results[0] if results else None,
                "results": results,
                "excluded_other_country": len(excluded),
                "experts": experts,
                "subgraph": self.subgraph_view(sub, [r["document"]["id"] for r in results]),
            }

    # ----------------------------------------------------------- mutations
    def flag_conflict(self, doc_id: str, reporter: str, text: str, channel: str, country: str) -> dict:
        with self.lock:
            before = self.score_document(doc_id, country)["score"]
            chat_id = f"chat-flag-{uuid.uuid4().hex[:10]}"
            self._add_chat(chat_id, channel, reporter, text, [country], utcnow(), doc_id, source="manual_flag")
            after = self.score_document(doc_id, country)
            owner = self.owner_of(doc_id)
            recipients: list[str] = []
            if owner and self.node(owner)["active"]:
                recipients = [owner]
            else:  # orphaned doc -> route to admins / experts of that country
                recipients = [n for n, d in self.g.nodes(data=True)
                              if d.get("type") == "Employee" and d.get("active")
                              and d.get("role") in ("admin", "expert") and country in d["countries"]]
            title = self.node(doc_id)["label"]
            reporter_name = self.node(reporter)["label"]
            for r in recipients:
                self.notifications.append(Notification(
                    id=uuid.uuid4().hex, recipient=r, document_id=doc_id, created_at=utcnow(),
                    message=f"{reporter_name} flagged a conflict on '{title}' in {channel}. "
                            f"Trust dropped from {before} to {after['score']}."))
            return {"chat_id": chat_id, "score_before": before, "trust": after, "notified": recipients}

    def verify(self, doc_id: str, verifier: str, country: str) -> dict:
        with self.lock:
            before = self.score_document(doc_id, country)["score"]
            self._add_verification(doc_id, verifier, utcnow())
            return {"score_before": before, "trust": self.score_document(doc_id, country)}

    def has_open_flag_by(self, doc_id: str, reporter: str) -> bool:
        lv = self.last_verified(doc_id)
        for chat in self.out_typed(doc_id, "Contradicted_By"):
            cd = self.node(chat)
            if cd.get("source") == "manual_flag" and reporter in self.out_typed(chat, "Posted_By"):
                if lv is None or cd["at"] > lv:
                    return True
        return False

    # ----------------------------------------------------------------- views
    def document_view(self, doc_id: str) -> dict:
        d = self.node(doc_id)
        return {"id": doc_id, "title": d["label"], "summary": d["summary"], "tags": d["tags"],
                "countries": d["countries"], "updated_at": d["updated_at"].isoformat()}

    def subgraph_view(self, sub: nx.MultiDiGraph, focus_docs: list[str]) -> dict:
        """Ego-network around the matching documents, for visualisation."""
        keep = set(focus_docs)
        for doc in focus_docs:
            keep.update(sub.successors(doc))
        nodes = [{"id": n, "type": sub.nodes[n]["type"], "label": sub.nodes[n].get("label", n),
                  "active": sub.nodes[n].get("active")} for n in keep if n in sub]
        edges = [{"source": u, "target": v, "type": d["type"]}
                 for u, v, d in sub.edges(data=True) if u in keep and v in keep]
        return {"nodes": nodes, "edges": edges}
