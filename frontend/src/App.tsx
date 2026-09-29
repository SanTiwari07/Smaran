import { useEffect, useState } from "react";
import { api, DEVICES, USE_MOCK } from "./api/client";
import AutoPlay, { autoMode } from "./auto/AutoPlay";
import { Badge } from "./components/ui";
import { usePoll } from "./hooks/usePoll";
import ConflictsDecisions from "./views/ConflictsDecisions";
import DevicesSync from "./views/DevicesSync";
import MemorySearch from "./views/MemorySearch";

const TABS = [
  { id: "devices", label: "Devices and sync" },
  { id: "memory", label: "Memory and search" },
  { id: "conflicts", label: "Conflicts and decisions" },
] as const;
type Tab = (typeof TABS)[number]["id"];

function readTab(): Tab {
  const h = window.location.hash.slice(1);
  return (TABS.some((t) => t.id === h) ? h : "devices") as Tab;
}

const STORY_URL = (import.meta.env.VITE_STORY_URL as string | undefined) ?? "/story/";

export default function App() {
  const [tab, setTab] = useState<Tab>(readTab);
  const [device, setDevice] = useState("A");
  const contested = usePoll(() => api.gwContested().then((g) => g.length), [], 2000);

  useEffect(() => {
    const onHash = () => setTab(readTab());
    const onDevice = (e: Event) => setDevice((e as CustomEvent<string>).detail);
    window.addEventListener("hashchange", onHash);
    window.addEventListener("smaran:device", onDevice);   // sent by the auto demo
    return () => {
      window.removeEventListener("hashchange", onHash);
      window.removeEventListener("smaran:device", onDevice);
    };
  }, []);
  const auto = autoMode();

  return (
    <div className="min-h-screen">
      {auto !== "off" && <AutoPlay mode={auto} />}
      <header className="sticky top-0 z-20 border-b border-line bg-paper/85 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-wrap items-end gap-x-8 gap-y-2 px-4 pt-3">
          <div className="flex items-baseline gap-3 pb-2.5">
            <img src="/logo.svg" alt="" className="h-7 w-[22px]" />
            <span className="text-xl font-semibold tracking-tight">Smaran</span>
            <span className="hidden text-sm text-muted sm:inline">mission control</span>
          </div>
          <nav className="-mb-px flex flex-wrap gap-5" aria-label="Views">
            {TABS.map((t) => (
              <a key={t.id} href={`#${t.id}`} onClick={() => setTab(t.id)}
                aria-current={tab === t.id ? "page" : undefined}
                className={`flex items-center gap-2 border-b-2 pb-2.5 text-sm font-semibold ${tab === t.id ? "border-brand text-ink" : "border-transparent text-muted hover:text-ink"}`}>
                {t.label}
                {t.id === "conflicts" && (contested.data ?? 0) > 0 && (
                  <span className="num rounded bg-alert px-1.5 text-xs font-semibold leading-5 text-paper">{contested.data}</span>
                )}
              </a>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-3 pb-2">
            {USE_MOCK && <Badge tone="gold">mock API</Badge>}
            <a href={STORY_URL} className="btn-outline inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-semibold transition hover:bg-white/5">
              <span aria-hidden="true">←</span> Back to story
            </a>
            {tab !== "devices" && (
              <div className="flex overflow-hidden rounded-lg border border-line" role="group" aria-label="Device">
                {Object.keys(DEVICES).map((d) => (
                  <button key={d} type="button" onClick={() => setDevice(d)} aria-pressed={device === d}
                    className={`px-3 py-1 text-sm ${device === d ? "btn-primary !rounded-none font-semibold" : "text-muted hover:text-ink"}`}>
                    Device {d}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-5">
        {tab === "devices" && <DevicesSync />}
        {tab === "memory" && <MemorySearch device={device} />}
        {tab === "conflicts" && <ConflictsDecisions device={device} />}
      </main>
      <footer className="mx-auto mt-4 grid border-t border-line pt-5  max-w-7xl gap-x-6 gap-y-1 px-4 pb-6 text-xs text-muted sm:grid-cols-4">
        <p><span className="text-ink">Krypta</span> keeps what's private</p>
        <p><span className="text-ink">Hermes</span> carries the rest when the link returns</p>
        <p><span className="text-ink">Agora</span> shares what the fleet knows</p>
        <p><span className="text-ink">Themis</span> decides what's true</p>
      </footer>
    </div>
  );
}
