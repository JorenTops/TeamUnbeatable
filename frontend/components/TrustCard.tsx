"use client";

import type { Result, User } from "@/lib/types";

const CODE_LABEL: Record<string, string> = {
  NO_OWNER: "No owner",
  OWNER_INACTIVE: "Owner left",
  CONTRADICTED: "Contradicted in Teams",
  STALE: "Stale",
  NEVER_VERIFIED: "Never verified",
};

function Meter({ label, value, weight }: { label: string; value: number; weight?: number }) {
  return (
    <div className="meter">
      <div className="meter-head">
        <span>{label}{weight !== undefined && <span className="muted"> ×{weight}</span>}</span>
        <span className="mono">{value.toFixed(2)}</span>
      </div>
      <div className="meter-track"><div className="meter-fill" style={{ width: `${Math.round(value * 100)}%` }} /></div>
    </div>
  );
}

export function TrustScore({ score, band }: { score: number; band: string }) {
  return (
    <div className={`score score-${band}`} aria-label={`Trust score ${score} out of 100, ${band}`}>
      <span className="score-num">{Math.round(score)}</span>
      <span className="score-band">{band}</span>
    </div>
  );
}

export default function TrustCard({
  result, primary, user, onFlag, onVerify, selected, onSelect,
}: {
  result: Result; primary?: boolean; user: User;
  onFlag: () => void; onVerify: () => void; selected: boolean; onSelect: () => void;
}) {
  const { document: doc, trust } = result;
  const critical = trust.warnings.filter((w) => w.code === "NO_OWNER" || w.code === "CONTRADICTED" || w.code === "OWNER_INACTIVE");
  const canVerify = user.role === "admin" || user.role === "expert" || trust.owner?.id === user.id;
  const isOwner = trust.owner?.id === user.id;

  return (
    <article className={`card ${primary ? "card-primary" : ""} ${selected ? "card-selected" : ""}`} onClick={onSelect}>
      {critical.length > 0 && (
        <div className="alert" role="alert">
          <span className="alert-icon" aria-hidden>!</span>
          <div>
            <strong>Do not rely on this without checking.</strong>
            <ul>{critical.map((w) => <li key={w.code}>{w.message}</li>)}</ul>
          </div>
        </div>
      )}

      <div className="card-head">
        <div>
          {primary && <div className="eyebrow">Best answer for this country</div>}
          <h3>{doc.title}</h3>
          <p className="summary">{doc.summary}</p>
          <div className="chips">
            {doc.countries.map((c) => <span key={c} className="chip chip-country">{c}</span>)}
            {trust.warnings.map((w) => (
              <span key={w.code} className={`chip chip-warn chip-${w.severity}`}>{CODE_LABEL[w.code] ?? w.code}</span>
            ))}
          </div>
        </div>
        <TrustScore score={trust.score} band={trust.band} />
      </div>

      <div className="facts">
        <div><span className="muted">Owner</span><br />
          {trust.owner ? <>{trust.owner.name}{!trust.owner.active && <span className="bad"> (left)</span>}</> : <span className="bad">Nobody</span>}
        </div>
        <div><span className="muted">Last verified</span><br />
          {trust.last_verified_days_ago === null ? <span className="bad">Never</span> : `${Math.round(trust.last_verified_days_ago)} days ago`}
        </div>
        <div><span className="muted">Endorsed by</span><br />{trust.endorsed_by.length ? trust.endorsed_by.join(", ") : "—"}</div>
      </div>

      {primary || selected ? (
        <>
          <div className="meters">
            <Meter label="Freshness" value={trust.components.freshness} weight={trust.weights.freshness} />
            <Meter label="Ownership" value={trust.components.ownership} weight={trust.weights.ownership} />
            <Meter label="Graph centrality" value={trust.components.centrality} weight={trust.weights.centrality} />
            <Meter label="Contradiction factor" value={trust.components.contradiction_factor} />
          </div>
          <details className="why" open={primary}>
            <summary>Why this score?</summary>
            <ol>{trust.explanation.map((e, i) => <li key={i}>{e}</li>)}</ol>
          </details>
          {trust.contradictions.length > 0 && (
            <div className="contras">
              {trust.contradictions.map((c) => (
                <blockquote key={c.chat_id} className={c.resolved_by_later_verification ? "resolved" : ""}>
                  <div className="muted small">
                    {c.channel} · {c.posted_by ?? "unknown"} · {c.days_ago < 1 ? "just now" : `${Math.round(c.days_ago)}d ago`}
                    {c.source === "manual_flag" && " · flagged in dashboard"}
                    {c.resolved_by_later_verification && " · resolved by re-verification"}
                  </div>
                  {c.text}
                </blockquote>
              ))}
            </div>
          )}
        </>
      ) : null}

      <div className="actions" onClick={(e) => e.stopPropagation()}>
        {!isOwner && <button className="btn btn-danger" onClick={onFlag}>Flag conflict</button>}
        {canVerify && <button className="btn" onClick={onVerify}>Re-verify</button>}
      </div>
    </article>
  );
}
