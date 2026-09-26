import { Cloud, Landmark, Lock, Send } from "lucide-react";
import type { ReactNode } from "react";
import type { Shard, Status } from "../api/types";

export function Card({ title, icon, right, children, className = "" }: {
  title?: ReactNode; icon?: ReactNode; right?: ReactNode; children: ReactNode; className?: string;
}) {
  return (
    <section className={`rounded-xl border border-stone-200 bg-white shadow-sm dark:border-stone-800 dark:bg-stone-900 ${className}`}>
      {title && (
        <header className="flex items-center justify-between gap-3 border-b border-stone-100 px-4 py-3 dark:border-stone-800">
          <h2 className="flex min-w-0 items-center gap-2 text-sm font-semibold">
            {icon}
            <span className="truncate">{title}</span>
          </h2>
          {right}
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}

const TONES = {
  neutral: "bg-stone-100 text-stone-700 dark:bg-stone-800 dark:text-stone-300",
  green: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300",
  red: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300",
  amber: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  sky: "bg-sky-100 text-sky-800 dark:bg-sky-950 dark:text-sky-300",
  violet: "bg-violet-100 text-violet-800 dark:bg-violet-950 dark:text-violet-300",
  gold: "bg-amber-50 text-amber-900 ring-1 ring-amber-300 dark:bg-amber-950/40 dark:text-amber-200 dark:ring-amber-800",
} as const;
export type Tone = keyof typeof TONES;

export function Badge({ tone = "neutral", children, title }: { tone?: Tone; children: ReactNode; title?: string }) {
  return (
    <span title={title} className={`inline-flex shrink-0 items-center gap-1 rounded-md px-1.5 py-0.5 text-xs font-medium ${TONES[tone]}`}>
      {children}
    </span>
  );
}

export const SHARD_META: Record<Shard, { name: string; tone: Tone; icon: ReactNode; hint: string }> = {
  krypta: { name: "Krypta", tone: "violet", icon: <Lock size={12} />, hint: "Private shard: never leaves the device" },
  hermes: { name: "Hermes", tone: "amber", icon: <Send size={12} />, hint: "Mutable shard: waiting to sync" },
  agora: { name: "Agora", tone: "sky", icon: <Landmark size={12} />, hint: "Mirror shard: fleet knowledge" },
  cloud: { name: "Cloud", tone: "neutral", icon: <Cloud size={12} />, hint: "Answered by Qdrant Server (escalated)" },
};

export function ShardBadge({ shard }: { shard: Shard }) {
  const m = SHARD_META[shard] ?? SHARD_META.cloud;
  return <Badge tone={m.tone} title={m.hint}>{m.icon}{m.name}</Badge>;
}

export function StatusBadge({ status }: { status: Status }) {
  const tone: Tone = status === "current" ? "green" : status === "contested" ? "red" : "neutral";
  return <Badge tone={tone}>{status}</Badge>;
}

export function CritBadge({ level }: { level: number }) {
  if (level >= 2) return <Badge tone="red">safety-critical</Badge>;
  if (level === 1) return <Badge tone="amber">important</Badge>;
  return <Badge>routine</Badge>;
}

export function Button({ children, onClick, variant = "primary", disabled, type = "button", title }: {
  children: ReactNode; onClick?: () => void; variant?: "primary" | "secondary" | "ghost" | "danger";
  disabled?: boolean; type?: "button" | "submit"; title?: string;
}) {
  const v = {
    primary: "bg-ink text-white hover:bg-indigo-900 dark:bg-indigo-500 dark:hover:bg-indigo-400 dark:text-stone-950",
    secondary: "border border-stone-300 bg-white hover:bg-stone-50 dark:border-stone-700 dark:bg-stone-900 dark:hover:bg-stone-800",
    ghost: "hover:bg-stone-100 dark:hover:bg-stone-800",
    danger: "bg-red-600 text-white hover:bg-red-700",
  }[variant];
  return (
    <button type={type} title={title} disabled={disabled} onClick={onClick}
      className={`inline-flex items-center justify-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50 ${v}`}>
      {children}
    </button>
  );
}

export function Switch({ checked, onChange, label, disabled }: {
  checked: boolean; onChange: (v: boolean) => void; label: string; disabled?: boolean;
}) {
  return (
    <button type="button" role="switch" aria-checked={checked} aria-label={label} disabled={disabled}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition ${checked ? "bg-emerald-500" : "bg-stone-300 dark:bg-stone-700"} disabled:opacity-50`}>
      <span className={`inline-block h-5 w-5 rounded-full bg-white shadow transition ${checked ? "translate-x-5" : "translate-x-0.5"}`} />
    </button>
  );
}

export function Stat({ label, value, hint, tone }: { label: string; value: ReactNode; hint?: string; tone?: "red" | "green" }) {
  const c = tone === "red" ? "text-red-600 dark:text-red-400" : tone === "green" ? "text-emerald-600 dark:text-emerald-400" : "";
  return (
    <div title={hint} className="min-w-0">
      <div className="truncate text-xs text-stone-500 dark:text-stone-400">{label}</div>
      <div className={`num text-lg font-semibold ${c}`}>{value}</div>
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="py-6 text-center text-sm text-stone-500 dark:text-stone-400">{children}</p>;
}

export function ErrorNote({ error }: { error: string | null }) {
  if (!error) return null;
  return (
    <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950/50 dark:text-red-300">{error}</p>
  );
}

export const inputCls =
  "w-full rounded-lg border border-stone-300 bg-white px-3 py-1.5 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 dark:border-stone-700 dark:bg-stone-950";

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
  new Date(ts * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });

export function bytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(2)} MB`;
}

export const vvText = (vv: Record<string, number>) =>
  Object.entries(vv).sort().map(([k, v]) => `${k}:${v}`).join(" ");
