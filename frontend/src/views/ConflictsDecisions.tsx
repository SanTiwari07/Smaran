import { useState } from "react";
import { api } from "../api/client";
import type { ContestedGroup, Memory } from "../api/types";
import {
  Badge, Button, Card, clock, CritBadge, Empty, ErrorNote, inputCls, vvText,
} from "../components/ui";
import { usePoll } from "../hooks/usePoll";

// What Qdrant's reference pattern (latest timestamp wins) would silently show instead.
const naivePick = (vs: Memory[]) => vs.reduce((a, b) => (b.valid_from > a.valid_from ? b : a));

function ConflictGroup({ g, onResolved }: { g: ContestedGroup; onResolved: () => void }) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [custom, setCustom] = useState("");
  const naive = naivePick(g.versions);

  const resolve = async (op_id?: string, text?: string) => {
    setBusy(true);
    setErr(null);
    try { await api.gwResolve(g.entity_key, op_id, text); onResolved(); }
    catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(false); }
  };

  return (
    <div className="border-l-2 border-alert pl-4">
      <div className="mb-3 flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="font-mono text-sm">{g.entity_key}</span>
        <span className="text-xs text-muted">{g.versions.length} versions written independently offline</span>
      </div>
      <div className="grid gap-px border border-line bg-line md:grid-cols-2">
        {g.versions.map((v) => (
          <div key={v.op_id} className="flex flex-col bg-panel p-3">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <span className="text-sm font-medium">Device {v.device_id}</span>
              <CritBadge level={v.criticality} />
              <span className="num ml-auto font-mono text-xs text-faint">{clock(v.valid_from)}</span>
            </div>
            <p className="mb-3 flex-1 text-sm">{v.text}</p>
            <div className="flex items-center justify-between gap-2">
              <span className="font-mono text-[11px] text-faint">{v.op_id} / vv {vvText(v.vv)}</span>
              <Button variant="secondary" disabled={busy} onClick={() => resolve(v.op_id)}>Keep this</Button>
            </div>
          </div>
        ))}
      </div>
      <form className="mt-3 flex gap-2" onSubmit={(e) => { e.preventDefault(); if (custom.trim()) resolve(undefined, custom); }}>
        <input aria-label="Write a new status" className={inputCls} value={custom} onChange={(e) => setCustom(e.target.value)}
          placeholder="Or write the verified status" />
        <Button type="submit" disabled={busy || !custom.trim()}>Resolve</Button>
      </form>
      <ErrorNote error={err} />
      <dl className="mt-4 grid gap-4 text-sm md:grid-cols-2">
        <div>
          <dt className="label mb-1">Naive merge (latest timestamp wins)</dt>
          <dd className="text-muted">
            Silently shows “{naive.text}”. Device {g.versions.find((v) => v !== naive)?.device_id}'s report is lost,
            and a skewed clock could pick the wrong one.
          </dd>
        </div>
        <div>
          <dt className="label mb-1 text-ink">Themis</dt>
          <dd>Version vectors show neither device saw the other's report. Both are kept and flagged for a person to decide.</dd>
        </div>
      </dl>
    </div>
  );
}

function DecisionLog({ device }: { device: string }) {
  const d = usePoll(() => api.decisions(device), [device], 1500);
  return (
    <Card title={`Argus decision log, device ${device}`}>
      {d.error && <ErrorNote error={d.error} />}
      {!d.data ? <Empty>Loading…</Empty> : d.data.length === 0 ? <Empty>No decisions yet. Write a note.</Empty> : (
        <div className="max-h-[560px] overflow-y-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-panel text-left">
              <tr className="label [&>th]:pb-1.5 [&>th]:pr-3 [&>th]:font-medium">
                <th>Time</th><th>Memory</th><th>Decision</th><th>Why</th>
              </tr>
            </thead>
            <tbody>
              {d.data.map((r) => (
                <tr key={r.op_id} className="border-t border-line align-top [&>td]:py-2 [&>td]:pr-3">
                  <td className="num font-mono text-xs text-faint">{clock(r.ts)}</td>
                  <td>{r.text}</td>
                  <td>
                    <div className="flex flex-wrap gap-1">
                      <Badge tone={r.residency === "private" ? "gold" : "neutral"}>{r.residency}</Badge>
                      <CritBadge level={r.criticality} />
                    </div>
                    <div className="num mt-1 text-xs text-muted">{r.by}, {(r.confidence * 100).toFixed(0)}%</div>
                  </td>
                  <td className="text-xs text-muted">{r.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

export default function ConflictsDecisions({ device }: { device: string }) {
  const c = usePoll(() => api.gwContested(), [], 1500);
  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <Card title="Themis, contested facts"
        right={c.data && c.data.length > 0 && <span className="num text-xs text-alert">{c.data.length} open</span>}>
        {c.error && <ErrorNote error={`Gateway unreachable (${c.error})`} />}
        {!c.data ? <Empty>Loading…</Empty> : c.data.length === 0 ? (
          <Empty>No conflicts. When two offline devices disagree about the same machine, it shows up here instead of being guessed away.</Empty>
        ) : (
          <div className="space-y-8">
            {c.data.map((g) => <ConflictGroup key={g.entity_key} g={g} onResolved={c.refresh} />)}
          </div>
        )}
      </Card>
      <DecisionLog device={device} />
    </div>
  );
}
