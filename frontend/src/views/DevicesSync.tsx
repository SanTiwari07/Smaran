import { useState } from "react";
import { api, DEVICES } from "../api/client";
import type { ActivityItem } from "../api/types";
import {
  Astronaut, ago, bytes, Button, Card, clock, CritBadge, Empty, ErrorNote, Group, Indicator, SHARD_META, Stat, StatRow,
} from "../components/ui";
import { usePoll } from "../hooks/usePoll";
import ProveIt from "./ProveIt";

function DeviceCard({ id }: { id: string }) {
  const st = usePoll(() => api.state(id), [id]);
  const gw = usePoll(() => api.gwStats(), [], 2000);
  const dupes = gw.data?.devices.find((d) => d.device_id === id)?.duplicates ?? 0;
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
      title={
        <span className="flex items-center gap-3">
          <Astronaut online={s?.online ?? true} size={30} stripe={id === "A" ? "#f5993c" : "#8ea2ff"} />
          <span>Device {id}</span>
        </span>
      }
      right={s && (
        <div className="flex items-center gap-3">
          <Indicator tone={s.online ? "ok" : "alert"}>{s.online ? "Comms online" : "Comms lost"}</Indicator>
          <button type="button" disabled={busy} onClick={() => run(() => api.setOnline(id, !s.online))}
            className="whitespace-nowrap text-xs text-muted underline decoration-line underline-offset-4 hover:text-ink disabled:opacity-40">
            {s.online ? "Cut link" : "Restore link"}
          </button>
        </div>
      )}
    >
      {st.error && !s ? (
        <ErrorNote error={`Device ${id} unreachable at ${DEVICES[id]} (${st.error}). Is it running? python scripts/demo.py status`} />
      ) : !s ? <Empty>Loading…</Empty> : (
        <div className="space-y-5">
          <Group title="Memory shards">
            <StatRow cols={3}>
              {(["krypta", "hermes", "agora"] as const).map((k) => (
                <Stat key={k} label={`${SHARD_META[k].name} · ${{ krypta: "private", hermes: "outgoing", agora: "fleet" }[k]}`}
                  value={s.counts[k]} hint={SHARD_META[k].hint} />
              ))}
            </StatRow>
          </Group>
          <Group title="Sync link">
            <StatRow cols={4}>
              <Stat label="Outbox" value={s.outbox_depth} hint="Memories waiting to sync" />
              <Stat label="Conflicts" value={s.contested} tone={s.contested ? "alert" : undefined} />
              <Stat label="Last sync" value={<span className="text-base">{ago(s.last_sync)}</span>} />
              <Stat label="Sent" value={<span className="text-base">{bytes(s.bytes_sent)}</span>} hint="Bytes pushed to the gateway" />
            </StatRow>
          </Group>
          <Group title="Crash recovery">
            <StatRow cols={4}>
              <Stat label="Acked" value={s.acked} hint="Ops the gateway confirmed and the outbox marked done" />
              <Stat label="Resent" value={s.recovery?.pending ?? 0}
                hint="Unacknowledged ops found in the outbox when this process last started" />
              <Stat label="Duplicates" value={dupes} hint="Resends the gateway recognised by op id and did not store again" />
              <Stat label="Up since" value={<span className="text-base">{ago(s.recovery?.ts)}</span>} />
            </StatRow>
          </Group>
          {st.error && <ErrorNote error={`Lost contact: ${st.error}`} />}
          {s.last_error && s.online && <ErrorNote error={`Sync error: ${s.last_error}`} />}
          <ErrorNote error={err} />
          <Group title="Outbox, most critical first">
            <div className="mb-2 flex justify-end">
              <Button variant="secondary" disabled={busy || !s.online} onClick={() => run(() => api.syncNow(id))}
                title={s.online ? "Push and pull now" : "Device is offline"}>
                {busy ? "Syncing…" : "Sync now"}
              </Button>
            </div>
            {ob.data && ob.data.length > 0 ? (
              <ul className="divide-y divide-line">
                {ob.data.slice(0, 6).map((o) => (
                  <li key={o.op_id} className="flex items-center gap-2 py-1.5 text-sm">
                    <CritBadge level={o.criticality} />
                    <span className="truncate">{o.text}</span>
                    <span className="ml-auto shrink-0 font-mono text-xs text-faint">{o.op_id}</span>
                  </li>
                ))}
                {ob.data.length > 6 && <li className="py-1.5 text-xs text-muted">and {ob.data.length - 6} more</li>}
              </ul>
            ) : <p className="text-sm text-muted">Empty. Everything is synced.</p>}
          </Group>
          <p className="font-mono text-[11px] text-faint">classifier {s.classifier} / embedder {s.embedder}</p>
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
    <Card title="Base station · Qdrant Server" right={s && <span className="truncate font-mono text-xs text-faint">{s.server}</span>}>
      {stats.error && !s ? <ErrorNote error={`Gateway unreachable (${stats.error})`} /> : !s ? <Empty>Loading…</Empty> : (
        <div className="space-y-5">
          <StatRow cols={3}>
            <Stat label="Fleet memories" value={s.points} />
            <Stat label="Change feed seq" value={s.server_seq} />
            <Stat label="Contested" value={s.contested} tone={s.contested ? "alert" : undefined} />
          </StatRow>
          {a && (
            <div className={`border-l-2 py-0.5 pl-3 ${a.ok ? "border-ok" : "border-alert"}`}>
              <div className={`text-sm font-medium ${a.ok ? "text-ok" : "text-alert"}`}>Privacy audit {a.ok ? "passed" : "failed"}</div>
              <div className="num text-sm text-muted">
                {a.private_count} private records, {a.pii_hits} PII matches, {a.total} memories scanned
              </div>
            </div>
          )}
          {s.devices.length > 0 && (
            <table className="num w-full text-sm">
              <thead className="text-left">
                <tr className="label [&>th]:pb-1.5 [&>th]:font-medium">
                  <th>Device</th><th>Received</th><th>Ops</th><th title="Retries the gateway ignored">Dupes</th><th>Rejected</th>
                </tr>
              </thead>
              <tbody>
                {s.devices.map((d) => (
                  <tr key={d.device_id} className="border-t border-line [&>td]:py-1.5">
                    <td>{d.device_id}</td><td>{bytes(d.bytes)}</td><td>{d.ops}</td><td>{d.duplicates}</td>
                    <td className={d.rejected ? "text-alert" : ""}>{d.rejected}</td>
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

const ALERT_KINDS = new Set(["conflict", "offline"]);

function describe(a: ActivityItem): string {
  const f = a as Record<string, unknown>;
  switch (a.kind) {
    case "decision": return `${f.residency} (${f.by}): ${f.text}`;
    case "synced": return `${f.op_id} to gateway: ${f.result}`;
    case "pulled": return `pulled ${f.count} from fleet (seq ${f.last_seq})`;
    case "conflict": return `${f.entity_key}: ${f.text}`;
    case "escalated": return `low local confidence (${f.top_dense}), asked the cloud`;
    default: return "";
  }
}

function ActivityFeed() {
  const a = usePoll(() => Promise.all(Object.keys(DEVICES).map((d) => api.activity(d).catch(() => []))), []);
  const items = (a.data ?? []).flat().sort((x, y) => y.ts - x.ts).slice(0, 60);
  return (
    <Card title="Mission log">
      {items.length === 0 ? <Empty>No activity yet.</Empty> : (
        <ul className="max-h-[560px] overflow-y-auto font-mono text-xs">
          {items.map((it, i) => (
            <li key={`${it.ts}-${i}`} className="grid grid-cols-[auto_auto_5.5rem_1fr] gap-x-3 border-b border-line/60 py-1.5 last:border-0">
              <span className="num text-faint">{clock(it.ts)}</span>
              <span className="text-muted">{it.device}</span>
              <span className={ALERT_KINDS.has(it.kind) ? "text-alert" : "text-ink"}>{it.kind}</span>
              <span className="min-w-0 break-words font-sans text-muted">{describe(it)}</span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function MissionBanner() {
  const gw = usePoll(() => api.gwStats(), [], 2000);
  const ids = Object.keys(DEVICES);
  const states = usePoll(() => Promise.all(ids.map((d) => api.state(d).catch(() => null))), [], 2000);
  const online = (states.data ?? []).filter((x) => x?.online).length;
  return (
    <section className="relative mb-4 overflow-hidden rounded-xl border border-line">
      <img src="/hero.webp" alt="" className="absolute inset-0 h-full w-full object-cover object-[50%_72%]" />
      <div className="absolute inset-0 bg-gradient-to-r from-paper via-paper/70 to-transparent" />
      <div className="absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-paper/80 to-transparent" />
      <div className="relative flex min-h-[210px] flex-col justify-center gap-3 px-6 py-6 sm:min-h-[240px] sm:px-9">
        <span className="font-mono text-[11px] uppercase tracking-[0.16em]" style={{ color: "var(--brand-glow)" }}>Mission control · CNC-07 fleet</span>
        <h1 className="max-w-md text-3xl font-semibold leading-tight sm:text-4xl">Every crew member remembers. Nobody lies.</h1>
        <div className="flex flex-wrap gap-2 pt-1">
          <span className="rounded-full border border-line bg-paper/70 px-3 py-1 text-xs backdrop-blur">
            <span className="num font-mono text-ink">{online}/{ids.length}</span> crew on comms
          </span>
          <span className="rounded-full border border-line bg-paper/70 px-3 py-1 text-xs backdrop-blur">
            <span className="num font-mono text-ink">{gw.data?.points ?? "–"}</span> fleet memories
          </span>
          <span className={`rounded-full border bg-paper/70 px-3 py-1 text-xs backdrop-blur ${gw.data?.contested ? "border-alert/50 text-alert" : "border-line"}`}>
            <span className="num font-mono">{gw.data?.contested ?? 0}</span> contested
          </span>
        </div>
      </div>
    </section>
  );
}

export default function DevicesSync() {
  return (
    <>
    <MissionBanner />
    <div className="grid gap-4 lg:grid-cols-3">
      <div className="space-y-4 lg:col-span-2">
        <div className="grid gap-4 md:grid-cols-2">
          {Object.keys(DEVICES).map((d) => <DeviceCard key={d} id={d} />)}
        </div>
        <GatewayCard />
        <ProveIt />
      </div>
      <ActivityFeed />
    </div>
    </>
  );
}
