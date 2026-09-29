// Self-playing demo: open the dashboard with ?auto (or ?auto=loop) and it plays beats 1-4
// through the real APIs, with a caption for each step. Same steps and texts as
// scripts/demo.py, so a recording made this way matches the live demo.
import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import type { Kind } from "../api/types";

type Step = { say: string; tab?: "devices" | "memory" | "conflicts"; device?: string; run?: () => Promise<unknown>; hold?: number };
type Beat = { title: string; steps: Step[] };

const note = (d: string, text: string, kind: Kind, machine: string | null) =>
  api.addNote(d, { text, kind, machine, author: `tech-${d}` });

/** Mirrors `demo.py reset`: fresh gateway with the fleet seed, both devices synced, then some links cut. */
async function resetAll(offline: string[]) {
  await api.gwReset();
  for (const d of ["A", "B"]) {
    await api.devReset(d);
    await api.syncNow(d);
  }
  for (const d of offline) await api.setOnline(d, false);
}

export const selectDevice = (d: string) => window.dispatchEvent(new CustomEvent("smaran:device", { detail: d }));
export const runSearch = (q: string) => window.dispatchEvent(new CustomEvent("smaran:search", { detail: q }));

const BEATS: Beat[] = [
  {
    title: "Beat 1 · Offline memory",
    steps: [
      { say: "Resetting to a known state…", run: () => resetAll(["A"]), hold: 500 },
      { say: "Device A has lost its link. Everything from here runs on the device.", tab: "devices" },
      { say: "A technician logs a fix on CNC-07. Argus decides where it lives.", tab: "memory", device: "A",
        run: () => note("A", "CNC-07 bearing replaced, vibration normal", "fix", "CNC-07") },
      { say: "Hybrid search, dense + BM25 fused with RRF, answered on the device in milliseconds.",
        run: async () => runSearch("CNC-07 bearing trouble"), hold: 6000 },
    ],
  },
  {
    title: "Beat 2 · Privacy",
    steps: [
      { say: "A note with a phone number. PII rules run before any model, and no model can override them.",
        run: () => note("A", "Call Ravi on 9876543210 about the night shift swap", "observation", null) },
      { say: "It lives in Krypta, which has no sync path. The link comes back, and the Qdrant Server audit still finds 0 private records.",
        tab: "devices", run: async () => { await api.setOnline("A", true); await api.syncNow("A"); }, hold: 6000 },
    ],
  },
  {
    title: "Beat 3 · Conflict",
    steps: [
      { say: "Both devices offline. Two technicians are about to disagree about CNC-07.", run: () => resetAll(["A", "B"]), tab: "devices" },
      { say: "Device A: running normally.", tab: "memory", device: "A",
        run: () => note("A", "CNC-07 running normally after bearing replacement, vibration normal", "status", "CNC-07") },
      { say: "Device B: still vibrating. And a safety-critical smoke report.", device: "B",
        run: async () => {
          await note("B", "CNC-07 still vibrating at high RPM, do not run above 8000 rpm", "status", "CNC-07");
          await note("B", "PRESS-02 smoke from the motor, pressed e-stop", "observation", "PRESS-02");
        } },
      { say: "The safety-critical note is first in B's outbox.", tab: "devices" },
      { say: "Links restored. Themis compares version vectors: neither report saw the other, so both are contested.",
        run: async () => {
          await api.setOnline("A", true); await api.setOnline("B", true);
          await api.syncNow("A"); await api.syncNow("B"); await api.syncNow("A");
        } },
      { say: "Both reports side by side. A latest-timestamp merge would have silently dropped one.", tab: "conflicts", hold: 9000 },
    ],
  },
  {
    title: "Beat 4 · Belief over time",
    steps: [
      { say: "The shift supervisor keeps device B's report.",
        run: async () => {
          const g = (await api.gwContested())[0];
          const keep = g?.versions.find((v) => v.device_id === "B");
          if (g && keep) await api.gwResolve(g.entity_key, keep.op_id);
          await api.syncNow("A"); await api.syncNow("B");
        } },
      { say: "The offline reports are superseded, not deleted. Drag Chronos back to see what device A believed before.",
        tab: "memory", device: "A", hold: 9000 },
    ],
  },
];

const STEP_MS = 4500;
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export function autoMode(): "off" | "once" | "loop" {
  const v = new URLSearchParams(window.location.search).get("auto");
  if (v === null) return "off";
  return v === "loop" ? "loop" : "once";
}

export default function AutoPlay({ mode }: { mode: "once" | "loop" }) {
  const [where, setWhere] = useState<{ beat: string; say: string; i: number; total: number } | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [stopped, setStopped] = useState(false);
  const stop = useRef(false);

  useEffect(() => {
    let cancelled = false;
    const total = BEATS.reduce((a, b) => a + b.steps.length, 0);
    (async () => {
      await sleep(300);          // StrictMode mounts effects twice in dev: let the first one cancel
      if (cancelled) return;
      do {
        let i = 0;
        for (const beat of BEATS) {
          for (const s of beat.steps) {
            if (stop.current || cancelled) return;
            i += 1;
            setWhere({ beat: beat.title, say: s.say, i, total });
            if (s.tab) window.location.hash = `#${s.tab}`;
            if (s.device) selectDevice(s.device);
            try { if (s.run) await s.run(); }
            catch (e) { setErr(e instanceof Error ? e.message : String(e)); return; }
            await sleep(s.hold ?? STEP_MS);
          }
        }
      } while (mode === "loop" && !stop.current && !cancelled);
      if (!cancelled) setWhere((w) => w && { ...w, say: "Done. Reload the page to play again.", i: w.total });
    })();
    return () => { cancelled = true; };
  }, [mode]);

  if (stopped) return null;
  return (
    <div role="status" aria-live="polite" className="sticky top-0 z-10 border-b border-line bg-[#161e33] text-ink">
      <div className="mx-auto flex max-w-7xl items-center gap-4 px-4 py-2">
        <span className="label shrink-0 text-muted">{where?.beat ?? "Auto demo"}</span>
        <span className="min-w-0 flex-1 text-sm">{err ? `Stopped: ${err}` : where?.say ?? "Starting…"}</span>
        {where && <span className="num shrink-0 font-mono text-xs text-muted">{where.i}/{where.total}</span>}
        <button type="button" onClick={() => { stop.current = true; setStopped(true); }}
          className="shrink-0 text-xs underline underline-offset-4">Stop</button>
      </div>
    </div>
  );
}
