// Small pieces shared by the Companion and Control Center views.
import type { ReactNode } from "react";
import type { CompanionStatus, Route } from "../api/companion";
import { Badge, Indicator } from "./ui";

export function RouteBadge({ route }: { route: Route }) {
  const meta = {
    "local-slm": { tone: "ok" as const, text: `On-device AI · ${route.model}` },
    extractive: { tone: "gold" as const, text: "Rules from local memory (no model)" },
    cloud: { tone: "live" as const, text: `Cloud · ${route.model}` },
    gemini: { tone: "live" as const, text: `Gemini · ${route.model}` },
    rules: { tone: "neutral" as const, text: "Rules · no model needed" },
  }[route.route] || { tone: "neutral" as const, text: `${route.route} · ${route.model}` };
  return <Badge tone={meta.tone} title={route.reason}>{meta.text}{route.latency_ms ? ` · ${Math.round(route.latency_ms)} ms` : ""}</Badge>;
}

export function Bar({ value, tone = "var(--rust-hot)" }: { value: number; tone?: string }) {
  return (
    <span className="inline-block h-1.5 w-16 overflow-hidden rounded-full bg-white/10 align-middle">
      <span className="block h-full rounded-full" style={{ width: `${Math.max(0, Math.min(1, value)) * 100}%`, background: tone }} />
    </span>
  );
}

function Block({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="tile !items-start !text-left">
      <div className="label mb-1.5 text-ink">{title}</div>
      <div className="space-y-1 text-[13px] leading-snug">{children}</div>
    </div>
  );
}

const Tick = ({ ok, children }: { ok: boolean; children: ReactNode }) => (
  <div className={ok ? "" : "text-muted"}>
    <span className={ok ? "text-ok" : "text-faint"}>{ok ? "✓" : "–"}</span> {children}
  </div>
);

/** The four-block "this is not a normal cloud chatbot" strip from the problem statement. */
export function EdgeStrip({ s }: { s: CompanionStatus | null }) {
  if (!s) return <div className="text-sm text-muted">Waiting for the device…</div>;
  const m = s.memory;
  return (
    <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
      <Block title="AI engine">
        <Tick ok={s.ai.local.available}>Local SLM {s.ai.local.available ? s.ai.local.model : "not running"}</Tick>
        <Tick ok={Boolean(s.ai.gemini?.configured || s.ai.cloud.configured)}>
          {s.ai.gemini?.configured
            ? `Gemini (${s.ai.gemini.model})`
            : s.ai.cloud.configured
            ? `Cloud (${s.ai.cloud.model})`
            : "Cloud / Gemini not configured"}
        </Tick>
        <div className="text-xs text-muted">Active route: {s.ai.active_route === "local-slm" ? "on device" : s.ai.active_route === "gemini" ? "Gemini cloud" : "rules from memory"}</div>
      </Block>
      <Block title="Memory">
        <Tick ok>Local vector index ({m.embedder})</Tick>
        <Tick ok>Chat + audit encrypted ({m.encryption.chat_and_audit})</Tick>
        <div className="text-xs text-muted">{m.counts.hermes + m.counts.agora + m.counts.krypta} memories · {m.counts.krypta} private · {m.counts.agora} from the cloud</div>
      </Block>
      <Block title="Connectivity">
        <Indicator tone={s.online ? "live" : "surface"}>{s.online ? "Online" : "Offline"}</Indicator>
        <div className="text-xs text-muted">{s.online ? "Local AI preferred · cloud is an enhancement" : "AI: on device · memory: local · queue is safe"}</div>
      </Block>
      <Block title="Sync">
        <div className="font-mono text-lg leading-none">{s.sync.queued}<span className="ml-1.5 text-xs text-muted">pending</span></div>
        <div className="text-xs text-muted">{s.sync.contested ? `${s.sync.contested} conflicting version(s)` : s.online ? "Sync complete" : "Will sync when the link returns"}</div>
      </Block>
    </div>
  );
}
