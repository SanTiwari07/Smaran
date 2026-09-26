import { Activity, Cpu, RefreshCw, Server, ShieldAlert, ShieldCheck, Wifi, WifiOff } from "lucide-react";
import { useState } from "react";
import { api, DEVICES } from "../api/client";
import type { ActivityItem } from "../api/types";
import {
  ago, Badge, bytes, Button, Card, clock, CritBadge, Empty, ErrorNote, SHARD_META, Stat, Switch,
} from "../components/ui";
import { usePoll } from "../hooks/usePoll";

function DeviceCard({ id }: { id: string }) {
  const st = usePoll(() => api.state(id), [id]);
  const ob = usePoll(() => api.outbox(id), [id]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const s = st.data;

  const run = async (f: () => Promise<unknown>) => {
    setBusy(true);
    setErr(null);
    try { await f(); await Promise.all([st.refresh(), ob.refresh()]); }
    catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(false); }
  };

  return (
    <Card
      icon={<Cpu size={16} className="text-indigo-600 dark:text-indigo-400" />}
      title={`Device ${id}`}
      right={s && (
        <div className="flex items-center gap-2">
          <Badge tone={s.online ? "green" : "red"}>{s.online ? <Wifi size={12} /> : <WifiOff size={12} />}{s.online ? "online" : "offline"}</Badge>
          <Switch checked={s.online} disabled={busy} label={`Device ${id} online`} onChange={(v) => run(() => api.setOnline(id, v))} />
        </div>
      )}
    >
      {st.error && !s ? (
        <ErrorNote error={`Device ${id} unreachable at ${DEVICES[id]} (${st.error}). Is it running? python scripts/demo.py status`} />
      ) : !s ? <Empty>Loading…</Empty> : (
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-3">
            {(["krypta", "hermes", "agora"] as const).map((k) => (
              <div key={k} title={SHARD_META[k].hint} className="rounded-lg border border-stone-100 p-2 dark:border-stone-800">
                <div className="flex items-center gap-1 text-xs text-stone-500 dark:text-stone-400">{SHARD_META[k].icon}{SHARD_META[k].name}</div>
                <div className="num text-lg font-semibold">{s.counts[k]}</div>
              </div>
            ))}
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Stat label="Outbox" value={s.outbox_depth} hint="Memories waiting to sync" />
            <Stat label="Contested" value={s.contested} tone={s.contested ? "red" : undefined} />
            <Stat label="Last sync" value={<span className="text-sm">{ago(s.last_sync)}</span>} />
            <Stat label="Sent" value={<span className="text-sm">{bytes(s.bytes_sent)}</span>} hint="Bytes pushed to the gateway" />
          </div>
          {st.error && <ErrorNote error={`Lost contact: ${st.error}`} />}
          {s.last_error && s.online && <ErrorNote error={`Sync error: ${s.last_error}`} />}
          <ErrorNote error={err} />
          <div>
            <div className="mb-2 flex items-center justify-between">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-stone-500 dark:text-stone-400">Outbox · most critical first</h3>
              <Button variant="secondary" disabled={busy || !s.online} onClick={() => run(() => api.syncNow(id))}
                title={s.online ? "Push and pull now" : "Device is offline"}>
                <RefreshCw size={14} className={busy ? "animate-spin" : ""} />Sync now
              </Button>
            </div>
            {ob.data && ob.data.length > 0 ? (
              <ul className="space-y-1.5">
                {ob.data.slice(0, 6).map((o) => (
                  <li key={o.op_id} className="flex items-center gap-2 text-sm">
                    <CritBadge level={o.criticality} />
                    <span className="truncate">{o.text}</span>
                    <span className="ml-auto shrink-0 font-mono text-xs text-stone-400">{o.op_id}</span>
                  </li>
                ))}
                {ob.data.length > 6 && <li className="text-xs text-stone-500">+{ob.data.length - 6} more</li>}
              </ul>
            ) : <p className="text-sm text-stone-500 dark:text-stone-400">Empty. Everything is synced.</p>}
          </div>
          <p className="text-xs text-stone-400">classifier: {s.classifier} · embedder: {s.embedder}</p>
        </div>
      )}
    </Card>
  );
}

function GatewayCard() {
  const stats = usePoll(() => api.gwStats(), [], 1500);
  const audit = usePoll(() => api.gwAudit(), [], 2000);
  const s = stats.data;
  const a = audit.data;
  return (
    <Card icon={<Server size={16} className="text-indigo-600 dark:text-indigo-400" />} title="Gateway · Qdrant Server"
      right={s && <span className="font-mono text-xs text-stone-500">{s.server}</span>}>
      {stats.error && !s ? <ErrorNote error={`Gateway unreachable (${stats.error})`} /> : !s ? <Empty>Loading…</Empty> : (
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-3">
            <Stat label="Fleet memories" value={s.points} />
            <Stat label="Change feed seq" value={s.server_seq} />
            <Stat label="Contested" value={s.contested} tone={s.contested ? "red" : undefined} />
          </div>
          {a && (
            <div className={`flex items-start gap-3 rounded-lg p-3 ${a.ok ? "bg-emerald-50 dark:bg-emerald-950/40" : "bg-red-50 dark:bg-red-950/40"}`}>
              {a.ok ? <ShieldCheck className="mt-0.5 shrink-0 text-emerald-600" size={20} /> : <ShieldAlert className="mt-0.5 shrink-0 text-red-600" size={20} />}
              <div className="text-sm">
                <div className="font-semibold">Privacy audit {a.ok ? "passed" : "FAILED"}</div>
                <div className="num text-stone-600 dark:text-stone-300">
                  {a.private_count} private records · {a.pii_hits} PII matches · {a.total} memories scanned
                </div>
              </div>
            </div>
          )}
          {s.devices.length > 0 && (
            <table className="w-full text-sm">
              <thead className="text-left text-xs text-stone-500">
                <tr><th className="font-medium">Device</th><th className="font-medium">Received</th><th className="font-medium">Ops</th><th className="font-medium" title="Retries the gateway ignored">Dupes</th><th className="font-medium">Rejected</th></tr>
              </thead>
              <tbody className="num">
                {s.devices.map((d) => (
                  <tr key={d.device_id} className="border-t border-stone-100 dark:border-stone-800">
                    <td className="py-1">{d.device_id}</td><td>{bytes(d.bytes)}</td><td>{d.ops}</td><td>{d.duplicates}</td>
                    <td className={d.rejected ? "text-red-600" : ""}>{d.rejected}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </Card>
  );
}

const KIND_TONE: Record<string, "green" | "red" | "amber" | "sky" | "violet" | "neutral"> = {
  decision: "violet", synced: "green", pulled: "sky", conflict: "red", offline: "red", online: "green",
  escalated: "amber", reset: "neutral", recovered: "amber",
};

function describe(a: ActivityItem): string {
  const f = a as Record<string, unknown>;
  switch (a.kind) {
    case "decision": return `${f.residency} (${f.by}): ${f.text}`;
    case "synced": return `${f.op_id} → gateway: ${f.result}`;
    case "pulled": return `pulled ${f.count} from fleet (seq ${f.last_seq})`;
    case "conflict": return `CONFLICT on ${f.entity_key}: ${f.text}`;
    case "escalated": return `low local confidence (${f.top_dense}), asked the cloud`;
    default: return a.kind;
  }
}

function ActivityFeed() {
  const a = usePoll(() => Promise.all(Object.keys(DEVICES).map((d) => api.activity(d).catch(() => []))), []);
  const items = (a.data ?? []).flat().sort((x, y) => y.ts - x.ts).slice(0, 60);
  return (
    <Card icon={<Activity size={16} className="text-indigo-600 dark:text-indigo-400" />} title="Fleet activity">
      {items.length === 0 ? <Empty>No activity yet.</Empty> : (
        <ul className="max-h-[520px] space-y-1.5 overflow-y-auto pr-1">
          {items.map((it, i) => (
            <li key={`${it.ts}-${i}`} className="flex items-start gap-2 text-sm">
              <span className="num mt-0.5 shrink-0 font-mono text-xs text-stone-400">{clock(it.ts)}</span>
              <Badge tone="neutral">{it.device}</Badge>
              <Badge tone={KIND_TONE[it.kind] ?? "neutral"}>{it.kind}</Badge>
              <span className="min-w-0 break-words text-stone-700 dark:text-stone-300">{describe(it)}</span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

export default function DevicesSync() {
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <div className="space-y-4 lg:col-span-2">
        <div className="grid gap-4 md:grid-cols-2">
          {Object.keys(DEVICES).map((d) => <DeviceCard key={d} id={d} />)}
        </div>
        <GatewayCard />
      </div>
      <ActivityFeed />
    </div>
  );
}
