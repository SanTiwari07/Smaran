import { useEffect, useState } from "react";
import { api, DEVICES, USE_MOCK } from "./api/client";
import AutoPlay, { autoMode } from "./auto/AutoPlay";
import { Badge, Indicator } from "./components/ui";
import { Horizon, Starfield } from "./components/scenery";
import { usePoll } from "./hooks/usePoll";
import Companion from "./views/Companion";
import ConflictsDecisions from "./views/ConflictsDecisions";
import ControlCenter from "./views/ControlCenter";
import DevicesSync from "./views/DevicesSync";
import MemorySearch from "./views/MemorySearch";
import ProveIt from "./views/ProveIt";

const TABS = [
  { id: "companion", label: "Companion" },
  { id: "control", label: "Control center" },
  { id: "devices", label: "Devices and sync" },
  { id: "memory", label: "Memory and search" },
  { id: "conflicts", label: "Conflicts" },
  { id: "prove", label: "Prove it" },
] as const;
type Tab = (typeof TABS)[number]["id"];

function readTab(): Tab {
  const h = window.location.hash.slice(1);
  return (TABS.some((t) => t.id === h) ? h : "companion") as Tab;
}

const STORY_URL = (import.meta.env.VITE_STORY_URL as string | undefined) ?? "/story/";
const pad = (n: number) => String(n).padStart(2, "0");

/** Mission clock: counts up from page load, in mono, like the story's T+ stamps. */
function MissionClock() {
  const [s, setS] = useState(0);
  useEffect(() => {
    const t0 = Date.now();
    const id = window.setInterval(() => setS(Math.floor((Date.now() - t0) / 1000)), 1000);
    return () => window.clearInterval(id);
  }, []);
  return <span className="num hidden font-mono text-xs text-live sm:inline" title="Mission time">T+{pad(Math.floor(s / 3600))}:{pad(Math.floor(s / 60) % 60)}:{pad(s % 60)}</span>;
}

export default function App() {
  const [tab, setTab] = useState<Tab>(readTab);
  const [device, setDevice] = useState("A");
  const contested = usePoll(() => api.gwContested().then((g) => g.length), [], 2000);
  const ids = Object.keys(DEVICES);
  const states = usePoll(() => Promise.all(ids.map((d) => api.state(d).catch(() => null))), [], 2000);
  const known = (states.data ?? []).filter(Boolean);
  const onSurface = known.filter((x) => x && !x.online).length;

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
      <Starfield dim={onSurface > 0} />
      {auto !== "off" && <AutoPlay mode={auto} />}
      <header className="sticky top-0 z-20 border-b border-line bg-[var(--basalt)]/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-8 gap-y-1 px-4">
          <div className="flex h-14 items-center gap-2.5">
            <img src="/logo.svg" alt="" className="h-[30px] w-[30px]" />
            <span className="font-display text-xl font-bold tracking-[0.02em]">smaran</span>
            <span className="label hidden md:inline">mission control</span>
          </div>
          <nav className="flex flex-wrap" aria-label="Views">
            {TABS.map((t) => (
              <a key={t.id} href={`#${t.id}`} onClick={() => setTab(t.id)}
                aria-current={tab === t.id ? "page" : undefined}
                className={`label relative flex h-14 items-center gap-2 px-3.5 ${tab === t.id ? "!text-ink" : "hover:!text-ink"}`}>
                {t.label}
                {t.id === "conflicts" && (contested.data ?? 0) > 0 && (
                  <span className="num rounded-full bg-gold px-1.5 text-[11px] font-semibold leading-5 text-paper">{contested.data}</span>
                )}
                {tab === t.id && (
                  <>
                    <span className="absolute inset-x-3.5 bottom-0 h-0.5 bg-[var(--rust-hot)]" />
                    <span className="absolute bottom-0.5 left-1/2 -translate-x-1/2 border-4 border-transparent border-b-[var(--rust-hot)]" />
                  </>
                )}
              </a>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-3 py-1.5">
            {USE_MOCK && <Badge tone="gold">mock API</Badge>}
            {known.length > 0 && (
              <Indicator tone={onSurface > 0 ? "surface" : "live"}>
                {onSurface > 0 ? `${onSurface} on the surface` : "relay in view"}
              </Indicator>
            )}
            <MissionClock />
            <a href={STORY_URL} className="btn-outline inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-semibold">
              <span aria-hidden="true">←</span> Back to story
            </a>
            {(tab === "memory" || tab === "conflicts") && (
              <div className="flex overflow-hidden rounded-md border border-line" role="group" aria-label="Device">
                {ids.map((d) => (
                  <button key={d} type="button" onClick={() => setDevice(d)} aria-pressed={device === d}
                    className={`min-h-11 px-3 py-1 text-sm ${device === d ? "btn-primary !rounded-none font-semibold" : "text-muted hover:text-ink"}`}>
                    Device {d}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-5">
        {tab === "companion" && <Companion device={device} setDevice={setDevice} devices={ids} />}
        {tab === "control" && <ControlCenter devices={ids} />}
        {tab === "devices" && <DevicesSync />}
        {tab === "memory" && <MemorySearch device={device} />}
        {tab === "conflicts" && <ConflictsDecisions device={device} />}
        {tab === "prove" && <ProveIt />}
      </main>
      <footer className="mt-10">
        <div className="mx-auto grid max-w-7xl gap-x-6 gap-y-1 px-4 pb-4 text-xs text-muted sm:grid-cols-5">
          <p><span className="text-ink">Krypta</span> seals what's private</p>
          <p><span className="text-ink">Hermes</span> carries the manifest on each relay pass</p>
          <p><span className="text-ink">Agora</span> shares what the colony knows</p>
          <p><span className="text-ink">Themis</span> decides what's true</p>
          <p><span className="text-ink">Argus</span> scans where each note belongs</p>
        </div>
        <Horizon height={48} />
      </footer>
    </div>
  );
}
