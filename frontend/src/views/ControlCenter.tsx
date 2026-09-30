import { useState } from "react";
import { companion, fmtTime, label, type Bench, type ChatResult, type Conflict, type Hit } from "../api/companion";
import { EdgeStrip, RouteBadge } from "../components/edge";
import { Badge, Button, Card, Empty, ErrorNote, Indicator } from "../components/ui";
import { usePoll } from "../hooks/usePoll";

type Panel = "memory" | "queue" | "routing" | "audit" | "bench" | "privacy" | null;
interface Line { at: number; tone: "ok" | "gold" | "neutral" | "alert"; text: string }

const Q = {
  teach: "I'm working on my final-year project. We're using PostgreSQL and Qdrant. My teammate handles the frontend and I'll handle the backend.",
  ask: "Which DB are we going with for the capstone?",
  tasks: "What are the remaining tasks for my project?",
  review: "When is the capstone review meeting?",
  remind: "Remind me tomorrow evening to finish the API integration",
  phone: "The capstone review meeting is at 4 PM.",
  laptop: "The capstone review meeting is at 5 PM.",
};

function ActionButton({ id, busy, children, onClick }: { id: string; busy: string | null; children: string; onClick: () => void }) {
  return (
    <Button variant="secondary" disabled={!!busy} onClick={onClick}>{busy === id ? "…" : children}</Button>
  );
}

export default function ControlCenter({ devices }: { devices: string[] }) {
  const [panel, setPanel] = useState<Panel>("routing");
  const [log, setLog] = useState<Line[]>([]);
  const [last, setLast] = useState<{ chat?: ChatResult; hits?: Hit[]; recallMs?: number; bench?: Bench } | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [step, setStep] = useState(0);

  const A = devices[0] ?? "A";
  const B = devices[1] ?? "B";
  const sA = usePoll(() => companion.status(A), [A], 1200);
  const sB = usePoll(() => companion.status(B), [B], 1200);
  const conflicts = usePoll(() => companion.conflicts(A), [A], 1500);
  const conflictsB = usePoll(() => companion.conflicts(B), [B], 1500);
  const outbox = usePoll(() => (panel === "queue" ? companion.outbox(A) : Promise.resolve([])), [panel, A], 1200);
  const memories = usePoll(() => (panel === "memory" ? companion.memories(A) : Promise.resolve([])), [panel, A], 2500);
  const traces = usePoll(() => (panel === "routing" ? companion.traces(A) : Promise.resolve([])), [panel, A], 1500);
  const audit = usePoll(() => (panel === "audit" ? companion.audit(A) : Promise.resolve([])), [panel, A], 1500);
  const gwAudit = usePoll(() => (panel === "privacy" ? companion.gwAudit() : Promise.resolve(null)), [panel], 2500);

  const say = (text: string, tone: Line["tone"] = "neutral") => setLog((l) => [{ at: Date.now() / 1000, tone, text }, ...l].slice(0, 40));
  const refresh = () => { sA.refresh(); sB.refresh(); conflicts.refresh(); conflictsB.refresh(); };

  const run = async (name: string, fn: () => Promise<void>) => {
    if (busy) return;
    setBusy(name);
    setErr(null);
    try { await fn(); } catch (e) { setErr(`${name}: ${e instanceof Error ? e.message : String(e)}`); }
    finally { setBusy(null); refresh(); }
  };

  const chat = async (d: string, text: string) => {
    const r = await companion.chat(d, text);
    setLast({ chat: r });
    say(`${label(d)} · “${text.length > 60 ? text.slice(0, 58) + "…" : text}” → ${r.reply.replace(/\n/g, " ")}`, r.route.route === "local-slm" ? "ok" : "neutral");
    return r;
  };

  const both = async (fn: (d: string) => Promise<unknown>) => { await fn(A); await fn(B); };

  const goOffline = () => run("Go offline", async () => {
    await both((d) => companion.setOnline(d, false));
    say("Both devices are offline. The AI, memory and task list keep working; changes will queue.", "gold");
  });

  const snapshot = async () => Promise.all([A, B].map((d) => companion.status(d)));

  const reconnect = () => run("Reconnect", async () => {
    const before = await snapshot();
    await both((d) => companion.setOnline(d, true));
    for (const d of [A, B, A]) await companion.syncNow(d);
    const after = await snapshot();
    const queued = before.reduce((n, x) => n + x.queued, 0);
    const uploaded = after.reduce((n, x, i) => n + (x.sync.acked - before[i].sync.acked), 0);
    const agora = after.reduce((n, x, i) => n + (x.memory.counts.agora - before[i].memory.counts.agora), 0);
    const pulled = Math.max(0, agora - uploaded);          // own uploads come back through the change feed too
    const c = await companion.conflicts(A);
    say(`Reconnected. ${queued} queued change(s) → ${uploaded} uploaded (duplicates are ignored by id). ${pulled} update(s) from the other device or the cloud pulled. ${c.length} conflict(s) detected, not overwritten.`, c.length ? "gold" : "ok");
  });

  const syncNow = () => run("Sync now", async () => {
    const r = await Promise.all([companion.syncNow(A), companion.syncNow(B)]);
    say(`Synced: ${r.map((x, i) => `${label([A, B][i])} sent ${x.push.sent ?? 0}, pulled ${x.pull.pulled ?? 0}`).join(" · ")}`, "ok");
  });

  const createConflict = () => run("Create conflict", async () => {
    await both((d) => companion.setOnline(d, false));
    await chat(A, Q.phone);
    await chat(B, Q.laptop);
    say("Both devices edited the meeting time while offline. Press “Simulate reconnect”.", "gold");
  });

  const loadStory = () => run("Load story", async () => {
    const r = await companion.seedStory(A);
    for (const d of [A, B, A]) await companion.syncNow(d).catch(() => null);
    say(`Two weeks of history replayed through the real agent: ${r.memories_written} memories, ${r.tasks} tasks, ${r.private} kept private (${r.ms} ms).`, "ok");
  });

  const resetAll = () => run("Reset", async () => {
    await companion.resetGateway();
    await both((d) => companion.resetDevice(d));
    setLog([]); setLast(null); setStep(0);
    say("Demo reset: empty devices, empty cloud (campus notices reloaded).");
  });

  const runSearch = () => run("Memory search", async () => {
    const r = await companion.recall(A, Q.ask);
    setLast({ hits: r.hits, recallMs: r.timing_ms.total });
    say(`Retrieved ${r.hits.length} memories for “${Q.ask}” in ${r.timing_ms.total} ms (${r.answered === "local" ? "all on device" : "cloud helped"}).`, "ok");
  });

  const runAI = () => run("Local AI", async () => { await chat(A, Q.tasks); });
  const runAgent = () => run("Agent", async () => { await chat(A, Q.remind); });
  const toggleModel = (on: boolean) => run("Model switch", async () => {
    await companion.useLocalModel(A, on);
    say(on ? "Local model back in the loop." : "Local model taken away: answers now come from rules over local memory.", on ? "ok" : "gold");
  });
  const benchmark = () => run("Benchmark", async () => {
    setPanel("bench");
    const b = await companion.bench(A);
    setLast((l) => ({ ...l, bench: b }));
    say(`Measured live on ${label(A)}: retrieval p50 ${b.retrieval_ms_p50} ms over ${b.memories} memories.`, "ok");
  });

  const resolve = (c: Conflict, op_id: string) => run("Resolve", async () => {
    const r = await companion.resolve(c.entity_key, op_id);
    for (const d of [A, B, A]) await companion.syncNow(d).catch(() => null);
    say(`You resolved “${c.label}”. Nothing was overwritten silently; new version ${r.op_id} supersedes both.`, "ok");
  });

  const STEPS: { title: string; hint: string; go: () => void }[] = [
    { title: "Reset and teach Smaran", hint: "Fresh devices, then say the Day-1 project sentence", go: () => run("Teach", async () => { await companion.resetGateway(); await both((d) => companion.resetDevice(d)); setLog([]); await chat(A, Q.teach); }) },
    { title: "Load two weeks of history", hint: "Replays 15 utterances through the real agent", go: loadStory },
    { title: "Retrieve naturally", hint: "“Which DB…” shares no keywords with the answer", go: () => run("Ask", async () => { await chat(A, Q.ask); }) },
    { title: "Disconnect the internet", hint: "Both devices offline", go: goOffline },
    { title: "Keep using Smaran", hint: "Ask about remaining tasks with no network", go: runAI },
    { title: "Ask something that needs memory", hint: "Answered from local memory", go: () => run("Ask", async () => { await chat(A, Q.review); }) },
    { title: "Ask the agent to act", hint: "Reminder created offline, verified, audited", go: runAgent },
    { title: "Two devices edit the same fact", hint: "Phone says 4 PM, Laptop says 5 PM, both offline", go: createConflict },
    { title: "Reconnect", hint: "Push, pull, idempotent replay", go: reconnect },
    { title: "Resolve the conflict", hint: "Use the conflict card below", go: () => setPanel("routing") },
    { title: "Show what stayed private", hint: "Cloud audit: 0 private memories", go: () => setPanel("privacy") },
    { title: "Show routing and audit", hint: "Which model answered, which tools ran", go: () => setPanel("audit") },
  ];

  const live = [sA.data, sB.data];
  const allConflicts = conflicts.data?.length ? conflicts.data : conflictsB.data ?? [];
  return (
    <div className="space-y-4">
      <div className="grid gap-4 lg:grid-cols-2">
        {[A, B].map((d, i) => (
          <Card key={d} title={`${label(d)} · device ${d}`} right={<Indicator tone={live[i]?.online === false ? "surface" : "live"}>{live[i]?.online === false ? "Offline" : "Online"}</Indicator>}>
            <EdgeStrip s={live[i] ?? null} />
          </Card>
        ))}
      </div>
      <ErrorNote error={sA.error ?? sB.error ?? err} />

      <Card title="Demo control center" right={busy ? <Badge tone="gold">running: {busy}</Badge> : undefined}>
        <div className="space-y-3">
          <div className="flex flex-wrap gap-2">
            <ActionButton busy={busy} id="Go offline" onClick={goOffline}>Go offline</ActionButton>
            <ActionButton busy={busy} id="Reconnect" onClick={reconnect}>Simulate reconnect</ActionButton>
            <ActionButton busy={busy} id="Create conflict" onClick={createConflict}>Create conflict</ActionButton>
            <ActionButton busy={busy} id="Sync now" onClick={syncNow}>Sync now</ActionButton>
            <ActionButton busy={busy} id="Load story" onClick={loadStory}>Load story data</ActionButton>
            <ActionButton busy={busy} id="Memory search" onClick={runSearch}>Run memory search</ActionButton>
            <ActionButton busy={busy} id="Local AI" onClick={runAI}>Run local AI</ActionButton>
            <ActionButton busy={busy} id="Agent" onClick={runAgent}>Run agent</ActionButton>
            <ActionButton busy={busy} id="Model switch" onClick={() => toggleModel(!sA.data?.ai.local.available)}>
              {sA.data?.ai.local.available ? "Take local model away" : "Restore local model"}
            </ActionButton>
            <ActionButton busy={busy} id="Reset" onClick={resetAll}>Reset demo</ActionButton>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="label">Show</span>
            {([["memory", "Memory"], ["queue", "Sync queue"], ["routing", "AI routing"], ["audit", "Audit log"], ["privacy", "Privacy"]] as const).map(([id, t]) => (
              <button key={id} type="button" onClick={() => setPanel(id)} aria-pressed={panel === id}
                className={`rounded-full border px-3 py-1 text-xs ${panel === id ? "border-[var(--rust-hot)] text-ink" : "border-line text-muted hover:text-ink"}`}>{t}</button>
            ))}
            <ActionButton busy={busy} id="Benchmark" onClick={benchmark}>Edge benchmark</ActionButton>
          </div>
        </div>
      </Card>

      {allConflicts.map((c) => (
        <Card key={c.entity_key} title={`Conflict detected · ${c.label}`} right={<Badge tone="gold">needs you</Badge>}>
          <p className="mb-3 text-sm text-muted">{c.why}</p>
          <div className="grid gap-px border border-line bg-line md:grid-cols-2">
            {c.versions.map((v) => (
              <div key={v.op_id} className="bg-panel p-3">
                <div className="mb-1 flex items-center gap-2 text-sm font-medium">{v.device_label}<span className="num ml-auto font-mono text-xs text-faint">{v.at_text}</span></div>
                <p className="mb-3 text-sm">{v.text}</p>
                <Button variant="secondary" disabled={!!busy} onClick={() => resolve(c, v.op_id)}>Keep this</Button>
              </div>
            ))}
          </div>
          <div className="mt-3 rounded border border-[var(--rust-hot)]/40 bg-[var(--rust)]/10 p-3 text-sm">
            <b>Suggested:</b> keep “{c.suggestion.text}”. <span className="text-muted">Why: {c.suggestion.reason}.</span>
            <div className="mt-2"><Button disabled={!!busy} onClick={() => resolve(c, c.suggestion.op_id)}>Accept suggestion</Button></div>
          </div>
        </Card>
      ))}

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
        <Card title={panel ? { memory: "Memory on the Phone", queue: "Sync queue (outbox)", routing: "AI routing and observability", audit: "Agent audit log", bench: "Edge benchmark (measured live)", privacy: "What stayed private" }[panel] : "Output"}>
          {panel === "routing" && (
            <div className="space-y-3">
              {last?.chat && (
                <div className="rounded border border-line bg-black/20 p-3 text-sm">
                  <div className="mb-1 flex flex-wrap items-center gap-2"><RouteBadge route={last.chat.route} /><span className="label">latest answer</span></div>
                  {last.chat.reply}
                  {last.chat.retrieval && <div className="mt-1 text-xs text-muted">Top-k: {last.chat.retrieval.hits.map((h) => `${h.payload.text.split(" Original:")[0].slice(0, 40)}… (${h.score.toFixed(2)})`).join(" | ")}</div>}
                </div>
              )}
              {last?.hits && (
                <div className="rounded border border-line bg-black/20 p-3 text-xs">
                  <div className="label mb-1 text-ink">Memory search · {last.recallMs} ms</div>
                  {last.hits.map((h) => <div key={h.payload.op_id}>{h.score.toFixed(2)} · {h.payload.text.split(" Original:")[0]}</div>)}
                </div>
              )}
              {(traces.data?.length ?? 0) === 0 ? <Empty>No requests yet. Press “Run local AI”.</Empty> : (
                <table className="w-full text-left text-xs">
                  <thead className="label"><tr><th className="py-1">Time</th><th>Route</th><th>Model</th><th>ms</th><th>Top-k</th><th>Tools</th><th>Queue</th></tr></thead>
                  <tbody>
                    {traces.data!.map((t, i) => (
                      <tr key={i} className="border-t border-line align-top">
                        <td className="py-1 font-mono">{fmtTime(t.ts)}</td>
                        <td>{t.route.route}</td><td>{t.route.model}</td>
                        <td className="num font-mono">{Math.round(t.latency_ms)}</td>
                        <td>{t.topk.length}</td><td>{t.tools.join(", ") || "–"}</td>
                        <td>{t.sync.queued}{t.sync.online ? "" : " (offline)"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}
          {panel === "queue" && ((outbox.data?.length ?? 0) === 0 ? <Empty>The outbox is empty: everything is synced.</Empty> : (
            <ul className="space-y-1.5 text-sm">
              {outbox.data!.map((o) => (
                <li key={o.op_id} className="flex items-center gap-2">
                  <Badge tone={o.criticality >= 2 ? "alert" : o.criticality === 1 ? "gold" : "neutral"}>{["routine", "important", "urgent"][o.criticality]}</Badge>
                  <span className="flex-1">{o.text}</span><span className="font-mono text-xs text-faint">{o.op_id} · tries {o.attempts}</span>
                </li>
              ))}
              <li className="pt-1 text-xs text-muted">Urgent items go first when the link returns.</li>
            </ul>
          ))}
          {panel === "memory" && ((memories.data?.length ?? 0) === 0 ? <Empty>No memories yet. Press “Load story data”.</Empty> : (
            <div className="max-h-[420px] overflow-y-auto">
              <table className="w-full text-left text-xs">
                <thead className="label"><tr><th className="py-1">Layer</th><th>Kind</th><th>Where</th><th>Memory</th></tr></thead>
                <tbody>
                  {memories.data!.map((m) => (
                    <tr key={m.op_id} className="border-t border-line align-top">
                      <td className="py-1"><Badge tone={m.memory_type === "semantic" ? "live" : m.memory_type === "procedural" ? "vault" : "neutral"}>{m.memory_type ?? "cloud"}</Badge></td>
                      <td>{m.kind}</td>
                      <td><Badge tone={m.shard === "krypta" ? "vault" : "neutral"}>{m.shard}</Badge>{m.status !== "current" && <Badge tone="gold">{m.status}</Badge>}</td>
                      <td>{m.text.split(" Original:")[0]}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
          {panel === "audit" && ((audit.data?.length ?? 0) === 0 ? <Empty>The agent has not acted yet.</Empty> : (
            <table className="w-full text-left text-xs">
              <thead className="label"><tr><th className="py-1">Time</th><th>Tool</th><th>Risk</th><th>State</th><th>Verified</th><th>Result</th></tr></thead>
              <tbody>
                {audit.data!.map((a) => (
                  <tr key={a.id} className="border-t border-line align-top">
                    <td className="py-1 font-mono">{fmtTime(a.ts)}</td><td>{a.tool}</td><td>{a.risk}</td>
                    <td><Badge tone={a.state === "executed" ? "ok" : a.state === "pending_confirmation" ? "gold" : "alert"}>{a.state}</Badge></td>
                    <td>{a.verified === null ? "–" : a.verified ? "✓" : "✗"}</td><td>{a.message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ))}
          {panel === "bench" && (last?.bench ? (
            <dl className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-3">
              {[
                ["Embedding p50 / p95", `${last.bench.embed_ms_p50} / ${last.bench.embed_ms_p95} ms`],
                ["Retrieval p50 / p95", `${last.bench.retrieval_ms_p50} / ${last.bench.retrieval_ms_p95} ms`],
                ["Agent read action p50", `${last.bench.agent_read_action_ms_p50} ms`],
                ["Local SLM round trip", last.bench.local_slm_ms ? `${last.bench.local_slm_ms} ms (${last.bench.local_slm_model})` : "model not running"],
                ["Memories searched", String(last.bench.memories)],
                ["On-disk size", `${last.bench.data_dir_mb} MB`],
              ].map(([k, v]) => <div key={k} className="tile"><dt className="label">{k}</dt><dd className="num font-mono text-base">{v}</dd></div>)}
              <p className="col-span-full text-xs text-muted">{last.bench.note}. Cloud never used for these numbers. Larger runs: <code>python -m bench.edge</code>.</p>
            </dl>
          ) : <Empty>Press “Edge benchmark”. Numbers are measured now, on this machine.</Empty>)}
          {panel === "privacy" && (
            <div className="space-y-3 text-sm">
              <div className="grid gap-2 sm:grid-cols-3">
                <div className="tile"><div className="num font-mono text-2xl">{sA.data?.memory.counts.krypta ?? 0}</div><div className="label">private on Phone (Krypta)</div></div>
                <div className="tile"><div className="num font-mono text-2xl">{sB.data?.memory.counts.krypta ?? 0}</div><div className="label">private on Laptop</div></div>
                <div className="tile"><div className="num font-mono text-2xl">{gwAudit.data ? gwAudit.data.private_count + gwAudit.data.pii_hits : "…"}</div><div className="label">private items found in the cloud</div></div>
              </div>
              <p className="text-muted">Phone numbers, emails, ID numbers and sensitive topics (salary, health, passwords) are routed to Krypta, which has no sync path. The gateway re-checks and would reject them. Chat history and the audit trail are encrypted at rest ({sA.data?.memory.encryption.chat_and_audit}, key: {sA.data?.memory.encryption.key}). The Qdrant Edge shard files themselves are not encrypted; use disk encryption.</p>
              {gwAudit.data && <Badge tone={gwAudit.data.ok ? "ok" : "alert"}>{gwAudit.data.ok ? "cloud audit clean" : "cloud audit found private data"}</Badge>}
            </div>
          )}
        </Card>

        <div className="space-y-4">
          <Card title="Judge walkthrough">
            <ol className="space-y-1.5">
              {STEPS.map((s, i) => (
                <li key={i} className={`flex items-start gap-2 rounded px-2 py-1 ${i === step ? "bg-white/[0.05]" : ""}`}>
                  <span className="num w-5 font-mono text-xs text-faint">{i + 1}</span>
                  <button type="button" className="flex-1 text-left" onClick={() => { setStep(i); s.go(); }} disabled={!!busy}>
                    <div className="text-sm">{s.title}</div><div className="text-xs text-muted">{s.hint}</div>
                  </button>
                </li>
              ))}
            </ol>
          </Card>
          <Card title="Activity">
            {log.length === 0 ? <Empty>Actions you trigger show up here.</Empty> : (
              <ul className="max-h-72 space-y-2 overflow-y-auto text-xs">
                {log.map((l, i) => (
                  <li key={i}><Badge tone={l.tone}>{fmtTime(l.at)}</Badge> <span className="text-muted">{l.text}</span></li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
