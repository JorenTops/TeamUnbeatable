export type Country = "BE" | "NL" | "FR" | "DE" | "UK";

export interface User { id: string; name: string; role: string; countries: string[] }

export interface Warning { code: string; severity: "high" | "medium" | "low"; message: string }

export interface Contradiction {
  chat_id: string; channel: string; text: string; source: string;
  posted_by: string | null; days_ago: number; weight: number;
  resolved_by_later_verification: boolean;
}

export interface Trust {
  score: number; band: "high" | "medium" | "low";
  components: { freshness: number; ownership: number; centrality: number; base: number; contradiction_factor: number };
  weights: { freshness: number; ownership: number; centrality: number };
  owner: { id: string; name: string; active: boolean; role: string } | null;
  last_verified_days_ago: number | null;
  endorsed_by: string[];
  contradictions: Contradiction[];
  warnings: Warning[];
  explanation: string[];
}

export interface Doc { id: string; title: string; summary: string; tags: string[]; countries: string[]; updated_at: string }

export interface Result { document: Doc; relevance: number; trust: Trust }

export interface GraphNode { id: string; type: string; label: string; active?: boolean | null }
export interface GraphEdge { source: string; target: string; type: string }

export interface QueryResponse {
  query: string; country: Country; top: Result | null; results: Result[];
  excluded_other_country: number;
  experts: { id: string; name: string; role: string; expertise: string[] }[];
  subgraph: { nodes: GraphNode[]; edges: GraphEdge[] };
}

export interface Notification { id: string; document_id: string; message: string; created_at: string; read: boolean }
