// In-memory stand-in for the device + gateway APIs (npm run dev:mock).
// Same contracts as the real backend, much simpler logic. Good enough to build and debug UI.
import type { Api } from "../api/client";
import type {
  ActivityItem, Belief, ContestedGroup, DecisionRow, DeviceState, Kind, Memory, NoteResult, SearchResult, Shard,
} from "../api/types";

type Dev = { id: string; online: boolean; mem: Memory[]; outbox: string[]; decisions: DecisionRow[]; activity: ActivityItem[]; seq: number; lastSync: number | null };
const now = () => Date.now() / 1000;
const PII = /(\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}|[\w.+-]+@[\w-]+\.[\w.-]+/;
const SAFETY = /smoke|spark|fire|leak|injur|overheat|burn|lockout|gas/i;
const server: Memory[] = [];
const devs: Record<string, Dev> = {};

function mk(p: Partial<Memory> & { op_id: string; text: string }): Memory {
  return {
    entity_key: null, machine: null, kind: "manual", device_id: "fleet", author: "manual", vv: {}, seq: 0,
    valid_from: now() - 86400, known_from: now() - 86400, valid_to: null, superseded_by: null, status: "current",
    residency: "sync", criticality: 0, decision: { residency: "sync", criticality: 0, confidence: 1, by: "seed", reason: "fleet knowledge" },
    ...p,
  };
}

[
  { op_id: "FLEET-0001", text: "CNC-07 status: running normally at last inspection", kind: "status" as Kind, machine: "CNC-07", entity_key: "machine:CNC-07/status" },
  { op_id: "FLEET-0006", text: "CNC-07 manual: bearing vibration above 4.5 mm/s at high RPM means bearing wear", machine: "CNC-07" },
  { op_id: "FLEET-0012", text: "LATHE-03 manual: coolant pump leak requires lockout tagout before replacing the seal", machine: "LATHE-03", criticality: 2 },
].forEach((p) => server.push(mk(p)));

for (const id of ["A", "B"]) {
  devs[id] = { id, online: true, mem: server.map((m) => ({ ...m, shard: "agora" as Shard })), outbox: [], decisions: [], activity: [], seq: 0, lastSync: now() };
}

const log = (d: Dev, kind: string, extra: Record<string, unknown> = {}) =>
  d.activity.unshift({ ts: now(), device: d.id, kind, ...extra });

function resolveEntity(list: Memory[], ek: string) {
  const vs = list.filter((m) => m.entity_key === ek && m.status !== "superseded");
  const byDevice = new Set(vs.map((v) => v.device_id).filter((x) => x !== "fleet"));
  if (byDevice.size > 1) vs.filter((v) => v.device_id !== "fleet").forEach((v) => (v.status = "contested"));
  vs.filter((v) => v.device_id === "fleet" && byDevice.size > 0).forEach((v) => { v.status = "superseded"; v.valid_to = now(); });
}

function sync(d: Dev) {
  if (!d.online) return;
  for (const id of d.outbox) {
    const m = d.mem.find((x) => x.op_id === id)!;
    if (!server.find((s) => s.op_id === id)) server.push({ ...m, shard: undefined });
    log(d, "synced", { op_id: id, result: "applied" });
  }
  d.outbox = [];
  server.filter((m) => m.entity_key).forEach((m) => resolveEntity(server, m.entity_key!));
  for (const s of server) {
    const local = d.mem.find((x) => x.op_id === s.op_id);
    if (local) Object.assign(local, { status: s.status, superseded_by: s.superseded_by, shard: "agora" });
    else d.mem.push({ ...s, shard: "agora", known_from: now() });
  }
  d.lastSync = now();
}

const state = (d: Dev): DeviceState => ({
  device_id: d.id, online: d.online, outbox_depth: d.outbox.length, last_sync: d.lastSync, last_error: null,
  last_server_seq: server.length, bytes_sent: d.outbox.length * 1900, acked: d.seq - d.outbox.length,
  recovery: { ts: now() - 600, pending: 0, restored: 0 },
  counts: { krypta: d.mem.filter((m) => m.shard === "krypta").length, hermes: d.mem.filter((m) => m.shard === "hermes").length, agora: d.mem.filter((m) => m.shard === "agora").length },
  contested: d.mem.filter((m) => m.status === "contested").length, classifier: "mock", embedder: "mock",
});

const ok = <T,>(v: T) => new Promise<T>((r) => setTimeout(() => r(structuredClone(v)), 80));

export const mockApi: Api = {
  state: (id) => ok(state(devs[id])),
  setOnline: (id, online) => { const d = devs[id]; d.online = online; log(d, online ? "online" : "offline"); if (online) { sync(d); Object.values(devs).forEach(sync); } return ok(state(d)); },
  addNote: (id, n) => {
    const d = devs[id];
    d.seq += 1;
    const op_id = `${id}-${String(d.seq).padStart(6, "0")}`;
    const pii = PII.test(n.text) || n.kind === "personal";
    const crit = SAFETY.test(n.text) ? 2 : 0;
    const decision = pii
      ? { residency: "private" as const, criticality: crit, confidence: 1, by: "pii_rule", reason: "PII rule matched: phone_in" }
      : { residency: "sync" as const, criticality: crit, confidence: 0.93, by: "classifier", reason: "mock proposed sync (0.93)" };
    const ek = !pii && n.machine && n.kind === "status" ? `machine:${n.machine}/status` : null;
    const m = mk({ op_id, text: n.text, kind: n.kind, machine: n.machine, entity_key: ek, device_id: id, author: `tech-${id}`, vv: { [id]: d.seq }, seq: d.seq, valid_from: now(), known_from: now(), residency: decision.residency, criticality: crit, decision, shard: pii ? "krypta" : "hermes" });
    d.mem.push(m);
    if (!pii) d.outbox.push(op_id);
    if (ek) d.mem.filter((x) => x.entity_key === ek && x.op_id !== op_id && x.status !== "superseded").forEach((x) => { x.status = "superseded"; x.superseded_by = op_id; x.valid_to = now(); });
    d.decisions.unshift({ ts: now(), op_id, text: n.text, ...decision });
    log(d, "decision", { op_id, residency: decision.residency, by: decision.by, text: n.text });
    sync(d);
    return ok<NoteResult>({ memory: m, decision, shard: m.shard! });
  },
  search: (id, q) => {
    const words = q.toLowerCase().split(/\W+/).filter(Boolean);
    const hits = devs[id].mem.filter((m) => m.status !== "superseded")
      .map((m) => ({ m, s: words.filter((w) => m.text.toLowerCase().includes(w)).length / Math.max(words.length, 1) }))
      .filter((x) => x.s > 0).sort((a, b) => b.s - a.s).slice(0, 10);
    return ok<SearchResult>({ results: hits.map(({ m, s }, i) => ({ payload: m, shard: m.shard!, rrf: 1 / (61 + i), dense_score: +(0.5 + s / 2).toFixed(3) })), top_dense: hits.length ? 0.8 : 0, latency_ms: 3.2, search_ms: 1.1, embed_ms: 2.1, answered: "local" });
  },
  memories: (id, shard) => ok(devs[id].mem.filter((m) => !shard || m.shard === shard) as (Memory & { shard: string })[]),
  outbox: (id) => ok(devs[id].outbox.map((op) => { const m = devs[id].mem.find((x) => x.op_id === op)!; return { op_id: op, criticality: m.criticality, seq: m.seq, attempts: 0, text: m.text }; })),
  decisions: (id) => ok(devs[id].decisions),
  activity: (id) => ok(devs[id].activity.slice(0, 100)),
  history: (id, at) => {
    const t = at ?? now();
    const groups: Record<string, Memory[]> = {};
    devs[id].mem.filter((m) => m.entity_key && (m.known_from ?? 0) <= t && (m.valid_to == null || m.valid_to > t))
      .forEach((m) => (groups[m.entity_key!] ??= []).push(m));
    return ok<Belief[]>(Object.entries(groups).map(([entity_key, versions]) => ({ entity_key, status: versions.length > 1 ? "contested" : "current", versions })));
  },
  syncNow: (id) => { sync(devs[id]); return ok({ ok: true }); },
  machines: () => ok(["CNC-07", "CNC-12", "LATHE-03", "PRESS-02", "ROBOT-ARM-5"]),
  gwStats: () => ok({ server: "mock", points: server.length, server_seq: server.length, contested: server.filter((m) => m.status === "contested").length, devices: Object.values(devs).map((d) => ({ device_id: d.id, bytes: 0, ops: d.seq, duplicates: 0, rejected: 0, last_seen: now() })) }),
  gwAudit: () => ok({ total: server.length, private_count: 0, pii_hits: 0, offenders: [], ok: true }),
  gwContested: () => {
    const g: Record<string, Memory[]> = {};
    server.filter((m) => m.status === "contested").forEach((m) => (g[m.entity_key!] ??= []).push(m));
    return ok<ContestedGroup[]>(Object.entries(g).map(([entity_key, versions]) => ({ entity_key, versions })));
  },
  proveLatency: () => ok({ ok: true, queries: 50, memories: 3, network: "none", search_p50_ms: 1.1, search_p95_ms: 1.9, total_p50_ms: 3.2 }),
  proveConflicts: () => ok({ ok: true, cases: 50, themis_correct: 50, naive_correct: 13, ms: 4 }),
  proveConvergence: () => ok({ ok: true, runs: 100, devices: 5, converged: 100, lost_concurrent_edits: 0, ms: 900 }),
  proveIdempotency: () => ok({ ok: true, op_id: "FLEET-0019", result: "duplicate", points_before: server.length, points_after: server.length }),
  proveBenchmarks: () => ok({ skipped: "mock API: no benchmark results" }),
  gwReset: () => { server.splice(3); server.forEach((m) => Object.assign(m, { status: "current", superseded_by: null, valid_to: null })); return ok({ ok: true }); },
  devReset: (id) => {
    devs[id] = { id, online: true, mem: server.map((m) => ({ ...m, shard: "agora" as Shard })), outbox: [], decisions: [], activity: [], seq: 0, lastSync: now() };
    return ok(state(devs[id]));
  },
  gwResolve: (entity_key, op_id, text) => {
    const vs = server.filter((m) => m.entity_key === entity_key && m.status === "contested");
    const chosen = vs.find((v) => v.op_id === op_id);
    const sup = mk({ op_id: `SUP-${String(server.length).padStart(6, "0")}`, text: text ?? chosen?.text ?? "", kind: "status", entity_key, machine: vs[0]?.machine ?? null, device_id: "supervisor", author: "supervisor", valid_from: now() });
    vs.forEach((v) => { v.status = "superseded"; v.superseded_by = sup.op_id; });
    server.push(sup);
    Object.values(devs).forEach((d) => { d.mem.filter((m) => m.entity_key === entity_key && m.status !== "superseded").forEach((m) => { m.status = "superseded"; m.valid_to = now(); }); sync(d); });
    return ok({ op_id: sup.op_id, result: "applied" });
  },
};
