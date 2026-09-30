# Demo script: the companion story (main demo)

One continuous story: *Smaran is an AI that remembers me, keeps working when the internet disappears, acts for me, and catches up intelligently when it returns.* Open **Control center** (`#control`). The **Judge walkthrough** card lists the steps below; each is one click. `python scripts/story.py` runs the same steps with pass/fail checks.

```bash
.venv/Scripts/python scripts/demo.py start-all --qdrant embedded    # or without --qdrant embedded if Docker is running
ollama serve                                                        # local model runtime (skip to show the rules fallback)
.venv/Scripts/python scripts/story.py --runs 3                      # dress rehearsal, every check PASS
```

| # | Say | Click | Proves |
|---|---|---|---|
| 1 | "Day 1: I tell Smaran about my project." | Reset and teach Smaran | Structured memory: decisions, roles, tasks |
| 2 | "Two weeks pass." | Load two weeks of history | 15 real utterances run through the agent; 2 kept private |
| 3 | "Day 3: which DB did we choose?" (no shared keywords) | Retrieve naturally | Semantic retrieval + rerank; badge shows *On-device AI* |
| 4 | "Day 5: I'm in a lecture, no signal." | Disconnect the internet | Both status strips flip to Offline, queue counter appears |
| 5-6 | "What are my remaining tasks? When is the review?" | Keep using Smaran / Ask something | Local memory + local model, zero network |
| 7 | "Remind me tomorrow evening to finish the API integration." | Ask the agent to act | Plan, validated tool, verified, audited; queue +1 |
| 8-9 | "Meanwhile my laptop, also offline, disagrees about the meeting time." | Two devices edit the same fact | Phone says 4 PM, Laptop says 5 PM |
| 10 | "Wi-Fi is back." | Reconnect | N queued, N uploaded, conflicts detected, nothing overwritten |
| 11 | "Smaran won't pick for me." | Conflict card | Both versions, why, a suggestion, you decide |
| 12 | "What never left the phone?" | Show: Privacy | Krypta count, cloud audit 0 private |
| 13 | "Why not just ChatGPT?" | Show: AI routing, Audit log, Edge benchmark | Route, model, latency, top-k, tools, measured numbers |

Optional: **Take local model away** to show rules-from-memory still answering; the badge changes to *Rules from local memory*.

If asked "is this a real device?": two local processes and a software link switch; see *Real versus simulated* in [ARCHITECTURE.md](ARCHITECTURE.md).

---

# Fleet demo script (engine beats, original domain)

Run with `SMARAN_DOMAIN=fleet SEED_DIR=seed/manuals`.


Four live beats plus an optional fifth (the crash), each starting from its own reset so one failure can't cascade into the next. Everything runs on one laptop. "Offline" is a software switch on the dashboard, so no venue Wi-Fi is needed.

## Before you present

```bash
.venv/Scripts/python scripts/demo.py start-all          # add --qdrant embedded if Docker isn't running
.venv/Scripts/python scripts/demo.py rehearse --runs 3  # every check should PASS
.venv/Scripts/python scripts/demo.py reset b1
```

Open http://localhost:5173 in a full-screen browser window, and http://localhost:6333/dashboard (the Qdrant Server web UI) in a second tab. Keep a terminal ready for the resets.

**Opening line:** *"Other teams show that a device can remember. We show that its memory stays correct and private when devices go offline and disagree."*

## Beat 1: offline memory (`reset b1`)

1. **Devices & sync**: point out that device A is **offline** (red badge).
2. **Memory & search** → device A. Machine `CNC-07`, type *Fix*, text: `CNC-07 bearing replaced, vibration normal` → **Remember**.
3. The note lands in **Hermes** (waiting to sync). Say: *"Argus decided it's shareable machine knowledge."*
4. Search `CNC-07 bearing trouble`: the new note is #1, **answered locally**, a few ms. The manual entries come from **Agora**.

> Proves: searchable semantic memory on device; low-latency hybrid search without network.

## Beat 2: privacy (`reset b2`)

1. **Memory & search** → device A: `Call Ravi on 9876543210 about the night shift swap` → **Remember**.
2. It lands in **Krypta**: *"PII rule matched: phone_in"*. No model can override that rule.
3. **Devices & sync** → Gateway card: **Privacy audit passed · 0 private records · 0 PII matches**. The audit scans the real Qdrant Server collection.

> Proves: deciding dynamically what stays local, with privacy enforced by structure.

## Beat 3: conflict (`reset b3`: both devices offline)

1. Device A, *Status update*, `CNC-07`: `CNC-07 running normally after bearing replacement`.
2. Device B, *Status update*, `CNC-07`: `CNC-07 still vibrating at high RPM, do not run above 8000 rpm`.
3. Device B, *Observation*, `PRESS-02`: `PRESS-02 smoke from the motor, pressed e-stop`.
4. **Devices & sync**: B's outbox lists the **safety-critical** smoke note first.
5. Flip both devices **online**. Watch the activity feed: synced → pulled → **CONFLICT**.
6. **Conflicts & decisions**: CNC-07 is **contested**, both reports side by side with their version vectors. Point at the "naive merge" box: *"Qdrant's reference pattern keeps the latest timestamp, so one technician's report would silently disappear."*
7. Optional: switch to the Qdrant web UI tab, open collection `smaran`, and show both CNC-07 points with `status: contested` on the server.

> Proves: sync when connectivity returns; handling conflicting information.

## Beat 4: belief over time (`reset b4`: conflict already there)

1. **Conflicts & decisions**: the supervisor clicks **Keep this** on device B's report.
2. **Memory & search** → device A: the table shows `SUP-…` **current**, both offline reports **superseded** (struck through, with arrows).
3. Drag the **Chronos** slider left: before the resolution, device A saw CNC-07 as **contested**; after it, one belief.

> Proves: evolving memory with history, not overwrites.

## Beat 5 (optional): pull the plug (`reset b5`: device A offline)

Run it from the terminal so the crash lands at the exact worst moment:

```bash
.venv/Scripts/python scripts/demo.py play b5
```

1. Device A writes three notes offline; they sit in its outbox.
2. A pushes them, the gateway stores them, and A is killed **before it records the acks**.
3. `demo.py` restarts A. The **Devices & sync** card shows **Resent after restart 3**, then **Duplicates ignored 3** on the gateway, and the gateway table shows 3 ops stored once.
4. Say: *"The outbox is SQLite, written before anything else. The gateway recognises every resend by its op id. A crash costs a resend, never a lost or duplicated memory."*

> Proves: intermittent connectivity in its harshest form; idempotent sync.

## If something breaks

- Re-run the beat's reset (`scripts/demo.py reset bN`, ~5 s) and go again.
- A device card shows "unreachable": `scripts/demo.py status`, then `stop-all` and `start-all`.
- Worst case: switch to the recorded video.

## Numbers to quote

The metrics are in [BENCHMARKS.md](BENCHMARKS.md), regenerated by `python -m bench.bench`. Quote them with their denominators ("50 of 50 scripted cases", "40 golden queries").
