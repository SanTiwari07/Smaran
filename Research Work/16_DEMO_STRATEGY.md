# 16 — Demo Strategy

← [15 Judging](15_JUDGING_STRATEGY.md) · [Master index](00_MASTER_RESEARCH_INDEX.md) · Next: [17 Pitch](17_PITCH_AND_PRESENTATION_STRATEGY.md)

Builds on the existing presenter script `docs/DEMO.md` (4 beats, per-beat resets, 10/10 rehearsals). Two versions: **5:00** (likely online-round slot, based on CC5's "5-min pitch + 2-min Q&A") and **~7:00** (final, if a longer slot is given).

## 5-minute flow (online round / short final slot)

| Time | Segment | What's on screen | Script (condensed) |
|---|---|---|---|
| 0:00–0:20 | **Problem** | Photo/illustration: a technician by a CNC machine, Wi-Fi ✗ | "On a factory floor, the Wi-Fi drops, and two technicians report opposite things about the same machine. Today one of those reports silently disappears." |
| 0:20–0:40 | **Existing pain** | A 3-row table: cloud RAG (fails offline) · local store (no fleet) · Qdrant reference sync (timestamp: one report lost) | "Even Qdrant's reference sync keeps the latest timestamp. Clocks drift, and concurrent edits vanish." |
| 0:40–1:05 | **Solution** | The architecture diagram (3 shards, gateway, Qdrant Server) | "Smaran is a memory layer on Qdrant Edge. It keeps private data on the device by construction, syncs the rest to Qdrant Server, and never guesses when devices disagree." |
| 1:05–3:35 | **Live demo** (4 beats, ~35 s each) | Dashboard, full screen | **B1** offline note + search (ms latency) → **B2** phone number → Krypta, audit 0/0 → **B3** both offline, conflicting notes; the safety note jumps the queue; reconnect → CONFLICT + naive-merge box → **B4** supervisor keeps B → superseded + Chronos slider |
| 3:35–4:05 | **Architecture / Qdrant usage** | The "Qdrant calls" slide | "EdgeShard with named dense + BM25 vectors, device-wide IDF, RRF, filters, scheduled optimize(), dual-write to Qdrant Server (+ partial snapshots)." |
| 4:05–4:30 | **Impact (measured)** | Results table | "3.9 ms offline. 50/50 conflicts vs 13/50 naive. 1000/1000 convergence. 0 private records on the server. X% bandwidth saved." |
| 4:30–4:50 | **Future / scale** | Deployment topology | "Per-device shards, one plant server; next: signed ops, multimodal notes, CMMS integration." |
| 4:50–5:00 | **Closing line** | Logo + tagline | "**Qdrant Edge gave devices a memory. Smaran makes that memory trustworthy offline.**" |

## Final-round extended beats (+2 min if available)

- **Kill-and-replay** (30 s): hard-kill device A mid-sync → restart → counters: acked N, replayed N, duplicates 0.
- **Qdrant Server tab** (20 s): the Qdrant Web UI with the collection, point count and a payload showing `status=contested`.
- **Partial snapshot** (20 s, if shipped): "mirror refreshed: 38 KB partial vs 2.1 MB full".
- **Retrieval scoreboard** (20 s, if shipped): hybrid vs dense vs BM25 hit@5.

## Live vs preloaded vs never-live

| Show live | Preload (reset state) | Do NOT demo live |
|---|---|---|
| Typing notes, search, link toggles, reconnect, conflict reveal, resolve, Chronos | Manuals in Agora; the fleet state for each beat (`demo.py reset bN`); models cached; Docker warm | Model downloads; `pip install`; training the classifier; 1000-run simulations (show results); anything on venue Wi-Fi; multi-laptop networking (unless rehearsed at the venue) |

## Pre-demo checklist (T-30 min)

1. Laptop on power; notifications off; display scaling checked on the projector.
2. `docker` running → `demo.py start-all` → `demo.py status` all green.
3. `demo.py rehearse --runs 3` → all PASS.
4. `demo.py reset b1`; browser full-screen at `localhost:5173`; a second tab on `localhost:6333/dashboard`.
5. Wi-Fi **off** (proves offline, removes the network variable).
6. The backup video on the desktop, plus a copy on a USB drive and in the cloud.
7. The terminal pre-typed with the reset commands (large font).

## Failure handling (a playbook per beat)

| Failure | Detect | Recovery (≤ 10 s) |
|---|---|---|
| A beat doesn't produce the expected state | `play` check fails / UI mismatch | `demo.py reset bN` (~5 s) and redo, narrating "fresh state per beat, by design" |
| Device card "unreachable" | Red card | `demo.py status` → `stop-all` + `start-all` (~30 s); talk over the architecture slide meanwhile |
| Docker/Qdrant Server fails | Gateway `timed out` in the logs | Switch to `start-all --qdrant embedded`; say so honestly; show the server beat from the video |
| Projector/laptop failure | — | Play the backup video from USB on the organizer's machine |
| Search returns an unexpected top result | Visible | Use the rehearsed query text exactly; keep the pre-written queries in a notes file |

## Backup data

- `seed/` data and per-beat reset snapshots (existing).
- The recorded video (Phase 1.7) with **server mode visible**.
- Screenshots of each beat's end state, placed in the deck as "hidden" backup slides.
