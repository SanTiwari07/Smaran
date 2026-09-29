import type { ReactNode } from "react";
import type { Decision, Shard, Status } from "../api/types";

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

const TONES = {
  neutral: "text-muted border-line bg-white/[0.03]",
  alert: "text-alert border-alert/40 bg-alert/10",
  ok: "text-ok border-ok/40 bg-ok/10",
  gold: "text-gold border-gold/40 bg-gold/10",
} as const;
export type Tone = keyof typeof TONES;

export function Badge({ tone = "neutral", children, title }: { tone?: Tone; children: ReactNode; title?: string }) {
  return (
    <span title={title}
      className={`inline-flex shrink-0 items-center gap-1 rounded border px-1.5 py-px text-[11px] font-semibold uppercase leading-4 tracking-wide ${TONES[tone]}`}>
      {children}
    </span>
  );
}

/** A coloured dot and a word, for states that change (online, offline). */
export function Indicator({ tone, children }: { tone: Tone; children: ReactNode }) {
  const dot = { neutral: "bg-faint", alert: "bg-alert", ok: "bg-ok", gold: "bg-gold" }[tone];
  return (
    <span className={`inline-flex items-center gap-1.5 whitespace-nowrap text-xs font-medium ${TONES[tone].split(" ")[0]}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${dot}`} />{children}
    </span>
  );
}

export const SHARD_META: Record<Shard, { name: string; tone: Tone; hint: string }> = {
  krypta: { name: "Krypta", tone: "gold", hint: "Private shard: never leaves the device" },
  hermes: { name: "Hermes", tone: "neutral", hint: "Mutable shard: waiting to sync" },
  agora: { name: "Agora", tone: "neutral", hint: "Mirror shard: fleet knowledge" },
  cloud: { name: "Cloud", tone: "neutral", hint: "Answered by Qdrant Server (escalated)" },
};

export function ShardBadge({ shard }: { shard: Shard }) {
  const m = SHARD_META[shard] ?? SHARD_META.cloud;
  return <Badge tone={m.tone} title={m.hint}>{m.name}</Badge>;
}

export function StatusBadge({ status }: { status: Status }) {
  return <Badge tone={status === "contested" ? "alert" : "neutral"}>{status}</Badge>;
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
      <div className={`num font-mono text-2xl font-medium leading-tight ${tone === "alert" ? "text-alert" : ""}`}>{value}</div>
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
        <span className="h-1.5 w-1.5 rotate-45" style={{ background: "var(--brand)" }} />
        <h3 className="label text-ink">{title}</h3>
        <span className="h-px flex-1 bg-line" />
      </div>
      {children}
    </div>
  );
}

const PIX: Record<string, string> = { h: "#e3e9ff", s: "#98a8dc", v: "#0e1530", r: "#dc244c", o: "#f5993c", g: "#4fd1a1", c: "#5d6886" };
const SUIT = [
  "....hhhhhh....",
  "..hhhhhhhhhh..",
  ".hhhvvvvvvhhs.",
  ".hhvvrrvvvvhs.",
  ".hhvvrvvvvvhs.",
  ".hhvvvvvvvvhs.",
  ".hhhvvvvvvhhs.",
  "..hhhhhhhhhs..",
  ".hhhhhhhhhhss.",
  "hhhhhccchhhhss",
  "hhhhhcgchhhhss",
  "hhhhhhhhhhhhss",
  ".hhhhhhhhhhss.",
  "..hhhh..hhhs..",
  "..hhhh..hhhs..",
  "..ooo...ooo...",
];
/** A pixel-art astronaut: one per device. `stripe` recolours the boots and chest light. */
export function Astronaut({ online = true, size = 44, stripe }: { online?: boolean; size?: number; stripe?: string }) {
  const light = online ? PIX.g : PIX.r;
  return (
    <svg viewBox="0 0 14 16" width={size} height={(size * 16) / 14} className="pix shrink-0" aria-hidden="true">
      {SUIT.flatMap((row, y) => [...row].map((ch, x) => {
        if (ch === ".") return null;
        const fill = ch === "g" ? light : ch === "o" ? (stripe ?? PIX.o) : PIX[ch];
        return <rect key={`${x}-${y}`} x={x} y={y} width="1.02" height="1.02" fill={fill} />;
      }))}
    </svg>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="py-6 text-sm text-muted">{children}</p>;
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
