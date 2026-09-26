import { Database, LayoutGrid, Scale } from "lucide-react";
import { useEffect, useState } from "react";
import { api, DEVICES, USE_MOCK } from "./api/client";
import { Badge } from "./components/ui";
import { usePoll } from "./hooks/usePoll";
import ConflictsDecisions from "./views/ConflictsDecisions";
import DevicesSync from "./views/DevicesSync";
import MemorySearch from "./views/MemorySearch";

const TABS = [
  { id: "devices", label: "Devices & sync", icon: LayoutGrid },
  { id: "memory", label: "Memory & search", icon: Database },
  { id: "conflicts", label: "Conflicts & decisions", icon: Scale },
] as const;
type Tab = (typeof TABS)[number]["id"];

function readTab(): Tab {
  const h = window.location.hash.slice(1);
  return (TABS.some((t) => t.id === h) ? h : "devices") as Tab;
}

export default function App() {
  const [tab, setTab] = useState<Tab>(readTab);
  const [device, setDevice] = useState("A");
  const contested = usePoll(() => api.gwContested().then((g) => g.length), [], 2000);

  useEffect(() => {
    const onHash = () => setTab(readTab());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  return (
    <div className="min-h-screen">
      <header className="border-b border-stone-200 bg-white dark:border-stone-800 dark:bg-stone-900">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
          <div className="flex items-baseline gap-3">
            <span className="font-serif text-2xl tracking-[0.2em] text-ink dark:text-laurel-soft">
              <span className="text-laurel">Σ</span>MARAN
            </span>
            <span className="hidden font-serif text-sm italic text-stone-500 sm:inline">aletheia at the edge</span>
          </div>
          <nav className="flex flex-wrap gap-1" aria-label="Views">
            {TABS.map((t) => (
              <a key={t.id} href={`#${t.id}`} onClick={() => setTab(t.id)}
                className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium ${tab === t.id ? "bg-indigo-50 text-ink dark:bg-indigo-950 dark:text-indigo-200" : "text-stone-600 hover:bg-stone-100 dark:text-stone-300 dark:hover:bg-stone-800"}`}>
                <t.icon size={15} />{t.label}
                {t.id === "conflicts" && (contested.data ?? 0) > 0 && <Badge tone="red">{contested.data}</Badge>}
              </a>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-2">
            {USE_MOCK && <Badge tone="gold">mock API</Badge>}
            {tab !== "devices" && (
              <div className="flex rounded-lg border border-stone-200 p-0.5 dark:border-stone-700" role="group" aria-label="Device">
                {Object.keys(DEVICES).map((d) => (
                  <button key={d} type="button" onClick={() => setDevice(d)}
                    className={`rounded-md px-3 py-1 text-sm font-medium ${device === d ? "bg-ink text-white dark:bg-indigo-500 dark:text-stone-950" : "text-stone-600 dark:text-stone-300"}`}>
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
      <footer className="mx-auto max-w-7xl px-4 pb-6 text-xs text-stone-400">
        Krypta keeps what's private · Hermes carries the rest when the link returns · Agora shares what the fleet knows · Themis decides what's true
      </footer>
    </div>
  );
}
