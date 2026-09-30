// Evidence panels for the companion: what was remembered, why an answer or action happened,
// which memory contradicts which, and what has aged out. Every value shown comes from an API response.
import { useState } from "react";
import { companion, type ActionResult, type ChatResult, type Conflict, type Contradiction, type Explain, type LifecycleReport, type Provenance } from "../api/companion";
import { Badge, Button, type Tone } from "./ui";

const clean = (t: string) => t.split(" Original:")[0];
const pct = (n: number) => `${Math.round(n * 100)}%`;

function Stage({ n, title, children }: { n?: string; title: string; children: React.ReactNode }) {
  return (
    <div className="rounded border border-line bg-black/20 p-3">
      <div className="label mb-2 flex items-center gap-2 text-ink">{n && <span className="num font-mono text-[var(--rust-hot)]">{n}</span>}{title}</div>
      {children}
    </div>
  );
}

/** REMEMBER: what Smaran extracted from a message, as structured memory. */
export function MemoryCreated({ actions }: { actions: ActionResult[] }) {
  const rows = actions.filter((a) => a.state === "executed" && ["store_memory", "create_task", "set_reminder"].includes(a.tool) && !a.contradiction);
  if (!rows.length) return null;
  return (
    <Stage title="Memory created">
      <ul className="space-y-1.5 text-sm">
        {rows.map((a, i) => {
          const args = a.args as { text?: string; kind?: string; title?: string; fields?: { reason?: string; decision_value?: string }; confidence?: number };
          const kind = a.tool === "store_memory" ? args.kind ?? "note" : "task";
          const text = a.tool === "store_memory" ? clean(args.text ?? "") : args.title ?? a.message;
          return (
            <li key={i} className="flex flex-wrap items-baseline gap-2">
              <Badge tone={kind === "decision" ? "gold" : kind === "task" ? "live" : "neutral"}>{kind}</Badge>
              <span>{text}</span>
              {args.fields?.reason && <span className="text-xs text-ok">reason: {args.fields.reason}</span>}
              {a.residency === "private" && <Badge tone="vault">private</Badge>}
            </li>
          );
        })}
      </ul>
    </Stage>
  );
}

/** A decision that contradicts a live one is held; the user answers. */
export function ContradictionCard({ c, device, onDone }: { c: Contradiction; device: string; onDone: (r: ActionResult) => void }) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const go = async (keep: "new" | "old") => {
    setBusy(true);
    try { onDone(await companion.resolveDecision(device, c.id, keep)); } catch (e) { setErr(e instanceof Error ? e.message : String(e)); } finally { setBusy(false); }
  };
  return (
    <div className="rounded border border-gold/50 bg-gold/10 p-3 text-sm">
      <div className="label mb-2 text-gold">Conflicting memory</div>
      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <div className="label">Previous decision</div>
          <div className="font-semibold">{c.previous.value}</div>
          <div className="text-xs text-muted">{c.previous.reason ? `because ${c.previous.reason}` : "no reason recorded"} · {c.previous.at_text}</div>
        </div>
        <div>
          <div className="label">New statement</div>
          <div className="font-semibold">{c.new.value}</div>
          <div className="text-xs text-muted">{c.new.stance === "proposal" ? "proposal" : "stated"}{c.new.reason ? ` · because ${c.new.reason}` : ""}</div>
        </div>
      </div>
      <p className="mt-2 text-xs text-muted">Reason for conflict: {c.why} Nothing was overwritten.</p>
      <p className="mt-1">Has the decision changed?</p>
      <div className="mt-2 flex flex-wrap gap-2">
        <Button disabled={busy} onClick={() => go("new")}>Yes, switch to {c.new.value}</Button>
        <Button disabled={busy} variant="secondary" onClick={() => go("old")}>No, keep {c.previous.value}</Button>
      </div>
      {err && <div className="mt-1 text-xs text-alert">{err}</div>}
    </div>
  );
}

const TREE = "border-l border-line pl-3";

/** "Why did Smaran say this?": source, time, reason, confidence with its parts. */
export function ProvenanceCard({ p }: { p: Provenance }) {
  const d = p.decision;
  const tone: Tone = p.status === "contested" ? "alert" : p.status === "superseded" ? "neutral" : "ok";
  return (
    <Stage title="Why does Smaran believe this?">
      <div className="mb-2 flex flex-wrap items-center gap-2 text-sm">
        <span className="font-semibold">{d ? `${d.value} (${d.category.replace("-", " ")})` : clean(p.text)}</span>
        <Badge tone={tone}>{p.status}</Badge>
        <Badge>{p.lifecycle.state}</Badge>
        {p.subject_label && <Badge>{p.subject_label}</Badge>}
      </div>
      {p.resolution && p.status === "current" && (
        <div className="mb-2 rounded border border-ok/40 bg-ok/10 p-2 text-xs">
          <div className="label mb-1 text-ok">Memory updated</div>
          <div><span className="label mr-2">Previous</span>{p.history.filter((h) => h.status === "superseded").map((h) => h.text.replace(/^The /, "")).slice(-2).join(" vs ")} (conflicting)</div>
          <div><span className="label mr-2">Current</span>{clean(p.text)}</div>
          <div><span className="label mr-2">Source</span>{p.source.type}</div>
        </div>
      )}
      <ul className={`${TREE} space-y-1 text-xs`}>
        <li><span className="label mr-2">Source</span>{p.source.type}{p.source.device ? ` on ${p.source.device}` : ""}: “{clean(p.source.quote)}”</li>
        <li><span className="label mr-2">Recorded</span>{p.at_text}</li>
        {d && <li><span className="label mr-2">Reason</span>{d.reason ?? "none recorded"}</li>}
        {d && d.supersedes.length > 0 && <li><span className="label mr-2">Replaced</span>{d.supersedes.length} earlier decision, kept as history</li>}
        {p.resolution && <li><span className="label mr-2">Resolution</span>{p.resolution.mode}{p.resolution.by ? ` by ${p.resolution.by}` : ""}</li>}
        {p.supporting.length > 0 && (
          <li><span className="label mr-2">Supported by</span>{p.supporting.map((s) => clean(s.text)).join("; ")}</li>
        )}
        {p.history.length > 1 && (
          <li>
            <span className="label mr-2">History</span>
            <ol className="ml-4 mt-0.5 list-decimal">
              {p.history.map((h) => <li key={h.op_id}>{h.text.replace(/^(TODO|DONE): /, "")} <span className="text-muted">· {h.device}{h.at_text ? `, ${h.at_text}` : ""} · {h.status}</span></li>)}
            </ol>
          </li>
        )}
        <li>
          <span className="label mr-2">Confidence</span><span className="num font-mono text-ink">{pct(p.confidence.value)}</span>
          <span className="ml-2 text-muted">
            = {p.confidence.parts.map((c) => c.op === "multiply" ? `×${c.value} ${c.label}` : `${c.value >= 0 && c.op === "add" ? "+" : ""}${c.value} ${c.label}`).join(" ")}
          </span>
        </li>
        <li className="text-muted"><span className="label mr-2">Lifecycle</span>{p.lifecycle.reason} ({p.lifecycle.persistence})</li>
      </ul>
    </Stage>
  );
}

/** "Why did Smaran do that?": intent -> memory -> decision -> tool -> result. */
export function ExplainCard({ e, title = "Why did Smaran do this?" }: { e: Explain; title?: string }) {
  return (
    <Stage title={title}>
      <ol className="space-y-2 text-sm">
        {e.chain.map((s, i) => (
          <li key={i} className="grid grid-cols-[110px_1fr] gap-2">
            <span className="label">{i + 1} · {s.stage}</span>
            <div className={`${TREE} min-w-0`}>
              {s.text && <div className={i === 0 ? "italic" : ""}>{i === 0 ? `“${s.text}”` : s.text}</div>}
              {s.items?.map((it, j) => <div key={j} className={s.stage === "Tool" ? "font-mono text-xs" : "text-xs"}>{s.stage === "Relevant memory" ? "• " : ""}{it}</div>)}
            </div>
          </li>
        ))}
      </ol>
      <div className="mt-2 flex flex-wrap gap-1.5">
        <Badge tone={e.online ? "live" : "surface"}>{e.mode}</Badge>
        <Badge title={e.model}>{e.planner === "local-slm" ? "planned by local SLM" : "planned on-device by rules"}</Badge>
        {e.queued > 0 && <Badge tone="gold">{e.queued} queued to sync</Badge>}
      </div>
    </Stage>
  );
}

/** ACT: the four facts that make "it still works offline" checkable. */
export function OfflineProof({ r, aiLocal }: { r: ChatResult; aiLocal: boolean }) {
  const off = !r.online_at_start;
  const mem = !r.retrieval || r.retrieval.answered === "local";
  const done = r.actions.some((a) => a.state === "executed");
  const chips: [string, boolean, string][] = [
    [off ? "Offline" : "Online", off, off ? "the link was off when this ran" : "link was up"],
    [aiLocal ? "Local AI ready" : "On-device rules", true, aiLocal ? "an on-device model is available (llama.cpp via Ollama); this request needed none, so rules planned it on this device" : "no model needed: planned on-device by rules"],
    ["Local memory", mem, "retrieval and writes used the Qdrant Edge shards on this device"],
    ["Action executed", done, r.actions.map((a) => a.message).join(" | ")],
  ];
  return (
    <div className="flex flex-wrap gap-2">
      {chips.map(([t, ok, hint]) => <Badge key={t} tone={ok ? (t.startsWith("Off") ? "surface" : "ok") : "alert"} title={hint}>{ok ? "✓" : "✕"} {t}</Badge>)}
    </div>
  );
}

/** RECONCILE: two devices disagreed; Smaran explains it and, if memory supports one side, says which. */
export function ConflictCard({ c, onKeep, busy }: { c: Conflict; onKeep: (op_id: string) => void; busy: boolean }) {
  return (
    <div className="rounded border border-gold/50 bg-gold/10 p-3 text-sm">
      <div className="label mb-1 text-gold">Conflict · {c.label}</div>
      <p className="text-xs text-muted">{c.explanation}</p>
      <div className="mt-2 grid gap-2 sm:grid-cols-2">
        {c.versions.map((v) => (
          <div key={v.op_id} className={`rounded border p-2 ${v.op_id === c.suggestion.op_id ? "border-ok/50" : "border-line"}`}>
            <div className="label">{v.device_label} · {v.at_text}</div>
            <div>{v.text}</div>
            <div className="mt-1"><Button disabled={busy} variant={v.op_id === c.suggestion.op_id ? "primary" : "secondary"} onClick={() => onKeep(v.op_id)}>Keep {v.when ?? "this"}</Button></div>
          </div>
        ))}
      </div>
      <p className="mt-2 text-xs"><Badge tone={c.suggestion.basis === "context" ? "ok" : "neutral"}>{c.suggestion.basis === "context" ? "supported by memory" : "no supporting evidence"}</Badge> {c.suggestion.reason}</p>
    </div>
  );
}

/** Memory that has aged out: the state, not a deletion. */
export function LifecycleStrip({ r }: { r: LifecycleReport }) {
  const tones: Record<string, Tone> = { temporary: "live", active: "ok", stale: "gold", archived: "neutral" };
  return (
    <Stage title="Smaran remembers what matters">
      <div className="flex flex-wrap gap-2">
        {(["temporary", "active", "stale", "archived"] as const).map((k) => <Badge key={k} tone={tones[k]}>{r.counts[k]} {k}</Badge>)}
      </div>
      <ul className="mt-2 space-y-1 text-xs text-muted">
        {r.examples.archived.slice(0, 3).map((x) => <li key={x.op_id}><span className="text-ink">archived</span> · {x.text} <span className="text-faint">({x.reason})</span></li>)}
      </ul>
      <p className="mt-1 text-xs text-faint">{r.note}</p>
    </Stage>
  );
}
