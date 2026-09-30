"use client";

import type { GraphEdge, GraphNode } from "@/lib/types";

const TYPE_CLASS: Record<string, string> = {
  Document: "n-doc", Employee: "n-emp", Country: "n-country", TeamsChat: "n-chat", Verification: "n-verif",
};

const W = 640, H = 420, CX = W / 2, CY = H / 2;

/** Radial layout: country in the middle, documents on an inner ring, evidence on the outer ring. */
function layout(nodes: GraphNode[], edges: GraphEdge[]) {
  const pos = new Map<string, { x: number; y: number }>();
  const docs = nodes.filter((n) => n.type === "Document");
  const country = nodes.find((n) => n.type === "Country");
  if (country) pos.set(country.id, { x: CX, y: CY });
  docs.forEach((d, i) => {
    const a = (2 * Math.PI * i) / Math.max(docs.length, 1) - Math.PI / 2;
    const r = docs.length === 1 ? 0 : 95;
    pos.set(d.id, { x: CX + r * Math.cos(a) + (docs.length === 1 ? 0 : 0), y: CY + r * Math.sin(a) + (docs.length === 1 ? -60 : 0) });
  });
  const outer = nodes.filter((n) => !pos.has(n.id));
  // order outer nodes by the angle of the document they hang off, so edges don't cross much
  const anchor = (id: string) => {
    const e = edges.find((e) => e.target === id && pos.has(e.source));
    const p = e ? pos.get(e.source)! : { x: CX, y: CY - 1 };
    return Math.atan2(p.y - CY, p.x - CX);
  };
  outer.sort((a, b) => anchor(a.id) - anchor(b.id));
  outer.forEach((n, i) => {
    const a = (2 * Math.PI * i) / Math.max(outer.length, 1) - Math.PI / 2;
    pos.set(n.id, { x: CX + 185 * Math.cos(a), y: CY + 165 * Math.sin(a) });
  });
  return pos;
}

export default function GraphView({ nodes, edges, focus }: { nodes: GraphNode[]; edges: GraphEdge[]; focus?: string }) {
  if (!nodes.length) return null;
  const pos = layout(nodes, edges);
  const near = new Set<string>();
  if (focus) {
    near.add(focus);
    edges.forEach((e) => { if (e.source === focus) near.add(e.target); if (e.target === focus) near.add(e.source); });
  }
  const dim = (id: string) => (focus && !near.has(id) ? 0.25 : 1);

  return (
    <div className="graph">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Country-scoped trust graph">
        <defs>
          <marker id="arrow" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M0,0 L10,5 L0,10 z" className="arrowhead" />
          </marker>
        </defs>
        {edges.map((e, i) => {
          const a = pos.get(e.source), b = pos.get(e.target);
          if (!a || !b) return null;
          const dx = b.x - a.x, dy = b.y - a.y, len = Math.hypot(dx, dy) || 1;
          const bx = b.x - (dx / len) * 14, by = b.y - (dy / len) * 14;
          return (
            <g key={i} opacity={Math.min(dim(e.source), dim(e.target))}>
              <line x1={a.x} y1={a.y} x2={bx} y2={by} className={`edge e-${e.type}`} markerEnd="url(#arrow)" />
            </g>
          );
        })}
        {nodes.map((n) => {
          const p = pos.get(n.id)!;
          const label = n.label.length > 26 ? n.label.slice(0, 25) + "…" : n.label;
          return (
            <g key={n.id} transform={`translate(${p.x},${p.y})`} opacity={dim(n.id)}>
              <title>{`${n.type}: ${n.label}`}</title>
              <circle r={n.type === "Document" ? 11 : n.type === "Country" ? 14 : 8}
                className={`node ${TYPE_CLASS[n.type] ?? ""} ${n.active === false ? "n-inactive" : ""}`} />
              <text y={n.type === "Document" ? 24 : 20} textAnchor="middle" className="node-label">{label}</text>
            </g>
          );
        })}
      </svg>
      <div className="legend">
        <span><i className="dot n-doc" />Document</span>
        <span><i className="dot n-emp" />Expert</span>
        <span><i className="dot n-chat" />Teams chat</span>
        <span><i className="dot n-verif" />Verification</span>
        <span><i className="dot n-country" />Country</span>
        <span><i className="line e-Contradicted_By" />Contradicted_By</span>
      </div>
    </div>
  );
}
