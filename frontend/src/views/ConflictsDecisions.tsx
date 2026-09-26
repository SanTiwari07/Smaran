import { Gavel, Scale, ScrollText } from "lucide-react";
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
    <div className="rounded-xl border border-red-200 bg-red-50/40 p-4 dark:border-red-900 dark:bg-red-950/20">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Badge tone="red">contested</Badge>
        <span className="font-mono text-sm">{g.entity_key}</span>
        <span className="text-xs text-stone-500">{g.versions.length} versions written independently offline</span>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        {g.versions.map((v) => (
          <div key={v.op_id} className="flex flex-col rounded-lg border border-stone-200 bg-white p-3 dark:border-stone-700 dark:bg-stone-900">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <Badge tone="violet">device {v.device_id}</Badge>
              <CritBadge level={v.criticality} />
              <span className="num ml-auto text-xs text-stone-500">{clock(v.valid_from)}</span>
            </div>
            <p className="mb-2 flex-1 text-sm">{v.text}</p>
            <p className="mb-2 font-mono text-xs text-stone-400">{v.op_id} · vv {vvText(v.vv)}</p>
            <Button variant="secondary" disabled={busy} onClick={() => resolve(v.op_id)}>
              <Gavel size={14} />Keep this
            </Button>
          </div>
        ))}
      </div>
      <form className="mt-3 flex gap-2" onSubmit={(e) => { e.preventDefault(); if (custom.trim()) resolve(undefined, custom); }}>
        <input aria-label="Write a new status" className={inputCls} value={custom} onChange={(e) => setCustom(e.target.value)}
          placeholder="…or write the verified status" />
        <Button type="submit" disabled={busy || !custom.trim()}>Resolve</Button>
      </form>
      <ErrorNote error={err} />
      <div className="mt-3 grid gap-2 text-sm md:grid-cols-2">
        <div className="rounded-lg bg-stone-100 p-3 dark:bg-stone-800/60">
          <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-stone-500">Naive merge (latest timestamp wins)</div>
          Silently shows: <span className="italic">“{naive.text}”</span>. Device {g.versions.find((v) => v !== naive)?.device_id}'s report is lost,
          and a skewed clock could pick the wrong one.
        </div>
        <div className="rounded-lg bg-emerald-50 p-3 dark:bg-emerald-950/40">
          <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-emerald-700 dark:text-emerald-400">Themis</div>
          Version vectors show neither device saw the other's report. Both are kept and flagged for a person to decide.
        </div>
      </div>
    </div>
  );
}

function DecisionLog({ device }: { device: string }) {
  const d = usePoll(() => api.decisions(device), [device], 1500);
  return (
    <Card icon={<ScrollText size={16} className="text-indigo-600 dark:text-indigo-400" />} title={`Argus decision log · device ${device}`}>
      {d.error && <ErrorNote error={d.error} />}
      {!d.data ? <Empty>Loading…</Empty> : d.data.length === 0 ? <Empty>No decisions yet. Write a note.</Empty> : (
        <div className="max-h-[520px] overflow-y-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-white text-left text-xs text-stone-500 dark:bg-stone-900">
              <tr><th className="py-1 font-medium">Time</th><th className="font-medium">Memory</th><th className="font-medium">Decision</th><th className="font-medium">Why</th></tr>
            </thead>
            <tbody>
              {d.data.map((r) => (
                <tr key={r.op_id} className="border-t border-stone-100 align-top dark:border-stone-800">
                  <td className="num py-1.5 pr-2 font-mono text-xs text-stone-500">{clock(r.ts)}</td>
                  <td className="pr-2">{r.text}</td>
                  <td className="pr-2">
                    <div className="flex flex-wrap gap-1">
                      <Badge tone={r.residency === "private" ? "violet" : r.residency === "sync" ? "amber" : "neutral"}>{r.residency}</Badge>
                      <CritBadge level={r.criticality} />
                    </div>
                    <div className="num mt-1 text-xs text-stone-500">{r.by} · {(r.confidence * 100).toFixed(0)}%</div>
                  </td>
                  <td className="text-xs text-stone-600 dark:text-stone-300">{r.reason}</td>
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
      <Card icon={<Scale size={16} className="text-indigo-600 dark:text-indigo-400" />} title="Themis · contested facts">
        {c.error && <ErrorNote error={`Gateway unreachable (${c.error})`} />}
        {!c.data ? <Empty>Loading…</Empty> : c.data.length === 0 ? (
          <Empty>No conflicts. When two offline devices disagree about the same machine, it shows up here instead of being guessed away.</Empty>
        ) : (
          <div className="space-y-4">
            {c.data.map((g) => <ConflictGroup key={g.entity_key} g={g} onResolved={c.refresh} />)}
          </div>
        )}
      </Card>
      <DecisionLog device={device} />
    </div>
  );
}
