// Self-playing demo: open the dashboard with ?auto (or ?auto=loop). It tells one story in five
// proof moments, and every moment is a real call to the running devices and gateway (the same
// requests a person would type), so nothing on screen is an animation:
//
//   01 REMEMBER   teach it project context; it extracts structured memory, with the reason
//   02 THINK      ask why; it answers from the recorded decision and shows its provenance;
//                 a contradicting statement is held, not written over the old decision
//   03 ACT        cut the network; it creates a task locally and explains why
//   04 RECONCILE  two offline devices edit the same meeting; they reconnect; it explains the conflict
//   05 LEARN      the resolved truth becomes memory; a follow-up question depends on it
import { useEffect, useRef, useState } from "react";
import { companion, type ChatResult } from "../api/companion";

type Ctx = { say: (s: string) => void };
type Step = { say: string; tab?: string; device?: string; run?: (c: Ctx) => Promise<unknown>; hold?: number };
type Beat = { n: number; title: string; note: string; steps: Step[] };

export const selectDevice = (d: string) => window.dispatchEvent(new CustomEvent("smaran:device", { detail: d }));
const stageEvent = (detail: unknown) => window.dispatchEvent(new CustomEvent("smaran:stage", { detail }));

/** Send a message to a device through the real agent loop and hand the result to the Companion view. */
async function say(device: string, text: string): Promise<ChatResult> {
  selectDevice(device);
  const result = await companion.chat(device, text);
  window.dispatchEvent(new CustomEvent("smaran:turn", { detail: { device, text, result } }));
  return result;
}

const sync = async (...ds: string[]) => { for (const d of ds) await companion.syncNow(d).catch(() => null); };

async function reset() {
  await companion.resetGateway();
  for (const d of ["A", "B"]) { await companion.resetDevice(d); await companion.syncNow(d).catch(() => null); }
  await companion.seedBackground("A");         // older material, so the lifecycle has something to show
  await sync("A", "B", "A");
}

const TEACH = "I'm building Project Nova. I handle the backend, we're using FastAPI and PostgreSQL, and we chose PostgreSQL because we need relational transactions.";

const BEATS: Beat[] = [
  {
    n: 1, title: "REMEMBER", note: "Smaran turns what you say into structured memory: facts, decisions, and the reason behind them.",
    steps: [
      { say: "Resetting to a known state…", run: reset, hold: 500, tab: "companion" },
      { say: "Aarav teaches Smaran about his project. Nothing to fill in: it extracts the structure.", device: "A", run: () => say("A", TEACH), hold: 7000 },
      { say: "Two more facts: the meeting time, and what the mentor said.", run: async () => {
        await say("A", "The Project Nova review meeting is at 3 PM.");
        await say("A", "The mentor said 5 PM suits the whole team because everyone is free by then.");
        await sync("A", "B", "A");
      }, hold: 5000 },
    ],
  },
  {
    n: 2, title: "THINK", note: "Retrieval, then a reasoned answer from the recorded decision, with where it came from.",
    steps: [
      { say: "Later: why did we choose PostgreSQL? Answered from the recorded decision, with its provenance.", run: () => say("A", "Why did we choose PostgreSQL?"), hold: 9000 },
      { say: "Someone proposes MongoDB. Smaran does not silently replace the decision; it detects the contradiction.", run: () => say("A", "I think we should use MongoDB instead."), hold: 8000 },
      { say: "The answer is no. The old decision stands and nothing was overwritten.", run: () => say("A", "No, keep PostgreSQL"), hold: 5000 },
    ],
  },
  {
    n: 3, title: "ACT", note: "The network is off. Memory, planning and the action all run on the device.",
    steps: [
      { say: "Cutting the network on both devices. Everything from here runs locally.", run: async () => { await companion.setOnline("A", false); await companion.setOnline("B", false); }, hold: 2500 },
      { say: "An action, offline: it retrieves project context, runs the tool locally and can explain why.", run: () => say("A", "Create a task to finish the authentication API tonight."), hold: 11000 },
    ],
  },
  {
    n: 4, title: "RECONCILE", note: "Both devices edited the same meeting while they could not see each other.",
    steps: [
      { say: "The phone moves the meeting to 4 PM, offline.", run: () => say("A", "The Project Nova review meeting is now at 4 PM."), hold: 4000 },
      { say: "The laptop moves it to 5 PM, also offline.", device: "B", run: () => say("B", "The Project Nova review meeting is now at 5 PM."), hold: 4000 },
      { say: "Reconnecting. Version vectors show neither edit saw the other, so both are kept and flagged.", run: async () => {
        await companion.setOnline("A", true); await companion.setOnline("B", true);
        await sync("A", "B", "A", "B");
      }, hold: 3000 },
      { say: "Smaran explains the conflict and checks memory for evidence. It suggests; you decide.", device: "A", hold: 11000 },
      { say: "You accept the suggestion that memory supports.", run: async () => {
        const cf = (await companion.conflicts("A"))[0];
        if (cf) await companion.resolve(cf.entity_key, cf.suggestion.op_id);
        await sync("A", "B", "A", "B");
      }, hold: 3000 },
    ],
  },
  {
    n: 5, title: "LEARN", note: "The resolved truth is now memory, and the next question depends on it.",
    steps: [
      { say: "The laptop is asked about the meeting. The answer comes from the user-confirmed resolution.", device: "B", run: () => say("B", "When is the Project Nova review meeting?"), hold: 9000 },
      { say: "Another question that depends on what was just learned: the task from the phone, before that meeting.", device: "A", run: () => say("A", "What do I still need to do before the Project Nova review meeting?"), hold: 7000 },
      { say: "It also knows what to let go: old chat and closed tasks are archived, not deleted.", run: async (c) => {
        const lifecycle = await companion.lifecycle("A");
        stageEvent({ n: 5, id: "learn", title: "LEARN", note: "Smaran does not remember everything forever. It remembers what matters.", lifecycle });
        c.say("Done. Reload the page to play again.");
      }, hold: 9000 },
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
          stageEvent({ n: beat.n, id: beat.title.toLowerCase(), title: beat.title, note: beat.note });
          for (const s of beat.steps) {
            if (stop.current || cancelled) return;
            i += 1;
            const label = `0${beat.n} ${beat.title}`;
            setWhere({ beat: label, say: s.say, i, total });
            if (s.tab) window.location.hash = `#${s.tab}`;
            if (s.device) selectDevice(s.device);
            try { if (s.run) await s.run({ say: (t) => setWhere((w) => w && { ...w, say: t }) }); }
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
    <div role="status" aria-live="polite" className="sticky top-0 z-30 border-b border-line bg-[var(--basalt)] text-ink">
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
