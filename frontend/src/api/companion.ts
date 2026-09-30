// Typed client for the companion routes (/companion/*) on each device.
import { DEVICES, GATEWAY } from "./client";

export const LABELS: Record<string, string> = { A: "Phone", B: "Laptop" };
export const label = (d: string) => LABELS[d] ?? `Device ${d}`;

async function req<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, { ...init, headers: { "content-type": "application/json", ...init?.headers } });
  if (!r.ok) {
    let detail = r.statusText;
    try { detail = (await r.json()).detail ?? detail; } catch { /* not json */ }
    throw new Error(`${r.status} ${detail}`);
  }
  return r.json() as Promise<T>;
}

export interface Step { step: string; detail: string; ms: number }
export interface Route { route: "local-slm" | "extractive" | "cloud" | "rules"; model: string; reason: string; latency_ms: number; tried?: { route: string; error: string }[] }
export interface Hit {
  payload: { op_id: string; text: string; kind: string; subject?: string | null; memory_type?: string | null; status: string; valid_from: number };
  shard: string; score: number; why: string[]; features: Record<string, number>;
}
export interface Contradiction {
  id: string; category: string; subject: string | null; subject_label: string; why: string; question: string;
  previous: { op_id: string; value: string; reason: string | null; at_text: string | null; confidence: number | null; evidence: string | null };
  new: { value: string; reason: string | null; confidence: number | null; stance: string | null };
}
export interface ActionResult {
  tool: string; args: Record<string, unknown>; risk: string; state: string; message: string; why?: string;
  verified?: boolean | null; audit_id?: number; shard?: string; residency?: string; needs_confirmation?: boolean;
  contradiction?: Contradiction; op_id?: string; found?: boolean; kept?: string;
}
export interface ConfPart { label: string; value: number; op: "start" | "add" | "multiply" }
export interface Provenance {
  op_id: string; text: string; kind: string; subject_label: string | null; status: string; shard: string;
  source: { type: string; device: string | null; request_id: string | null; quote: string; recorded_by: string | null };
  at_text: string | null; confidence: { value: number; parts: ConfPart[] };
  lifecycle: { state: string; reason: string; persistence: string };
  supporting: { op_id: string; text: string; kind: string; why: string }[];
  history: { op_id: string; text: string; status: string; at_text: string | null; device: string | null }[];
  resolution: { mode: string; by?: string } | null;
  decision?: { value: string; category: string; reason: string | null; evidence: string | null; status: string; superseded_by: string | null; supersedes: string[]; at_text: string | null };
}
export interface CtxMemory { op_id: string; text: string; kind: string; subject: string | null; score: number; why: string[]; shard: string }
export interface ChatResult {
  request_id: string; reply: string; intent: string; planner: string; steps: Step[]; actions: ActionResult[];
  retrieval: { hits: Hit[]; understanding: Record<string, unknown>; answered: string; timing_ms: Record<string, number> } | null;
  route: Route; latency_ms: number; queued: number; online: boolean; online_at_start: boolean;
  provenance: Provenance[]; context: CtxMemory[]; pending: Contradiction[];
}
export interface Explain {
  request_id: string; user_request: string; intent: string; planner: string; mode: string; online: boolean; model: string;
  active_subject: string | null; relevant_memories: CtxMemory[]; reply: string; queued: number;
  chain: { stage: string; text?: string; items?: string[] }[];
  actions: { audit_id: number; tool: string; state: string; message: string; why: string | null; verified: number | null; op_ids: string[] }[];
}
export interface LifecycleReport {
  counts: Record<"temporary" | "active" | "stale" | "archived", number>; total: number; note: string;
  examples: Record<"stale" | "archived", { op_id: string; text: string; kind: string; reason: string }[]>;
}
export interface Task { op_id: string; task_id: string; title: string; status: string; due: number | null; due_text: string | null; subject: string | null; conflict: boolean; shard: string }
export interface Briefing { items: { level: "alert" | "warn" | "info"; text: string }[]; open_tasks: number }
export interface Conflict {
  entity_key: string; label: string; why: string; explanation: string;
  versions: { op_id: string; text: string; device: string; device_label: string; at: number; at_text: string; when: string | null }[];
  evidence: { op_id: string; when: string; support_text: string } | null;
  suggestion: { op_id: string; text: string; reason: string; basis: "context" | "clock" };
}
export interface CompanionStatus {
  device: string; label: string; online: boolean; queued: number;
  ai: { local: { model: string; available: boolean; runtime: string }; cloud: { model: string; configured: boolean; usable_now: boolean }; policy: string; active_route: string };
  memory: { counts: { krypta: number; hermes: number; agora: number }; by_type: Record<string, number>; index: string; embedder: string;
    encryption: { chat_and_audit: string; key: string; shards: string } };
  sync: { queued: number; acked: number; last_sync: number | null; last_error: string | null; contested: number };
  observability: { requests: number; routes: Record<string, number>; tools: number };
}
export interface Trace {
  ts: number; request: string; route: Route; latency_ms: number; planner: string; intent: string;
  topk: { op_id: string; score: number; shard: string }[]; tools: string[]; sync: { queued: number; online: boolean };
}
export interface AuditRow { id: number; ts: number; tool: string; args: Record<string, unknown>; risk: string; state: string; message: string; verified: number | null; actor: string; op_ids: string[] }
export interface Bench {
  samples: number; memories: number; embed_ms_p50: number; embed_ms_p95: number; retrieval_ms_p50: number; retrieval_ms_p95: number;
  agent_read_action_ms_p50: number; local_slm_ms: number | null; local_slm_model: string; data_dir_mb: number; note: string;
}
export interface OutboxRow { op_id: string; criticality: number; seq: number; attempts: number; text: string }
export interface MemoryRow { shard: string; op_id: string; text: string; kind: string; memory_type?: string | null; subject?: string | null; status: string; importance?: number | null; known_from?: number }

const u = (d: string) => DEVICES[d];

export const companion = {
  chat: (d: string, text: string, prefer_cloud = false) =>
    req<ChatResult>(`${u(d)}/companion/chat`, { method: "POST", body: JSON.stringify({ text, prefer_cloud }) }),
  confirm: (d: string, audit_id: number) =>
    req<ActionResult>(`${u(d)}/companion/confirm`, { method: "POST", body: JSON.stringify({ audit_id }) }),
  tasks: (d: string) => req<Task[]>(`${u(d)}/companion/tasks`),
  briefing: (d: string) => req<Briefing>(`${u(d)}/companion/briefing`),
  conflicts: (d: string) => req<Conflict[]>(`${u(d)}/companion/conflicts`),
  status: (d: string) => req<CompanionStatus>(`${u(d)}/companion/status`),
  traces: (d: string) => req<Trace[]>(`${u(d)}/companion/traces?limit=30`),
  audit: (d: string) => req<AuditRow[]>(`${u(d)}/companion/audit?limit=40`),
  history: (d: string) => req<{ ts: number; role: string; text: string }[]>(`${u(d)}/companion/history?limit=30`),
  recall: (d: string, q: string) =>
    req<{ hits: Hit[]; timing_ms: Record<string, number>; answered: string; understanding: Record<string, unknown> }>(`${u(d)}/companion/recall?q=${encodeURIComponent(q)}&k=5`),
  explain: (d: string, q: { request_id?: string; audit_id?: number }) =>
    req<Explain>(`${u(d)}/companion/explain?${new URLSearchParams(Object.entries(q).map(([k, v]) => [k, String(v)]))}`),
  memoryExplain: (d: string, op_id: string) => req<Provenance>(`${u(d)}/companion/memory/explain?op_id=${encodeURIComponent(op_id)}`),
  resolveDecision: (d: string, id: string, keep: "new" | "old") =>
    req<ActionResult>(`${u(d)}/companion/decisions/resolve`, { method: "POST", body: JSON.stringify({ id, keep }) }),
  pending: (d: string) => req<Contradiction[]>(`${u(d)}/companion/pending`),
  lifecycle: (d: string) => req<LifecycleReport>(`${u(d)}/companion/lifecycle`),
  seedBackground: (d: string) => req<{ utterances: number }>(`${u(d)}/companion/seed-background`, { method: "POST" }),
  bench: (d: string) => req<Bench>(`${u(d)}/companion/bench?n=30`),
  seedStory: (d: string) => req<{ utterances: number; memories_written: number; tasks: number; private: number; ms: number }>(`${u(d)}/companion/seed-story`, { method: "POST" }),
  useLocalModel: (d: string, on: boolean) => req<unknown>(`${u(d)}/companion/model?use_local=${on}`, { method: "POST" }),
  warmup: (d: string) => req<{ model: string; ms: number }>(`${u(d)}/companion/warmup`, { method: "POST" }),
  outbox: (d: string) => req<OutboxRow[]>(`${u(d)}/outbox`),
  memories: (d: string) => req<MemoryRow[]>(`${u(d)}/memories`),
  setOnline: (d: string, online: boolean) => req<unknown>(`${u(d)}/online`, { method: "POST", body: JSON.stringify({ online }) }),
  syncNow: (d: string) => req<{ push: { sent?: number; results?: Record<string, number> }; pull: { pulled?: number } }>(`${u(d)}/sync-now`, { method: "POST" }),
  resetDevice: (d: string) => req<unknown>(`${u(d)}/admin/reset?online=true`, { method: "POST" }),
  resetGateway: () => req<unknown>(`${GATEWAY}/admin/reset?seed=true`, { method: "POST" }),
  resolve: (entity_key: string, op_id: string) =>
    req<{ op_id: string; result: string }>(`${GATEWAY}/resolve`, { method: "POST", body: JSON.stringify({ entity_key, op_id, author: "you" }) }),
  gwAudit: () => req<{ total: number; private_count: number; pii_hits: number; ok: boolean }>(`${GATEWAY}/audit`),
};

export const fmtTime = (ts: number) => new Date(ts * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
