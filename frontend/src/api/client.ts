// One typed client for the device and gateway APIs.
// VITE_USE_MOCK=1 (npm run dev:mock) swaps in src/mock/, so a UI bug can be told apart
// from a backend bug: if it still happens on mock data, it's in the frontend.
import type {
  ActivityItem, Audit, Belief, Benchmarks, ContestedGroup, DecisionRow, DeviceState, GatewayStats, Kind,
  LatencyProof, Memory, NoteResult, OutboxItem, Proof, SearchResult,
} from "./types";
import { mockApi } from "../mock/mock";

export const DEVICES: Record<string, string> = {
  A: import.meta.env.VITE_DEVICE_A_URL ?? "http://127.0.0.1:8001",
  B: import.meta.env.VITE_DEVICE_B_URL ?? "http://127.0.0.1:8002",
};
export const GATEWAY: string = import.meta.env.VITE_GATEWAY_URL ?? "http://127.0.0.1:8000";
export const USE_MOCK = import.meta.env.VITE_USE_MOCK === "1";

async function req<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, { ...init, headers: { "content-type": "application/json", ...init?.headers } });
  if (!r.ok) {
    let detail = r.statusText;
    try { detail = (await r.json()).detail ?? detail; } catch { /* not json */ }
    throw new Error(`${r.status} ${detail}`);
  }
  return r.json() as Promise<T>;
}

const qs = (p: Record<string, string | number | boolean | undefined | null>) => {
  const s = new URLSearchParams();
  for (const [k, v] of Object.entries(p)) if (v !== undefined && v !== null && v !== "") s.set(k, String(v));
  const out = s.toString();
  return out ? `?${out}` : "";
};

const realApi = {
  state: (d: string) => req<DeviceState>(`${DEVICES[d]}/state`),
  setOnline: (d: string, online: boolean) =>
    req<DeviceState>(`${DEVICES[d]}/online`, { method: "POST", body: JSON.stringify({ online }) }),
  addNote: (d: string, note: { text: string; kind: Kind; machine: string | null; author?: string }) =>
    req<NoteResult>(`${DEVICES[d]}/notes`, { method: "POST", body: JSON.stringify(note) }),
  search: (d: string, q: string, at?: number) =>
    req<SearchResult>(`${DEVICES[d]}/search${qs({ q, at })}`),
  memories: (d: string, shard?: string) => req<(Memory & { shard: string })[]>(`${DEVICES[d]}/memories${qs({ shard })}`),
  outbox: (d: string) => req<OutboxItem[]>(`${DEVICES[d]}/outbox`),
  decisions: (d: string) => req<DecisionRow[]>(`${DEVICES[d]}/decisions`),
  activity: (d: string) => req<ActivityItem[]>(`${DEVICES[d]}/activity`),
  history: (d: string, at?: number) => req<Belief[]>(`${DEVICES[d]}/history${qs({ at })}`),
  syncNow: (d: string) => req<unknown>(`${DEVICES[d]}/sync-now`, { method: "POST" }),
  machines: (d: string) => req<string[]>(`${DEVICES[d]}/machines`),
  gwStats: () => req<GatewayStats>(`${GATEWAY}/stats`),
  gwAudit: () => req<Audit>(`${GATEWAY}/audit`),
  gwContested: () => req<ContestedGroup[]>(`${GATEWAY}/contested`),
  gwResolve: (entity_key: string, op_id?: string, text?: string) =>
    req<{ op_id: string; result: string }>(`${GATEWAY}/resolve`, {
      method: "POST", body: JSON.stringify({ entity_key, op_id, text }),
    }),
  // "Prove it" checks (re-run a headline claim live) and demo resets (auto mode)
  proveLatency: (d: string) => req<LatencyProof>(`${DEVICES[d]}/prove/latency?n=50`),
  proveConflicts: () => req<Proof>(`${GATEWAY}/prove/conflicts`),
  proveConvergence: () => req<Proof>(`${GATEWAY}/prove/convergence?runs=100`),
  proveIdempotency: () => req<Proof>(`${GATEWAY}/prove/idempotency`, { method: "POST" }),
  proveBenchmarks: () => req<Benchmarks>(`${GATEWAY}/prove/benchmarks`),
  gwReset: () => req<unknown>(`${GATEWAY}/admin/reset?seed=true`, { method: "POST" }),
  devReset: (d: string) => req<DeviceState>(`${DEVICES[d]}/admin/reset?online=true`, { method: "POST" }),
};

export type Api = typeof realApi;
export const api: Api = USE_MOCK ? mockApi : realApi;
