import { useEffect, useRef, useState } from "react";
import { companion, label, type ChatResult, type Explain, type Hit, type LifecycleReport } from "../api/companion";
import { Bar, EdgeStrip, RouteBadge } from "../components/edge";
import { ConflictCard, ContradictionCard, ExplainCard, LifecycleStrip, MemoryCreated, OfflineProof, ProvenanceCard } from "../components/proof";
import { Badge, Button, Card, Empty, ErrorNote, inputCls } from "../components/ui";
import { usePoll } from "../hooks/usePoll";

interface Turn { who: "you" | "smaran"; text: string; result?: ChatResult; at: number; device?: string }
export interface StageInfo { n: number; id: string; title: string; note: string; lifecycle?: LifecycleReport }
export const STAGES = ["Remember", "Think", "Act", "Reconcile", "Learn"];

const PROMPTS = [
  "I'm building Project Nova. I handle the backend, we're using FastAPI and PostgreSQL, and we chose PostgreSQL because we need relational transactions.",
  "Why did we choose PostgreSQL?",
  "I think we should use MongoDB instead.",
  "Create a task to finish the authentication API tonight.",
  "What are the remaining tasks for my project?",
  "When is the Project Nova review meeting?",
];

const STATE_TONE: Record<string, "ok" | "gold" | "alert" | "neutral"> = {
  executed: "ok", duplicate: "neutral", pending_confirmation: "gold", blocked: "alert", failed: "alert",
};

function Hits({ hits }: { hits: Hit[] }) {
  if (!hits.length) return <div className="text-xs text-muted">No memories matched.</div>;
  return (
    <table className="w-full text-left text-xs">
      <thead className="label"><tr><th className="py-1 pr-2">Memory</th><th className="pr-2">Meaning</th><th className="pr-2">Recency</th><th className="pr-2">Importance</th><th>Score</th></tr></thead>
      <tbody>
        {hits.map((h) => (
          <tr key={h.payload.op_id} className="border-t border-line align-top">
            <td className="py-1.5 pr-2">
              <div>{h.payload.text.split(" Original:")[0]}</div>
              <div className="mt-0.5 flex flex-wrap gap-1">
                <Badge tone={h.shard === "krypta" ? "vault" : "neutral"}>{h.shard}</Badge>
                {h.payload.memory_type && <Badge>{h.payload.memory_type}</Badge>}
                {h.why.map((w) => <Badge key={w} tone="gold">{w}</Badge>)}
                {h.payload.status === "contested" && <Badge tone="alert">conflict</Badge>}
              </div>
            </td>
            <td className="pr-2"><Bar value={h.features.semantic} /></td>
            <td className="pr-2"><Bar value={h.features.recency} /></td>
            <td className="pr-2"><Bar value={h.features.importance} /></td>
            <td className="num font-mono">{h.score.toFixed(2)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Trace({ r, device, onChange, aiLocal, extra }: { r: ChatResult; device: string; onChange: () => void; aiLocal: boolean; extra?: string }) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [why, setWhy] = useState<Explain | null>(null);
  const [showProv, setShowProv] = useState(r.intent === "ask");
  const [answered, setAnswered] = useState<string | null>(null);
  const acted = r.actions.some((a) => ["create_task", "set_reminder", "update_task", "cancel_task", "resolve_decision"].includes(a.tool));
  const contradictions = r.actions.filter((a) => a.contradiction).map((a) => a.contradiction!);
  const explain = async () => { setWhy(await companion.explain(device, { request_id: r.request_id })); };
  // an action taken with the link off is the moment people ask "why did it do that?": show it straight away
  useEffect(() => { if (acted && !r.online_at_start) explain().catch(() => null); }, []);  // eslint-disable-line react-hooks/exhaustive-deps
  const confirm = async (id: number) => {
    setBusy(true);
    try { await companion.confirm(device, id); onChange(); } finally { setBusy(false); }
  };
  return (
    <div className="mt-2 space-y-2">
      <div className="flex flex-wrap items-center gap-1.5">
        <RouteBadge route={r.route} />
        <Badge>{r.planner === "local-slm" ? "planned by local SLM" : "planned by rules"}</Badge>
        {r.actions.map((a, i) => (
          <Badge key={i} tone={STATE_TONE[a.state] ?? "neutral"} title={a.message}>
            {a.tool} · {a.contradiction ? "held: conflicts with a decision" : a.state.replace("_", " ")}{a.verified ? " · verified" : ""}
          </Badge>
        ))}
        {r.queued > 0 && <Badge tone="gold">{r.queued} queued to sync</Badge>}
        <button type="button" className="label ml-auto hover:!text-ink" onClick={() => setOpen(!open)}>
          {open ? "Hide" : "How did Smaran do this?"}
        </button>
      </div>
      {r.intent === "remember" && <MemoryCreated actions={r.actions} />}
      {contradictions.map((c) => (answered ? null : <ContradictionCard key={c.id} c={c} device={device} onDone={(x) => { setAnswered(x.message); onChange(); }} />))}
      {answered && <div className="rounded border border-ok/40 bg-ok/10 px-3 py-2 text-sm">{answered}</div>}
      {acted && !r.online_at_start && <OfflineProof r={r} aiLocal={aiLocal} />}
      {acted && (
        <div>
          <button type="button" className="label hover:!text-ink" onClick={() => (why ? setWhy(null) : explain())}>{why ? "Hide" : "Why did Smaran do this?"}</button>
          {why && <div className="mt-2"><ExplainCard e={why} /></div>}
        </div>
      )}
      {r.intent === "ask" && r.provenance.length > 0 && (
        <div>
          <button type="button" className="label hover:!text-ink" onClick={() => setShowProv(!showProv)}>{showProv ? "Hide" : "Why did Smaran say this?"}</button>
          {showProv && <div className="mt-2 space-y-2">{r.provenance.slice(0, 1).map((p) => <ProvenanceCard key={p.op_id} p={p} />)}</div>}
        </div>
      )}
      {extra && <div className="rounded border border-ok/40 bg-ok/10 px-3 py-2 text-xs">{extra}</div>}
      {r.actions.filter((a) => a.state === "pending_confirmation" && a.audit_id).map((a) => (
        <div key={a.audit_id} className="flex items-center gap-3 rounded border border-gold/40 bg-gold/10 px-3 py-2 text-sm">
          <span className="flex-1">{a.message}</span>
          <Button disabled={busy} onClick={() => confirm(a.audit_id!)}>Confirm</Button>
        </div>
      ))}
      {open && (
        <div className="space-y-3 rounded border border-line bg-black/20 p-3">
          <ol className="space-y-1 text-xs">
            {r.steps.map((s, i) => (
              <li key={i} className="flex gap-2">
                <span className="label w-16 shrink-0 text-ink">{s.step}</span>
                <span className="flex-1 text-muted">{s.detail}</span>
                <span className="num font-mono text-faint">{s.ms} ms</span>
              </li>
            ))}
          </ol>
          {r.route.tried && r.route.tried.length > 0 && (
            <div className="text-xs text-gold">Tried first and failed: {r.route.tried.map((t) => `${t.route} (${t.error})`).join("; ")}</div>
          )}
          <div className="text-xs text-muted">Route reason: {r.route.reason}</div>
          {r.retrieval && (
            <div>
              <div className="label mb-1 text-ink">
                Retrieved from memory · {r.retrieval.timing_ms.total} ms · {r.retrieval.answered === "local" ? "all local" : "cloud helped"}
              </div>
              <Hits hits={r.retrieval.hits} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function Companion({ device, setDevice, devices }: { device: string; setDevice: (d: string) => void; devices: string[] }) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const bottom = useRef<HTMLDivElement>(null);
  const status = usePoll(() => companion.status(device), [device], 1500);
  const tasks = usePoll(() => companion.tasks(device), [device], 1500);
  const brief = usePoll(() => companion.briefing(device), [device], 2000);
  const online = status.data?.online ?? true;
  const aiLocal = !!status.data?.ai.local.available;
  const conflicts = usePoll(() => companion.conflicts(device), [device], 1500);
  const [stage, setStage] = useState<StageInfo | null>(null);
  const [resolving, setResolving] = useState(false);
  const [provider, setProvider] = useState<"auto" | "gemini" | "local-slm" | "extractive">("auto");
  const [showGeminiModal, setShowGeminiModal] = useState(false);
  const [geminiKeyInput, setGeminiKeyInput] = useState("");
  const [geminiSaveMsg, setGeminiSaveMsg] = useState<string | null>(null);

  useEffect(() => { bottom.current?.scrollIntoView({ behavior: "smooth" }); }, [turns.length]);
  useEffect(() => { setErr(null); }, [device]);
  // The auto demo runs real chats and hands each result here, so it shows up exactly like a typed message.
  useEffect(() => {
    const onTurn = (e: Event) => {
      const d = (e as CustomEvent<{ device: string; text: string; result: ChatResult }>).detail;
      setTurns((x) => [...x, { who: "you", text: d.text, at: Date.now(), device: d.device }, { who: "smaran", text: d.result.reply, result: d.result, at: Date.now(), device: d.device }]);
      status.refresh(); tasks.refresh(); brief.refresh(); conflicts.refresh();
    };
    const onStage = (e: Event) => setStage((e as CustomEvent<StageInfo | null>).detail);
    window.addEventListener("smaran:turn", onTurn);
    window.addEventListener("smaran:stage", onStage);
    return () => { window.removeEventListener("smaran:turn", onTurn); window.removeEventListener("smaran:stage", onStage); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [device]);

  const keep = async (entity_key: string, op_id: string) => {
    setResolving(true);
    try {
      await companion.resolve(entity_key, op_id);
      for (const d of devices) await companion.syncNow(d).catch(() => null);
      conflicts.refresh(); tasks.refresh(); status.refresh();
    } finally { setResolving(false); }
  };

  const saveGeminiKey = async () => {
    if (!geminiKeyInput.trim()) return;
    try {
      for (const d of devices) {
        await companion.configureGemini(d, geminiKeyInput.trim());
      }
      setGeminiSaveMsg("Gemini API key configured successfully!");
      status.refresh();
      setTimeout(() => { setShowGeminiModal(false); setGeminiSaveMsg(null); }, 1200);
    } catch (e) {
      setGeminiSaveMsg(e instanceof Error ? e.message : String(e));
    }
  };

  const send = async (t: string) => {
    if (!t.trim() || busy) return;
    setBusy(true);
    setErr(null);
    setTurns((x) => [...x, { who: "you", text: t, at: Date.now(), device }]);
    setText("");
    try {
      const p = provider === "auto" ? undefined : provider;
      const r = await companion.chat(device, t, provider === "gemini", p);
      setTurns((x) => [...x, { who: "smaran", text: r.reply, result: r, at: Date.now(), device }]);
      status.refresh(); tasks.refresh(); brief.refresh();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally { setBusy(false); }
  };

  const toggleLink = async () => { await companion.setOnline(device, !online); status.refresh(); };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex overflow-hidden rounded-md border border-line" role="group" aria-label="Device">
          {devices.map((d) => (
            <button key={d} type="button" onClick={() => setDevice(d)} aria-pressed={device === d}
              className={`min-h-11 px-4 py-1 text-sm ${device === d ? "btn-primary !rounded-none font-semibold" : "text-muted hover:text-ink"}`}>
              {label(d)}
            </button>
          ))}
        </div>
        <Button variant="secondary" onClick={toggleLink}>{online ? "Go offline" : "Reconnect"}</Button>
        <div className="flex items-center gap-2 rounded-md border border-line bg-surface/60 px-2.5 py-1 text-xs">
          <span className="text-muted">Route:</span>
          <select value={provider} onChange={(e) => {
            const val = e.target.value as "auto" | "gemini" | "local-slm" | "extractive";
            if (val === "gemini" && !status.data?.ai.gemini?.configured) setShowGeminiModal(true);
            setProvider(val);
          }} className="rounded bg-black/40 px-2 py-1 text-xs text-ink outline-none border border-line">
            <option value="auto">Auto (Local First &#8594; Cloud)</option>
            <option value="gemini">Google Gemini {status.data?.ai.gemini?.configured ? "✓" : "(Set Key)"}</option>
            <option value="local-slm">Local SLM (Ollama)</option>
            <option value="extractive">Rules Only (No LLM)</option>
          </select>
          <button type="button" onClick={() => setShowGeminiModal(!showGeminiModal)}
            className="text-[11px] text-muted hover:text-ink underline">
            {status.data?.ai.gemini?.configured ? `Gemini ${status.data?.ai.gemini?.model ?? "2.0-flash"}` : "Set Gemini Key"}
          </button>
        </div>
        <span className="text-sm text-muted">
          {online ? "Online: local AI preferred, sync running." : "Offline: everything below still works, changes queue on this device."}
        </span>
      </div>
      {showGeminiModal && (
        <div className="rounded-lg border border-[var(--rust-hot)]/40 bg-surface/95 p-3.5 shadow-lg">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-semibold text-ink">Configure Google Gemini for LLM Answers</h4>
            <button onClick={() => setShowGeminiModal(false)} className="text-xs text-muted hover:text-ink">✕</button>
          </div>
          <p className="mt-1 text-xs text-muted">
            Enter your Google Gemini API key. It will be used for cloud LLM answers when online (private Krypta memories are strictly protected and stay local).
          </p>
          <div className="mt-2.5 flex gap-2">
            <input type="password" placeholder="AIzaSy..." value={geminiKeyInput}
              onChange={(e) => setGeminiKeyInput(e.target.value)}
              className="flex-1 rounded border border-line bg-black/40 px-3 py-1.5 text-xs text-ink outline-none" />
            <Button variant="primary" onClick={saveGeminiKey}>Save Key</Button>
          </div>
          {geminiSaveMsg && <div className="mt-1.5 text-xs text-ok">{geminiSaveMsg}</div>}
        </div>
      )}
      {stage && (
        <div className="q-card hud flex flex-wrap items-center gap-x-4 gap-y-1 px-4 py-2" aria-live="polite">
          {STAGES.map((n, i) => (
            <span key={n} className={`label flex items-center gap-1.5 ${i + 1 === stage.n ? "!text-ink" : i + 1 < stage.n ? "!text-ok" : ""}`}>
              <span className="num font-mono">{String(i + 1).padStart(2, "0")}</span>{n}{i + 1 < stage.n ? " ✓" : ""}
            </span>
          ))}
          <span className="basis-full text-sm text-muted">{stage.note}</span>
          {stage.lifecycle && <div className="basis-full"><LifecycleStrip r={stage.lifecycle} /></div>}
        </div>
      )}
      <EdgeStrip s={status.data} />
      <ErrorNote error={status.error} />

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_340px]">
        <Card title={`Talk to Smaran on your ${label(device).toLowerCase()}`}>
          <div className="flex h-[520px] flex-col">
            <div className="flex-1 space-y-4 overflow-y-auto pr-1" aria-live="polite">
              {turns.length === 0 && (
                <Empty>Tell Smaran something to remember, ask about something you said before, or give it a task. Try a suggestion below.</Empty>
              )}
              {turns.map((t, i) => (
                <div key={i} className={t.who === "you" ? "ml-auto max-w-[85%]" : "max-w-[92%]"}>
                  {t.device && <div className={`label mb-0.5 ${t.who === "you" ? "text-right" : ""}`}>{label(t.device)}</div>}
                  <div className={`whitespace-pre-wrap rounded-lg px-3 py-2 text-sm ${t.who === "you" ? "bg-[var(--rust)]/25 text-ink" : "border border-line bg-white/[0.03]"}`}>{t.text}</div>
                  {t.result && <Trace r={t.result} device={t.device ?? device} aiLocal={aiLocal} onChange={() => { tasks.refresh(); status.refresh(); }} />}
                </div>
              ))}
              {busy && <div className="text-sm text-muted">Thinking on this device…</div>}
              <div ref={bottom} />
            </div>
            <ErrorNote error={err} />
            <div className="mt-3 flex flex-wrap gap-1.5">
              {PROMPTS.map((p) => (
                <button key={p} type="button" onClick={() => send(p)} disabled={busy}
                  className="rounded-full border border-line px-2.5 py-1 text-left text-xs text-muted hover:border-[var(--rust-hot)] hover:text-ink disabled:opacity-40">
                  {p.length > 58 ? p.slice(0, 56) + "…" : p}
                </button>
              ))}
            </div>
            <form className="mt-3 flex gap-2" onSubmit={(e) => { e.preventDefault(); send(text); }}>
              <input aria-label="Message" className={inputCls} value={text} onChange={(e) => setText(e.target.value)}
                placeholder="Remember this, ask me something, or give me a task…" />
              <Button type="submit" disabled={busy || !text.trim()}>Send</Button>
            </form>
          </div>
        </Card>

        <div className="space-y-4">
          {(conflicts.data?.length ?? 0) > 0 && (
            <Card title="Two devices disagree">
              <div className="space-y-3">
                {conflicts.data!.map((c) => <ConflictCard key={c.entity_key} c={c} busy={resolving} onKeep={(op) => keep(c.entity_key, op)} />)}
              </div>
            </Card>
          )}
          <Card title="Needs your attention">
            {(brief.data?.items.length ?? 0) === 0 ? <Empty>Nothing pending.</Empty> : (
              <ul className="space-y-2 text-sm">
                {brief.data!.items.map((b, i) => (
                  <li key={i} className="flex gap-2">
                    <Badge tone={b.level === "alert" ? "alert" : b.level === "warn" ? "gold" : "neutral"}>{b.level}</Badge>
                    <span>{b.text}</span>
                  </li>
                ))}
              </ul>
            )}
          </Card>
          <Card title={`Tasks (${tasks.data?.filter((t) => t.status === "open").length ?? 0} open)`}>
            {(tasks.data?.length ?? 0) === 0 ? <Empty>No tasks yet. Say “I need to …” or “Remind me …”.</Empty> : (
              <ul className="space-y-2 text-sm">
                {tasks.data!.map((t) => (
                  <li key={t.op_id} className={t.status === "open" ? "" : "text-muted line-through"}>
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span>{t.title}</span>
                      {t.conflict && <Badge tone="alert">conflict</Badge>}
                      {t.shard === "krypta" && <Badge tone="vault">private</Badge>}
                    </div>
                    <div className="text-xs text-muted no-underline">{t.due_text ? `due ${t.due_text}` : "no due time"}{t.subject ? ` · ${t.subject}` : ""}{t.status !== "open" ? ` · ${t.status}` : ""}</div>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
