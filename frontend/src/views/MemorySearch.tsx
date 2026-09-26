import { Clock, Database, History, PenLine, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import type { Kind, NoteResult, SearchResult, Shard } from "../api/types";
import {
  Badge, Button, Card, clock, CritBadge, Empty, ErrorNote, inputCls, ShardBadge, StatusBadge, vvText,
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
    <Card icon={<PenLine size={16} className="text-indigo-600 dark:text-indigo-400" />} title={`Remember · device ${device}`}>
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
          <span className="text-xs text-stone-500">Argus decides where it lives: Krypta, Hermes or dropped.</span>
          <Button type="submit" disabled={busy || !text.trim()}>Remember</Button>
        </div>
        <ErrorNote error={err} />
        {res && (
          <div className="space-y-1 rounded-lg bg-stone-50 p-3 text-sm dark:bg-stone-800/50">
            <div className="flex flex-wrap items-center gap-2">
              {res.shard ? <ShardBadge shard={res.shard} /> : <Badge>dropped</Badge>}
              <CritBadge level={res.decision.criticality} />
              <span className="font-mono text-xs text-stone-400">{res.memory.op_id}</span>
            </div>
            <div className="text-stone-600 dark:text-stone-300">
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

  return (
    <Card icon={<Search size={16} className="text-indigo-600 dark:text-indigo-400" />} title="Hybrid search · dense + BM25"
      right={res && (
        <div className="flex items-center gap-2 text-xs">
          <Badge tone={res.answered === "local" ? "green" : "amber"}>{res.answered === "local" ? "answered locally" : "escalated to cloud"}</Badge>
          <span className="num text-stone-500" title={`embed ${res.embed_ms} ms + search ${res.search_ms} ms`}>{res.latency_ms} ms</span>
        </div>
      )}>
      <form className="mb-3 flex gap-2" onSubmit={(e) => { e.preventDefault(); run(); }}>
        <input aria-label="Search query" className={inputCls} value={q} onChange={(e) => setQ(e.target.value)} placeholder="Ask device memory…" />
        <Button type="submit">Search</Button>
      </form>
      <ErrorNote error={err} />
      {!res ? <Empty>Search runs on the device across Krypta, Hermes and Agora, with or without network.</Empty>
        : res.results.length === 0 ? <Empty>No matches.</Empty> : (
          <ol className="space-y-2">
            {res.results.map((h, i) => (
              <li key={h.payload.op_id} className="rounded-lg border border-stone-100 p-3 dark:border-stone-800">
                <div className="mb-1 flex flex-wrap items-center gap-2">
                  <span className="num text-xs font-semibold text-stone-400">#{i + 1}</span>
                  <ShardBadge shard={h.shard} />
                  <StatusBadge status={h.payload.status} />
                  {h.payload.criticality > 0 && <CritBadge level={h.payload.criticality} />}
                  <span className="num ml-auto text-xs text-stone-500" title="Cosine similarity to the query (dense)">
                    cos {h.dense_score?.toFixed(3) ?? "–"}
                  </span>
                </div>
                <p className="text-sm">{h.payload.text}</p>
                <p className="mt-1 font-mono text-xs text-stone-400">{h.payload.op_id} · {h.payload.device_id} · {h.payload.machine ?? "no machine"}</p>
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
    <Card icon={<History size={16} className="text-indigo-600 dark:text-indigo-400" />} title={`Chronos · what device ${device} believed`}
      right={<span className="num flex items-center gap-1 text-xs text-stone-500"><Clock size={12} />{pos >= 1000 || !at ? "now" : clock(at)}</span>}>
      <input type="range" min={0} max={1000} value={pos} onChange={(e) => setPos(+e.target.value)} className="mb-3 w-full accent-indigo-600" aria-label="Point in time" />
      {!beliefs.data ? <Empty>Loading…</Empty> : beliefs.data.length === 0 ? <Empty>No machine statuses known at this time.</Empty> : (
        <ul className="space-y-2">
          {beliefs.data.map((b) => (
            <li key={b.entity_key} className="rounded-lg border border-stone-100 p-3 dark:border-stone-800">
              <div className="mb-1 flex items-center gap-2">
                <span className="font-mono text-xs">{b.entity_key}</span>
                <Badge tone={b.status === "current" ? "green" : "red"}>{b.status === "current" ? "one belief" : "contested"}</Badge>
              </div>
              {b.versions.map((v) => (
                <p key={v.op_id} className="text-sm">
                  <span className="font-mono text-xs text-stone-400">{v.op_id}</span> {v.text}
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
    <Card icon={<Database size={16} className="text-indigo-600 dark:text-indigo-400" />} title={`Device ${device} memory`}
      right={
        <select aria-label="Shard filter" className="rounded-md border border-stone-300 bg-white px-2 py-1 text-xs dark:border-stone-700 dark:bg-stone-900"
          value={shard} onChange={(e) => setShard(e.target.value as Shard | "")}>
          <option value="">All shards</option><option value="krypta">Krypta</option><option value="hermes">Hermes</option><option value="agora">Agora</option>
        </select>
      }>
      {mems.error && <ErrorNote error={mems.error} />}
      {!mems.data ? <Empty>Loading…</Empty> : mems.data.length === 0 ? <Empty>No memories.</Empty> : (
        <div className="max-h-[440px] overflow-y-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-white text-left text-xs text-stone-500 dark:bg-stone-900">
              <tr><th className="py-1 font-medium">Shard</th><th className="font-medium">Status</th><th className="font-medium">Memory</th><th className="font-medium">Version vector</th></tr>
            </thead>
            <tbody>
              {mems.data.map((m) => (
                <tr key={`${m.shard}-${m.op_id}`} className="border-t border-stone-100 align-top dark:border-stone-800">
                  <td className="py-1.5 pr-2"><ShardBadge shard={m.shard as Shard} /></td>
                  <td className="pr-2"><StatusBadge status={m.status} /></td>
                  <td className={`pr-2 ${m.status === "superseded" ? "text-stone-400 line-through" : ""}`}>
                    {m.text}
                    <div className="font-mono text-xs text-stone-400 no-underline">{m.op_id}{m.superseded_by ? ` → ${m.superseded_by}` : ""}</div>
                  </td>
                  <td className="font-mono text-xs text-stone-500">{vvText(m.vv)}</td>
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
