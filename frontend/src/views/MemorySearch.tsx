import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import type { Kind, NoteResult, SearchResult, Shard } from "../api/types";
import {
  Badge, Button, Card, clock, CritBadge, Empty, ErrorNote, inputCls, ShardBadge, StatusBadge, vvText, WhyHere,
} from "../components/ui";
import { usePoll } from "../hooks/usePoll";

const KINDS: { value: Kind; label: string }[] = [
  { value: "observation", label: "Observation" },
  { value: "status", label: "Status update" },
  { value: "fix", label: "Fix" },
  { value: "personal", label: "Personal" },
];

function Composer({ device, onWrote }: { device: string; onWrote: () => void }) {
  const machines = usePoll(() => api.machines(device), [device], 60_000);
  const [machine, setMachine] = useState("CNC-07");
  const [kind, setKind] = useState<Kind>("observation");
  const [text, setText] = useState("");
  const [res, setRes] = useState<NoteResult | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim()) return;
    setBusy(true);
    setErr(null);
    try {
      setRes(await api.addNote(device, { text, kind, machine: machine || null, author: `tech-${device}` }));
      setText("");
      onWrote();
    } catch (e2) { setErr(e2 instanceof Error ? e2.message : String(e2)); }
    finally { setBusy(false); }
  };

  return (
    <Card title={`Remember, device ${device}`}>
      <form onSubmit={submit} className="space-y-3">
        <div className="grid grid-cols-2 gap-2">
          <select aria-label="Machine" className={inputCls} value={machine} onChange={(e) => setMachine(e.target.value)}>
            <option value="">No machine</option>
            {(machines.data ?? []).map((m) => <option key={m}>{m}</option>)}
          </select>
          <select aria-label="Note type" className={inputCls} value={kind} onChange={(e) => setKind(e.target.value as Kind)}>
            {KINDS.map((k) => <option key={k.value} value={k.value}>{k.label}</option>)}
          </select>
        </div>
        <textarea aria-label="Note" className={`${inputCls} min-h-20`} value={text} onChange={(e) => setText(e.target.value)}
          placeholder="e.g. CNC-07 bearing replaced, vibration normal" />
        <div className="flex items-center justify-between gap-2">
          <span className="text-xs text-muted">Argus decides where it lives: Krypta, Hermes or dropped.</span>
          <Button type="submit" disabled={busy || !text.trim()}>Remember</Button>
        </div>
        <ErrorNote error={err} />
        {res && (
          <div className="space-y-1 border-l-2 border-line py-1 pl-3 text-sm">
            <div className="flex flex-wrap items-center gap-2">
              {res.shard ? <ShardBadge shard={res.shard} /> : <Badge>dropped</Badge>}
              <CritBadge level={res.decision.criticality} />
              <span className="font-mono text-xs text-faint">{res.memory.op_id}</span>
            </div>
            <div className="text-muted">
              <span className="font-medium">{res.decision.by}:</span> {res.decision.reason}
            </div>
          </div>
        )}
      </form>
    </Card>
  );
}

function SearchPanel({ device, bump }: { device: string; bump: number }) {
  const [q, setQ] = useState("CNC-07 bearing trouble");
  const [res, setRes] = useState<SearchResult | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const run = async (query = q) => {
    if (!query.trim()) return;
    setErr(null);
    try { setRes(await api.search(device, query)); }
    catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
  };
  // re-run the current search when a note is written or the device changes
  useEffect(() => { if (res) run(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [device, bump]);
  // the auto demo types a query here
  useEffect(() => {
    const onSearch = (e: Event) => { const query = (e as CustomEvent<string>).detail; setQ(query); run(query); };
    window.addEventListener("smaran:search", onSearch);
    return () => window.removeEventListener("smaran:search", onSearch);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [device]);

  return (
    <Card title="Hybrid search, dense + BM25"
      right={res && (
        <div className="flex items-center gap-2 text-xs">
          <Badge tone={res.answered === "local" ? "ok" : "gold"}>{res.answered === "local" ? "answered locally" : "escalated to cloud"}</Badge>
          <span className="num text-muted" title={`embed ${res.embed_ms} ms + search ${res.search_ms} ms`}>{res.latency_ms} ms</span>
        </div>
      )}>
      <form className="mb-3 flex gap-2" onSubmit={(e) => { e.preventDefault(); run(); }}>
        <input aria-label="Search query" className={inputCls} value={q} onChange={(e) => setQ(e.target.value)} placeholder="Ask device memory…" />
        <Button type="submit">Search</Button>
      </form>
      <ErrorNote error={err} />
      {!res ? <Empty>Search runs on the device across Krypta, Hermes and Agora, with or without network.</Empty>
        : res.results.length === 0 ? <Empty>No matches.</Empty> : (
          <ol>
            {res.results.map((h, i) => (
              <li key={h.payload.op_id} className="border-t border-line py-2.5">
                <div className="mb-1 flex flex-wrap items-center gap-2">
                  <span className="num w-5 font-mono text-xs text-faint">{String(i + 1).padStart(2, "0")}</span>
                  <ShardBadge shard={h.shard} />
                  {h.payload.status !== "current" && <StatusBadge status={h.payload.status} />}
                  {h.payload.criticality > 0 && <CritBadge level={h.payload.criticality} />}
                  <span className="num ml-auto text-xs text-muted" title="Cosine similarity to the query (dense)">
                    cos {h.dense_score?.toFixed(3) ?? "–"}
                  </span>
                </div>
                <p className="text-sm">{h.payload.text}</p>
                <WhyHere decision={h.payload.decision} shard={h.shard} />
                <p className="mt-1 font-mono text-xs text-faint">{h.payload.op_id} / {h.payload.device_id} / {h.payload.machine ?? "no machine"}</p>
              </li>
            ))}
          </ol>
        )}
    </Card>
  );
}

function Chronos({ device }: { device: string }) {
  const mems = usePoll(() => api.memories(device), [device], 2000);
  const times = useMemo(() => {
    const ts = (mems.data ?? []).filter((m) => m.entity_key).flatMap((m) => [m.known_from ?? m.valid_from, m.valid_to ?? 0]).filter(Boolean) as number[];
    return ts.length ? { min: Math.min(...ts) - 1, max: Date.now() / 1000 } : null;
  }, [mems.data]);
  const [pos, setPos] = useState(1000);
  const at = times ? times.min + ((times.max - times.min) * pos) / 1000 : undefined;
  const beliefs = usePoll(() => api.history(device, pos >= 1000 ? undefined : at), [device, pos >= 1000 ? "now" : Math.round(at ?? 0)], 2000);

  return (
    <Card title={`Chronos, what device ${device} believed`}
      right={<span className="num font-mono text-xs text-muted">{pos >= 1000 || !at ? "now" : clock(at)}</span>}>
      <input type="range" min={0} max={1000} value={pos} onChange={(e) => setPos(+e.target.value)} className="mb-3 w-full accent-[var(--ink)]" aria-label="Point in time" />
      {!beliefs.data ? <Empty>Loading…</Empty> : beliefs.data.length === 0 ? <Empty>No machine statuses known at this time.</Empty> : (
        <ul>
          {beliefs.data.map((b) => (
            <li key={b.entity_key} className="border-t border-line py-2.5">
              <div className="mb-1 flex items-center gap-2">
                <span className="font-mono text-xs">{b.entity_key}</span>
                <Badge tone={b.status === "current" ? "neutral" : "gold"}>{b.status === "current" ? "one belief" : "contested"}</Badge>
              </div>
              {b.versions.map((v) => (
                <p key={v.op_id} className="text-sm">
                  <span className="font-mono text-xs text-faint">{v.op_id}</span> {v.text}
                </p>
              ))}
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function MemoryTable({ device, bump }: { device: string; bump: number }) {
  const [shard, setShard] = useState<Shard | "">("");
  const mems = usePoll(() => api.memories(device, shard || undefined), [device, shard, bump], 2000);
  return (
    <Card title={`Device ${device} memory`}
      right={
        <select aria-label="Shard filter" className="border border-line bg-paper px-2 py-1 text-xs text-ink"
          value={shard} onChange={(e) => setShard(e.target.value as Shard | "")}>
          <option value="">All shards</option><option value="krypta">Krypta</option><option value="hermes">Hermes</option><option value="agora">Agora</option>
        </select>
      }>
      {mems.error && <ErrorNote error={mems.error} />}
      {!mems.data ? <Empty>Loading…</Empty> : mems.data.length === 0 ? <Empty>No memories.</Empty> : (
        <div className="max-h-[440px] overflow-y-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-panel text-left label">
              <tr><th className="pb-1.5 font-medium">Shard</th><th className="font-medium">Status</th><th className="font-medium">Memory</th><th className="font-medium">Version vector</th></tr>
            </thead>
            <tbody>
              {mems.data.map((m) => (
                <tr key={`${m.shard}-${m.op_id}`} className="border-t border-line align-top">
                  <td className="py-1.5 pr-2"><ShardBadge shard={m.shard as Shard} /></td>
                  <td className="pr-2"><StatusBadge status={m.status} /></td>
                  <td className={`pr-2 ${m.status === "superseded" ? "text-faint line-through" : ""}`}>
                    {m.text}
                    <div className="font-mono text-xs text-faint no-underline">{m.op_id}{m.superseded_by ? ` → ${m.superseded_by}` : ""}</div>
                    <WhyHere decision={m.decision} />
                  </td>
                  <td className="font-mono text-xs text-muted">{vvText(m.vv)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

export default function MemorySearch({ device }: { device: string }) {
  const [bump, setBump] = useState(0);
  return (
    <div className="grid gap-4 lg:grid-cols-5">
      <div className="space-y-4 lg:col-span-2">
        <Composer device={device} onWrote={() => setBump((b) => b + 1)} />
        <Chronos device={device} />
      </div>
      <div className="space-y-4 lg:col-span-3">
        <SearchPanel device={device} bump={bump} />
        <MemoryTable device={device} bump={bump} />
      </div>
    </div>
  );
}
