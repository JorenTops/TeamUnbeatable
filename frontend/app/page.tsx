"use client";

import { useCallback, useEffect, useState } from "react";
import FlagConflictForm from "@/components/FlagConflictForm";
import GraphView from "@/components/GraphView";
import TrustCard from "@/components/TrustCard";
import { api } from "@/lib/api";
import type { Country, Doc, Notification, QueryResponse, User } from "@/lib/types";

const COUNTRIES: { code: Country; name: string }[] = [
  { code: "BE", name: "Belgium" }, { code: "NL", name: "Netherlands" }, { code: "FR", name: "France" },
  { code: "DE", name: "Germany" }, { code: "UK", name: "United Kingdom" },
];
const EXAMPLES = ["holiday pay", "remote work allowance", "sick leave", "meal vouchers"];

export default function Dashboard() {
  const [users, setUsers] = useState<User[]>([]);
  const [token, setToken] = useState<string | null>(null); // memory only, never persisted
  const [user, setUser] = useState<User | null>(null);
  const [country, setCountry] = useState<Country>("BE");
  const [q, setQ] = useState("holiday pay");
  const [data, setData] = useState<QueryResponse | null>(null);
  const [selected, setSelected] = useState<string | undefined>();
  const [flagDoc, setFlagDoc] = useState<Doc | null>(null);
  const [notes, setNotes] = useState<Notification[]>([]);
  const [toast, setToast] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.demoUsers().then(setUsers).catch(() => setError("Backend not reachable, or demo login is disabled (set TTG_DEMO_LOGIN=true)."));
  }, []);

  const flash = (m: string) => { setToast(m); setTimeout(() => setToast(null), 4500); };

  const refreshNotes = useCallback(async (t: string) => {
    try { setNotes(await api.notifications(t)); } catch { /* non-critical */ }
  }, []);

  const run = useCallback(async (t: string, query: string, c: Country) => {
    setLoading(true); setError(null);
    try {
      const res = await api.query(t, query, c);
      setData(res);
      setSelected(res.top?.document.id);
    } catch (e) {
      setData(null); setError(e instanceof Error ? e.message : "Query failed");
    } finally { setLoading(false); }
  }, []);

  async function login(uid: string) {
    if (!uid) { setToken(null); setUser(null); setData(null); setNotes([]); return; }
    try {
      const r = await api.login(uid);
      setToken(r.access_token); setUser(r.user);
      const c = (r.user.countries.includes(country) ? country : r.user.countries[0]) as Country;
      setCountry(c);
      await Promise.all([run(r.access_token, q, c), refreshNotes(r.access_token)]);
    } catch (e) { setError(e instanceof Error ? e.message : "Login failed"); }
  }

  async function flag(channel: string, text: string) {
    if (!token || !flagDoc) return;
    const r = await api.flag(token, flagDoc.id, country, channel, text);
    setFlagDoc(null);
    flash(`Trust ${r.score_before} → ${r.trust.score}. Alert sent to ${r.notified.length} owner/expert(s).`);
    await run(token, q, country);
  }

  async function verify(docId: string) {
    if (!token) return;
    try {
      const r = await api.verify(token, docId, country);
      flash(`Re-verified. Trust ${r.score_before} → ${r.trust.score}. Earlier contradictions marked resolved.`);
      await run(token, q, country);
    } catch (e) { flash(e instanceof Error ? e.message : "Verification failed"); }
  }

  const unread = notes.filter((n) => !n.read);

  return (
    <main>
      <header className="top">
        <div>
          <div className="brand"><span className="logo" aria-hidden>◈</span> Temporal Trust Graph</div>
          <div className="muted small">Find it. Understand it. Trust it.</div>
        </div>
        <div className="who">
          <select aria-label="Sign in as" value={user?.id ?? ""} onChange={(e) => login(e.target.value)}>
            <option value="">Sign in as… (demo)</option>
            {users.map((u) => <option key={u.id} value={u.id}>{u.name} · {u.role} · {u.countries.join("/")}</option>)}
          </select>
          {user && (
            <button className="btn bell" onClick={() => token && refreshNotes(token)} title="Refresh alerts">
              Alerts {unread.length > 0 && <span className="badge">{unread.length}</span>}
            </button>
          )}
        </div>
      </header>

      {user && unread.length > 0 && (
        <section className="inbox">
          {unread.map((n) => (
            <div key={n.id} className="inbox-item">
              <span>🔔 {n.message}</span>
              <button className="btn small" onClick={async () => { await api.markRead(token!, n.id); refreshNotes(token!); }}>Dismiss</button>
            </div>
          ))}
        </section>
      )}

      {!user ? (
        <section className="empty">
          <h2>A search returns ten answers. Which one can you trust?</h2>
          <p className="muted">Pick a demo user above. Try <strong>Greet Maes</strong> (Belgian consultant) asking about holiday pay,
            then sign in as <strong>Anna Peeters</strong> to receive the conflict alert.</p>
          {error && <div className="error">{error}</div>}
        </section>
      ) : (
        <>
          <form className="search" onSubmit={(e) => { e.preventDefault(); if (token) run(token, q, country); }}>
            <select aria-label="Country" value={country} onChange={(e) => { const c = e.target.value as Country; setCountry(c); if (token) run(token, q, c); }}>
              {COUNTRIES.filter((c) => user.role === "admin" || user.countries.includes(c.code)).map((c) => (
                <option key={c.code} value={c.code}>{c.code} · {c.name}</option>
              ))}
            </select>
            <input value={q} onChange={(e) => setQ(e.target.value)} minLength={2} maxLength={200} required
              placeholder="Ask a question, e.g. holiday pay on exit" />
            <button className="btn btn-primary" disabled={loading}>{loading ? "Scoring…" : "Ask the graph"}</button>
          </form>
          <div className="examples">
            {EXAMPLES.map((ex) => <button key={ex} className="chip chip-btn" onClick={() => { setQ(ex); if (token) run(token, ex, country); }}>{ex}</button>)}
          </div>

          {error && <div className="error">{error}</div>}

          {data && (
            <div className="grid">
              <section>
                <div className="scope">
                  Scoped to <strong>{data.country}</strong> ·
                  {" "}{data.results.length} matching document(s) scored
                  {data.excluded_other_country > 0 && <> · <span className="warn-text">{data.excluded_other_country} from other countries filtered out</span></>}
                </div>
                {data.results.length === 0 && <div className="card">No documents for this question in {data.country}.</div>}
                {data.results.map((r, i) => (
                  <TrustCard key={r.document.id} result={r} primary={i === 0} user={user}
                    selected={selected === r.document.id} onSelect={() => setSelected(r.document.id)}
                    onFlag={() => setFlagDoc(r.document)} onVerify={() => verify(r.document.id)} />
                ))}
              </section>
              <aside>
                <div className="card">
                  <h4>Trust topology</h4>
                  <p className="muted small">Only the {data.country} sub-graph. Click a document card to highlight its evidence.</p>
                  <GraphView nodes={data.subgraph.nodes} edges={data.subgraph.edges} focus={selected} />
                </div>
                <div className="card">
                  <h4>Who can help when documents are not enough</h4>
                  {data.experts.length === 0 ? <p className="muted small">No matching expert in {data.country}.</p> : (
                    <ul className="experts">
                      {data.experts.map((x) => <li key={x.id}><strong>{x.name}</strong> <span className="muted small">· {x.expertise.join(", ")}</span></li>)}
                    </ul>
                  )}
                </div>
              </aside>
            </div>
          )}
        </>
      )}

      {flagDoc && <FlagConflictForm doc={flagDoc} onSubmit={flag} onCancel={() => setFlagDoc(null)} />}
      {toast && <div className="toast" role="status">{toast}</div>}
    </main>
  );
}
