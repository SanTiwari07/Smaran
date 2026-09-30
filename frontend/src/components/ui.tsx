import type { ReactNode } from "react";
import type { Decision, Shard, Status } from "../api/types";
import { Helmet } from "./scenery";

export function Card({ title, right, children, className = "" }: {
  title?: ReactNode; right?: ReactNode; children: ReactNode; className?: string;
}) {
  return (
    <section className={`q-card hud ${className}`}>
      {title && (
        <header className="flex items-center justify-between gap-3 border-b border-line px-4 py-3">
          <h2 className="label min-w-0 truncate text-ink">{title}</h2>
          {right}
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}

// Instrument colours only: live (relay in view), ok (nominal), gold (caution / contested / needs a human),
// vault (private), surface (offline: a place, not an error), alert (a real failure or safety-critical).
const TONES = {
  neutral: "text-muted border-line bg-white/[0.03]",
  alert: "text-alert border-alert/40 bg-alert/10",
  ok: "text-ok border-ok/40 bg-ok/10",
  gold: "text-gold border-gold/40 bg-gold/10",
  live: "text-live border-live/40 bg-live/10",
  vault: "text-vault border-vault/40 bg-vault/10",
  surface: "text-surface border-surface/40 bg-surface/10",
} as const;
export type Tone = keyof typeof TONES;

export function Badge({ tone = "neutral", children, title }: { tone?: Tone; children: ReactNode; title?: string }) {
  return (
    <span title={title}
      className={`inline-flex shrink-0 items-center gap-1 rounded-full border px-2 py-px font-mono text-[11px] font-medium uppercase leading-4 tracking-[0.1em] ${TONES[tone]}`}>
      {children}
    </span>
  );
}

/** A coloured dot and a word, for states that change. A hollow dot means "on the surface" (offline). */
export function Indicator({ tone, children }: { tone: Tone; children: ReactNode }) {
  const dot = {
    neutral: "bg-faint", alert: "bg-alert", ok: "bg-ok", gold: "bg-gold", live: "bg-live pulse-dot",
    vault: "bg-vault", surface: "border-[1.5px] border-current",
  }[tone];
  return (
    <span className={`inline-flex items-center gap-1.5 whitespace-nowrap font-mono text-[11px] font-medium uppercase tracking-[0.1em] ${TONES[tone].split(" ")[0]}`}>
      <span className={`h-[7px] w-[7px] rounded-full ${dot}`} />{children}
    </span>
  );
}

export const SHARD_META: Record<Shard, { name: string; tone: Tone; hint: string }> = {
  krypta: { name: "Krypta", tone: "vault", hint: "Sealed vault: never leaves the device" },
  hermes: { name: "Hermes", tone: "neutral", hint: "Manifest: waits for the next relay pass" },
  agora: { name: "Agora", tone: "neutral", hint: "Colony hub: what the whole fleet knows" },
  cloud: { name: "Cloud", tone: "neutral", hint: "Answered by Qdrant Server (escalated)" },
};

export function ShardBadge({ shard }: { shard: Shard }) {
  const m = SHARD_META[shard] ?? SHARD_META.cloud;
  return <Badge tone={m.tone} title={m.hint}>{m.name}</Badge>;
}

export function StatusBadge({ status }: { status: Status }) {
  return <Badge tone={status === "contested" ? "gold" : "neutral"}>{status}</Badge>;
}

export function CritBadge({ level }: { level: number }) {
  if (level >= 2) return <Badge tone="alert">safety-critical</Badge>;
  if (level === 1) return <Badge tone="gold">important</Badge>;
  return <Badge>routine</Badge>;
}

export function Button({ children, onClick, variant = "primary", disabled, type = "button", title }: {
  children: ReactNode; onClick?: () => void; variant?: "primary" | "secondary";
  disabled?: boolean; type?: "button" | "submit"; title?: string;
}) {
  const v = {
    primary: "btn-primary",
    secondary: "btn-outline",
  }[variant];
  return (
    <button type={type} title={title} disabled={disabled} onClick={onClick}
      className={`inline-flex shrink-0 items-center justify-center gap-1.5 px-3.5 py-1.5 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-40 ${v}`}>
      {children}
    </button>
  );
}

export function Stat({ label, value, hint, tone }: { label: string; value: ReactNode; hint?: string; tone?: "alert" }) {
  return (
    <div title={hint} className="tile">
      <div className={`num font-mono text-2xl font-medium leading-tight ${tone === "alert" ? "text-gold" : ""}`}>{value}</div>
      <div className="label mt-1 tracking-[0.04em]">{label}</div>
    </div>
  );
}

/** A row of telemetry tiles. */
export function StatRow({ children, cols }: { children: ReactNode; cols: 2 | 3 | 4 }) {
  const c = { 2: "grid-cols-2", 3: "grid-cols-3", 4: "grid-cols-2 sm:grid-cols-4" }[cols];
  return <div className={`grid ${c} gap-2`}>{children}</div>;
}

/** A small labelled group inside a panel ("Sync", "Recovery"). */
export function Group({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div>
      <div className="mb-2 flex items-center gap-2">
        <span className="h-1.5 w-1.5 rotate-45" style={{ background: "var(--rust-hot)" }} />
        <h3 className="label text-ink">{title}</h3>
        <span className="h-px flex-1 bg-line" />
      </div>
      {children}
    </div>
  );
}

/** The crew helmet: one per device. The visor is cyan with the relay in view, dust when on the surface. */
export function Astronaut({ online = true, size = 44, stripe }: { online?: boolean; size?: number; stripe?: string }) {
  return <Helmet size={size} visor={online ? "#3de0e6" : "#d9a066"} patch={stripe} />;
}

export function Empty({ children }: { children: ReactNode }) {
  return (
    <div className="flex items-center gap-4 py-6">
      <svg viewBox="0 0 64 40" width="64" height="40" aria-hidden="true" className="shrink-0">
        <path d="M0 34Q16 28 32 33T64 31V40H0Z" fill="#7a2a12" />
        <line x1="40" y1="8" x2="40" y2="33" stroke="#b9afa6" strokeWidth="1.5" />
        <path d="M40 9h11l-3 4 3 4H40z" fill="#c1440e" />
      </svg>
      <p className="text-sm text-muted">{children}</p>
    </div>
  );
}

export function ErrorNote({ error }: { error: string | null }) {
  if (!error) return null;
  return <p className="border-l-2 border-alert py-1 pl-3 text-sm text-alert">{error}</p>;
}

export const inputCls =
  "w-full rounded-lg border border-line bg-paper/70 px-3 py-2 text-sm text-ink outline-none placeholder:text-faint focus:border-brand focus:ring-1 focus:ring-brand/60";

export function ago(ts: number | null | undefined): string {
  if (!ts) return "never";
  const s = Math.max(0, Date.now() / 1000 - ts);
  if (s < 5) return "just now";
  if (s < 60) return `${Math.floor(s)}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

export const clock = (ts: number) =>
  new Date(ts * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false });

export function bytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(2)} MB`;
}

export const vvText = (vv: Record<string, number>) =>
  Object.entries(vv).sort().map(([k, v]) => `${k}:${v}`).join(" ");

const BY_LABEL: Record<string, string> = {
  pii_rule: "PII rule", classifier: "classifier", rule: "rule", dedup: "dedup", seed: "fleet seed", supervisor: "supervisor",
};

/** "Why here?": which Argus layer placed this memory, how sure it was, and the full reason. */
export function WhyHere({ decision, shard }: { decision?: Decision; shard?: Shard }) {
  if (!decision) return null;
  const by = BY_LABEL[decision.by] ?? decision.by;
  const conf = decision.by === "classifier" || decision.by === "dedup" ? ` ${decision.confidence.toFixed(2)}` : "";
  const where = shard ? `${SHARD_META[shard]?.name ?? shard} · ` : "";
  return (
    <p className="mt-0.5 text-xs text-muted" title={decision.reason}>
      <span className="label mr-1 tracking-[0.04em]">Why here</span>
      {where}{by}{conf}: <span className="text-faint">{decision.reason}</span>
    </p>
  );
}
