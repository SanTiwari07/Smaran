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

export interface ContestedGroup {
  entity_key: string;
  versions: Memory[];
}
