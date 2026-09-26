import type { ReactNode } from "react";
import type { Shard, Status } from "../api/types";

export function Card({ title, right, children, className = "" }: {
  title?: ReactNode; right?: ReactNode; children: ReactNode; className?: string;
}) {
  return (
    <section className={`border border-line bg-panel ${className}`}>
      {title && (
        <header className="flex items-center justify-between gap-3 border-b border-line px-4 py-2.5">
          <h2 className="label min-w-0 truncate text-ink">{title}</h2>
          {right}
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}

const TONES = {
  neutral: "text-muted border-line",
  alert: "text-alert border-alert/40",
  ok: "text-ok border-ok/40",
  gold: "text-gold border-gold/40",
} as const;
export type Tone = keyof typeof TONES;

export function Badge({ tone = "neutral", children, title }: { tone?: Tone; children: ReactNode; title?: string }) {
  return (
    <span title={title}
      className={`inline-flex shrink-0 items-center gap-1 border px-1.5 py-px text-[11px] font-medium uppercase leading-4 tracking-wide ${TONES[tone]}`}>
      {children}
    </span>
  );
}

/** A coloured dot and a word, for states that change (online, offline). */
export function Indicator({ tone, children }: { tone: Tone; children: ReactNode }) {
  const dot = { neutral: "bg-faint", alert: "bg-alert", ok: "bg-ok", gold: "bg-gold" }[tone];
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${TONES[tone].split(" ")[0]}`}>
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
    primary: "border-ink bg-ink text-paper hover:opacity-85",
    secondary: "border-line bg-panel text-ink hover:border-muted",
  }[variant];
  return (
    <button type={type} title={title} disabled={disabled} onClick={onClick}
      className={`inline-flex shrink-0 items-center justify-center gap-1.5 border px-3 py-1.5 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-40 ${v}`}>
      {children}
    </button>
  );
}

export function Stat({ label, value, hint, tone }: { label: string; value: ReactNode; hint?: string; tone?: "alert" }) {
  return (
    <div title={hint} className="min-w-0">
      <div className={`num text-2xl leading-tight ${tone === "alert" ? "text-alert" : ""}`}>{value}</div>
      <div className="label mt-0.5 truncate tracking-[0.04em]">{label}</div>
    </div>
  );
}

/** A row of stats separated by hairlines. */
export function StatRow({ children, cols }: { children: ReactNode; cols: 2 | 3 | 4 }) {
  // four stats wrap to two rows on phones, so the third starts a row and loses its divider there
  const c = {
    2: "grid-cols-2", 3: "grid-cols-3",
    4: "grid-cols-2 sm:grid-cols-4 [&>*:nth-child(3)]:border-l-0 [&>*:nth-child(3)]:pl-0 sm:[&>*:nth-child(3)]:border-l sm:[&>*:nth-child(3)]:pl-3",
  }[cols];
  return <div className={`grid ${c} gap-y-3 [&>*]:border-line [&>*]:px-3 [&>*:not(:first-child)]:border-l [&>*:first-child]:pl-0`}>{children}</div>;
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="py-6 text-sm text-muted">{children}</p>;
}

export function ErrorNote({ error }: { error: string | null }) {
  if (!error) return null;
  return <p className="border-l-2 border-alert py-1 pl-3 text-sm text-alert">{error}</p>;
}

export const inputCls =
  "w-full border border-line bg-paper px-3 py-1.5 text-sm text-ink outline-none placeholder:text-faint focus:border-ink";

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
