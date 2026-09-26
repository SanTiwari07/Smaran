# 10 — WOW Features

← [09 Differentiation](09_DIFFERENTIATION_STRATEGY.md) · [Master index](00_MASTER_RESEARCH_INDEX.md) · Next: [11 What not to build](11_WHAT_NOT_TO_BUILD.md)

Scale: Difficulty is L / M / H for a 4-person team with about 4 days to the 30 Sep freeze, plus 10 days to the 11 Oct final. "Built?" is checked against the repo as of 26 Sep 2026.

| # | Feature | Built? | Class |
|---|---|---|---|
| W1 | Conflict reveal: side-by-side reports + "naive merge would have lost this" | ✓ | **MUST HAVE** |
| W2 | Live Qdrant Server proof: points appear on the real server; the privacy audit runs against it | ◐ code done, not run | **MUST HAVE** |
| W3 | Pull-the-plug durability: kill a device mid-sync, restart, replay, 0 duplicates | ◐ tests only | **HIGH VALUE** |
| W4 | Partial-snapshot mirror: "pulled 38 KB instead of 2.1 MB" | ✗ | **HIGH VALUE** |
| W5 | Chronos time slider: what did device A believe at 10:02? | ✓ | **HIGH VALUE** (already there) |
| W6 | "Why here?" explainer on every memory (rule/classifier, confidence, shard) | ◐ | **HIGH VALUE** |
| W7 | Retrieval scoreboard: hybrid vs dense vs BM25 on a golden set, live | ✗ | **HIGH VALUE** |
| W8 | Second physical device (phone/Raspberry Pi/second laptop) as device B | ✗ | NICE TO HAVE |
| W9 | Voice note capture (on-device ASR) | ✗ | NICE TO HAVE (post-final) |
| W10 | Local LLM "ask the machine" chat | cut | **AVOID** |
| W11 | P2P mesh / Ed25519 signing | ✗ | **AVOID** (for now) |

---

### W1. Conflict reveal: MUST HAVE (built)

- **What:** two offline devices write contradicting status reports on CNC-07. On reconnect, the dashboard shows a **CONFLICT** with both versions, their version vectors, and a box showing what a timestamp merge would have kept.
- **Why it matters:** it is PS3's "conflicting information" requirement, and it is the thing no rival does correctly.
- **Implementation:** Themis `resolve(versions)`; gateway change feed; `ConflictsDecisions.tsx`.
- **Demo impact:** very high. It is the "aha" moment. **Real-world impact:** it prevents a safety-relevant report from disappearing.
- **Hackathon feasibility:** done. Polish the animation/emphasis only.

### W2. Live Qdrant Server proof: MUST HAVE (not yet run)

- **What:** start `qdrant/qdrant` in Docker. On reconnect, show the server's points count (Qdrant Web UI at `:6333/dashboard`) rising, and run the privacy audit *against the server*.
- **Why:** PS3 names "Qdrant Server". The top rival admits its server round trip is untested.
- **Implementation:** `scripts/demo.py start-all` (server mode) already exists. Get Docker Desktop working on the demo laptop, run `rehearse --runs 10`, and fix the version-warning noise (pin the image to match the client).
- **Difficulty:** L–M (environment work). **Risk:** Docker on Windows at the venue. Keep embedded mode as the fallback and pre-record the server beat.

### W3. Pull-the-plug durability: HIGH VALUE

- **What:** a dashboard button (or a terminal command) that hard-kills device A's process while its outbox is draining. Restart it: the outbox replays, the gateway dedups by idempotency key, and the counts match.
- **Why:** PS3 "intermittent connectivity" in its harshest form. AegisEdge uses this as its headline, so parity is needed, and a better *explanation* wins.
- **Implementation:** a `demo.py kill a` + `demo.py start a` helper already fits the design (tests `test_crash_recovery_replays_outbox`, `test_sync_is_idempotent` exist). Add an "acked / replayed / duplicates" counter to the Devices view.
- **Difficulty:** L–M. **Demo risk:** low if scripted with reset.

### W4. Partial-snapshot mirror: HIGH VALUE

- **What:** replace the scroll-based Agora refresh with Qdrant Edge's official mechanism: `manifest = agora.snapshot_manifest()` → `POST /collections/{c}/shards/0/snapshot/partial/create` with the manifest → `agora.update_from_snapshot(path)`. Show the bytes transferred vs a full snapshot.
- **Why:** this is exactly the Qdrant-documented pattern (the immutable mirror shard). It proves "Qdrant Usage" at a level no rival reaches, and it cuts pull bandwidth.
- **Implementation risks:** beta API; Windows file locking; the collection's shard layout must match (a single shard, `shard_number=1`); the snapshot restore replaces Agora's config. Keep the scroll path as a fallback behind a flag.
- **Difficulty:** M. **Feasibility:** a day-long spike. Only ship if it passes 10 rehearsals.

### W5. Chronos time slider: HIGH VALUE (built)

- **What:** drag time back and see device A's belief before and after the supervisor's decision.
- **Why:** "evolving local memory" made visible. Superseded, never deleted.
- **Status:** done. Make sure it is in the video.

### W6. "Why here?" explainer: HIGH VALUE

- **What:** each memory row shows `Krypta · PII rule phone_in` or `Hermes · classifier 0.94 sync · critical`.
- **Why:** turns "dynamically decide" from a claim into something visible. It also builds judge trust.
- **Difficulty:** L (the data exists in the router output).

### W7. Retrieval scoreboard: HIGH VALUE

- **What:** 30–50 golden queries (paraphrases, part numbers, typos). Report hit@1, hit@5 and MRR for dense-only, BM25-only and hybrid (RRF). Show a small table in the UI and in BENCHMARKS.md.
- **Why:** Qdrant spotlighted "similarity ≠ relevance; measure hit rate" [Q-recap]. It justifies *why* hybrid search. Nobody else has it.
- **Difficulty:** L–M (bench script + labelled queries). **Risk:** numbers may be unflattering, which is fine if reported honestly.

### W8. Second physical device: NICE TO HAVE

- **What:** device B runs on a second laptop or a Raspberry Pi (a community armv7l port of Qdrant Edge exists), linked over a phone hotspot that you can physically switch off.
- **Why:** a physical "offline" gesture is memorable. **Risk:** venue networking, ARM wheels for `qdrant-edge-py` (unverified on aarch64 Windows/Linux in our setup), setup time. Only if W1–W7 are rock solid.

### W9. Voice notes (on-device ASR): NICE TO HAVE, post-final

- Technicians wear gloves, so voice capture is realistic. Do it with an on-device model (e.g. whisper.cpp) or not at all. Cloud voice (Omnidimension) contradicts offline-first.

### W10. Local LLM chat: AVOID

- Adds latency and a failure point. Qdrant explicitly rewards non-chatbot work [Q6]. The proposal already cut it.

### W11. P2P mesh / signing: AVOID for now

- A different problem (device↔device with no cloud); the rival already owns it. List signing as future scope in the security section.
