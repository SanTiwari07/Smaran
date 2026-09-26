// Shapes returned by the device and gateway APIs (docs/IMPLEMENTATION_PLAN.md section 3).

export type Shard = "krypta" | "hermes" | "agora" | "cloud";
export type Status = "current" | "superseded" | "contested";
export type Residency = "private" | "sync" | "drop";
export type Kind = "status" | "observation" | "fix" | "personal" | "manual";

export interface Decision {
  residency: Residency;
  criticality: number;
  confidence: number;
  by: string;
  reason: string;
}

export interface Memory {
  op_id: string;
  entity_key: string | null;
  machine: string | null;
  kind: Kind;
  text: string;
  device_id: string;
  author: string;
  vv: Record<string, number>;
  seq: number;
  valid_from: number;
  known_from?: number;
  valid_to?: number | null;
  superseded_by: string | null;
  status: Status;
  residency: Residency;
  criticality: number;
  decision: Decision;
  server_seq?: number;
  shard?: Shard;
}

export interface DeviceState {
  device_id: string;
  online: boolean;
  outbox_depth: number;
  last_sync: number | null;
  last_error: string | null;
  last_server_seq: number;
  bytes_sent: number;
  acked: number;
  /** What the last process start found: unacknowledged outbox ops it will send again. */
  recovery: { ts: number; pending: number; restored: number } | null;
  counts: { krypta: number; hermes: number; agora: number };
  contested: number;
  classifier: string;
  embedder: string;
}

export interface SearchHit {
  payload: Memory;
  shard: Shard;
  rrf: number;
  dense_score: number | null;
}

export interface SearchResult {
  results: SearchHit[];
  top_dense: number;
  latency_ms: number;
  search_ms: number;
  embed_ms: number;
  answered: "local" | "escalated";
}

export interface NoteResult {
  memory: Memory;
  decision: Decision;
  shard: Shard | null;
}

export interface OutboxItem {
  op_id: string;
  criticality: number;
  seq: number;
  attempts: number;
  text: string;
}

export interface DecisionRow {
  ts: number;
  op_id: string;
  text: string;
  by: string;
  residency: Residency;
  criticality: number;
  confidence: number;
  reason: string;
}

export interface ActivityItem {
  ts: number;
  device: string;
  kind: string;
  [k: string]: unknown;
}

export interface Belief {
  entity_key: string;
  status: "current" | "contested";
  versions: Memory[];
}

export interface GatewayStats {
  server: string;
  points: number;
  server_seq: number;
  contested: number;
  devices: { device_id: string; bytes: number; ops: number; duplicates: number; rejected: number; last_seen: number }[];
}

export interface Audit {
  total: number;
  private_count: number;
  pii_hits: number;
  offenders: string[];
  ok: boolean;
}

/** A "Prove it" check result: `ok` plus the measured fields of that check. */
export interface Proof {
  ok: boolean;
  command?: string;
  error?: string;
  [k: string]: unknown;
}

export interface LatencyProof extends Proof {
  queries: number;
  memories: number;
  network: string;
  search_p50_ms: number;
  search_p95_ms: number;
  total_p50_ms: number;
}

export interface ModeScores { "hit@1": number; "hit@5": number; mrr: number; n: number }

export interface Benchmarks {
  skipped?: string;
  generated?: number;
  retrieval?: { queries: number; corpus: number; modes: Record<"hybrid" | "dense" | "bm25", { all: ModeScores }> };
  bandwidth?: { saved_by_selection_pct: number; saved_total_pct: number; avg_op_bytes_json: number; avg_op_bytes_f16: number };
  snapshots?: { skipped?: string; partial_snapshot_bytes?: number; full_snapshot_after_bytes?: number; partial_vs_full_pct?: number };
  latency?: { search_p50_ms: number; search_p95_ms: number; memories: number };
}

export interface ContestedGroup {
  entity_key: string;
  versions: Memory[];
}
