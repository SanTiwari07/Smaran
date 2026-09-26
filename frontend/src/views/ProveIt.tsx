// "Prove it": every headline claim with a button that re-runs its check against the live
// system, plus the last benchmark scoreboard. A claim you can't re-run doesn't belong here.
import { useState } from "react";
import { api } from "../api/client";
import type { Audit, LatencyProof, Proof } from "../api/types";
import { Badge, bytes, Button, Card, Empty, ErrorNote } from "../components/ui";
import { usePoll } from "../hooks/usePoll";

type Check = {
  id: string;
  claim: string;
  command: string;
  run: () => Promise<{ ok: boolean; detail: string }>;
};

const n = (v: unknown) => String(v);

const CHECKS: Check[] = [
  {
    id: "privacy", claim: "Private data never reaches Qdrant Server", command: "GET /audit (scans the server collection)",
    run: async () => {
      const a: Audit = await api.gwAudit();
      return { ok: a.ok, detail: `${a.private_count} private records, ${a.pii_hits} PII matches in ${a.total} server memories` };
    },
  },
  {
    id: "latency", claim: "Device A searches offline in milliseconds", command: "GET device A /prove/latency (50 hybrid queries, no network)",
    run: async () => {
      const r: LatencyProof = await api.proveLatency("A");
      return { ok: r.ok, detail: `search p50 ${r.search_p50_ms} ms, p95 ${r.search_p95_ms} ms over ${r.memories} memories (with embedding p50 ${r.total_p50_ms} ms)` };
    },
  },
  {
    id: "conflicts", claim: "Concurrent edits are flagged, never silently lost", command: "python -m bench.bench conflicts",
    run: async () => {
      const r: Proof = await api.proveConflicts();
      return { ok: r.ok, detail: `Themis ${n(r.themis_correct)}/${n(r.cases)} · last-writer-wins ${n(r.naive_correct)}/${n(r.cases)} (clocks skewed ±10 min)` };
    },
  },
  {
    id: "convergence", claim: "Every replica converges to the same answer", command: "python -m bench.bench convergence",
    run: async () => {
      const r: Proof = await api.proveConvergence();
      return { ok: r.ok, detail: `${n(r.converged)}/${n(r.runs)} random runs identical across ${n(r.devices)} devices + gateway, ${n(r.lost_concurrent_edits)} edits lost` };
    },
  },
  {
    id: "idempotency", claim: "A resent op is never stored twice", command: "POST /prove/idempotency (resends the newest op)",
    run: async () => {
      const r: Proof = await api.proveIdempotency();
      if (r.error) return { ok: false, detail: r.error };
      return { ok: r.ok, detail: `resent ${n(r.op_id)}: ${n(r.result)}; server points ${n(r.points_before)} → ${n(r.points_after)}` };
    },
  },
];

function CheckRow({ c }: { c: Check }) {
  const [state, setState] = useState<{ ok: boolean; detail: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const go = async () => {
    setBusy(true);
    setErr(null);
    try { setState(await c.run()); }
    catch (e) { setErr(e instanceof Error ? e.message : String(e)); setState(null); }
    finally { setBusy(false); }
  };
  return (
    <li className="border-t border-line py-2.5 first:border-t-0">
      <div className="flex items-center gap-3">
        <span className="min-w-0 flex-1 text-sm">{c.claim}</span>
        {state && <Badge tone={state.ok ? "ok" : "alert"}>{state.ok ? "pass" : "fail"}</Badge>}
        <Button variant="secondary" disabled={busy} onClick={go}>{busy ? "Running…" : "Run"}</Button>
      </div>
      {state && <p className="num mt-1 text-xs text-muted">{state.detail}</p>}
      <ErrorNote error={err} />
      <p className="mt-0.5 font-mono text-[11px] text-faint">{c.command}</p>
    </li>
  );
}

function Scoreboard() {
  const b = usePoll(() => api.proveBenchmarks(), [], 30_000).data;
  if (!b) return <Empty>Loading…</Empty>;
  if (b.skipped) return <p className="text-sm text-muted">{b.skipped}</p>;
  const r = b.retrieval;
  const s = b.snapshots;
  return (
    <div className="space-y-3 text-sm">
      {r && (
        <table className="num w-full">
          <thead className="label text-left">
            <tr className="[&>th]:pb-1 [&>th]:font-medium"><th>Retrieval, {r.queries} golden queries</th><th>hit@1</th><th>hit@5</th><th>MRR</th></tr>
          </thead>
          <tbody>
            {(["hybrid", "dense", "bm25"] as const).map((m) => (
              <tr key={m} className={`border-t border-line [&>td]:py-1 ${m === "hybrid" ? "font-medium" : "text-muted"}`}>
                <td>{m === "hybrid" ? "hybrid (shipped)" : `${m} only`}</td>
                <td>{r.modes[m].all["hit@1"]}</td><td>{r.modes[m].all["hit@5"]}</td><td>{r.modes[m].all.mrr}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {b.bandwidth && (
        <p className="text-muted">
          Bandwidth vs syncing every note: <span className="text-ink">{b.bandwidth.saved_total_pct}% saved</span> (selection alone {b.bandwidth.saved_by_selection_pct}%;
          an op is {bytes(b.bandwidth.avg_op_bytes_f16)} with float16 vectors vs {bytes(b.bandwidth.avg_op_bytes_json)} as JSON floats)
        </p>
      )}
      {s && !s.skipped && s.partial_snapshot_bytes !== undefined && (
        <p className="text-muted">
          Partial snapshot refresh: <span className="text-ink">{bytes(s.partial_snapshot_bytes)}</span> instead of a {bytes(s.full_snapshot_after_bytes ?? 0)} full
          snapshot ({s.partial_vs_full_pct}%)
        </p>
      )}
      {b.generated && <p className="font-mono text-[11px] text-faint">from bench/results.json, {new Date(b.generated * 1000).toLocaleString()} · python -m bench.bench</p>}
    </div>
  );
}

export default function ProveIt() {
  return (
    <Card title="Prove it">
      <ul>{CHECKS.map((c) => <CheckRow key={c.id} c={c} />)}</ul>
      <div className="mt-3 border-t border-line pt-3">
        <h3 className="label mb-2">Last benchmark run</h3>
        <Scoreboard />
      </div>
    </Card>
  );
}
