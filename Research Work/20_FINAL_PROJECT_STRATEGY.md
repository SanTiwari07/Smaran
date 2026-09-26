# 20 — FINAL PROJECT STRATEGY

← [19 Risks](19_RISK_ANALYSIS.md) · [Master index](00_MASTER_RESEARCH_INDEX.md) · Sources: [21](21_SOURCE_DATABASE.md)

**Bottom line (RECOMMENDATION):** **Don't pivot.** Smaran already targets the exact white space that the research found: Qdrant's reference sync, competing products and rival teams all leave governance, conflict semantics and durability open. The job for the next four days is to **close four gaps**, and for the next fourteen to **rehearse the story**:

1. Run it against the real Qdrant Server.
2. Make the GitHub repo sell it in 30 seconds.
3. Fix the one missed metric (bandwidth).
4. Measure retrieval quality.

Then add partial snapshots and a live crash-recovery beat for the final.

---

### 1. What exactly should we build?

**Smaran**: an offline-first memory layer on **Qdrant Edge** for edge-AI devices. The demo use case is a **maintenance copilot for factory technicians**. It:
- stores and hybrid-searches memories on the device in three Edge Shards (Krypta: private; Hermes: syncing; Agora: fleet mirror),
- decides per memory what stays private, what syncs and what is dropped, with a visible reason,
- syncs through a crash-safe outbox and an idempotent gateway to **Qdrant Server**,
- detects conflicting facts with version vectors, lets a supervisor resolve them, and keeps history.

This is already built ([12](12_TECHNICAL_ARCHITECTURE.md)). Finish, prove and present it.

### 2. Why should we build it?

- It answers **every PS3 bullet** (traceability R1–R10 in [02](02_PROBLEM_STATEMENT_3_ANALYSIS.md)), including the three that most teams skip: dynamic decisions, conflicting information, and "rather than simply running a local vector database".
- The PS3 owner (Qdrant) has already demoed "device remembers and searches offline" itself ([04](04_PS3_ORGANIZATION_RESEARCH.md)). Value has to come from what its reference pattern leaves open.
- Qdrant's judging history rewards **deep Qdrant usage, technical depth and non-chatbot** projects, including a robot-memory-with-safety entry (RoboBank, 2nd place 2025) ([07](07_PREVIOUS_WINNERS_ANALYSIS.md)).

### 3. What problem are we solving?

**Silent data loss and privacy leaks when edge devices go offline and disagree.** Today's defaults (timestamp/last-writer-wins, sync-everything, in-memory queues) drop a technician's report without anyone noticing, push personal data to the cloud, and lose work on a crash ([02](02_PROBLEM_STATEMENT_3_ANALYSIS.md) §3).

### 4. Who is the user?

- **Primary:** the shop-floor maintenance technician (tablet or handheld, poor Wi-Fi).
- **Secondary:** the shift supervisor, who resolves conflicts and sees safety-critical items first.
- **Admin / buyer:** plant IT/OT and operations. Generalises to robots, kiosks and vehicles.

### 5. Why are existing solutions insufficient?

| Existing | Insufficient because |
|---|---|
| Cloud RAG | Fails offline; ~50 ms+ per round trip; raw data leaves the device |
| Local vector stores (sqlite-vec, Chroma …) | No fleet knowledge, no sync; PS3 explicitly says "rather than simply running a local vector database" |
| Qdrant's reference two-shard sync | Syncs everything; the sample queue is in-memory; timestamp dedup (clock skew, concurrent edits lost) |
| Couchbase Lite / Ditto / PowerSync / (Realm, EOL) | Document-level defaults (most-revisions / LWW / deletes win); vector search is missing or secondary |
| Rival PS3 entries | Timestamp conflicts; static residency rules; `qdrant-client` instead of Qdrant Edge; server untested |

Detail: [06](06_COMPETITOR_ANALYSIS.md).

### 6. What makes our approach different?

1. **Correct under conflict:** version vectors separate *newer* from *concurrent*. Concurrent facts are **flagged, never guessed**; history is **superseded, not deleted** (Chronos).
2. **Private by structure:** Krypta has no sync code path; PII rules run before any model; the server audit shows 0.
3. **Measured judgment:** the residency classifier is reported with held-out accuracy and caveats.
4. **Real Qdrant Edge, used idiomatically:** EdgeShard, the built-in BM25, device-wide IDF, RRF, filters, scheduled `optimize()` (+ partial snapshots).
5. **Every claim is reproducible:** benchmarks, 30 tests, 1000-run convergence simulation, 10/10 rehearsals.

### 7. What technology should we use?

Keep the current stack ([13](13_TECH_STACK_RECOMMENDATION.md)): Qdrant Edge (`qdrant-edge-py` 0.8.0, pinned) · Qdrant Server (Docker) · FastEmbed bge-small + Edge BM25 · scikit-learn classifier + PII rules · SQLite WAL outbox · FastAPI device/gateway · React/Vite dashboard · pytest/Hypothesis + bench. **Add:** GitHub Actions CI; float16 vector transport. **Reject:** local LLM, Pathway, n8n/Cloudinary/Omnidimension in the live path, mobile rewrite, P2P mesh.

### 8. What should the MVP contain?

Already built: offline hybrid search; Argus decisions; outbox + idempotent sync; Themis + resolve + Chronos; 3-view dashboard; demo tooling.
**Must be added before the 30 Sep freeze:** a real Qdrant Server run (10/10 rehearsals); the backup video; README hero GIF + CI badge + credits. See [14](14_MVP_ROADMAP.md) Phase 1.

### 9. What should the WOW feature be?

**The conflict reveal:** two offline devices write opposite reports; on reconnect, the dashboard shows both side by side with version vectors, next to a "naive merge would have kept only this" box, and the supervisor's decision rewrites the belief timeline (Chronos).
Second WOW for the final: **pull the plug**. Kill a device mid-sync; it restarts and replays with 0 duplicates.
Third, if shipped: the **partial-snapshot mirror** with a bytes-saved counter. See [10](10_WOW_FEATURES.md).

### 10. What should we avoid?

Chatbots and local LLMs; re-creating Qdrant's own glasses/robot demos; timestamp conflicts; LLM-as-judge for truth; cloud sponsor APIs in the live path; mobile rewrites; P2P mesh; unmeasured claims ("any device", "guaranteed"). See [11](11_WHAT_NOT_TO_BUILD.md).

### 11. How should we demonstrate it?

Four live beats on one laptop, Wi-Fi physically off, Qdrant Server in Docker, each beat with its own reset:
(1) offline memory + ms search → (2) phone number → Krypta + audit 0/0 → (3) both offline, conflicting reports, the safety-critical note first, reconnect → CONFLICT → (4) supervisor resolves → superseded + Chronos.
For the final, add the kill-and-replay beat and the Qdrant Web UI tab. The backup video is always ready. See [16](16_DEMO_STRATEGY.md).

### 12. How should we pitch it?

A 10-slide deck, 5:00 exactly: the moment (technician, Wi-Fi off, opposite reports) → why defaults fail (including Qdrant's timestamp pattern) → Smaran in one picture → live demo → Themis in one picture → Qdrant calls → measured results → PS3 checklist → roadmap → close with **"Qdrant Edge gave devices a memory. Smaran makes that memory trustworthy offline."** See [17](17_PITCH_AND_PRESENTATION_STRATEGY.md) and [18](18_JUDGE_PERSPECTIVE.md).

### 13. What measurable impact can we demonstrate?

| Metric | Now | After planned work |
|---|---|---|
| Offline hybrid search | 3.9 ms p50 / 5.6 ms p95 (2,000 memories) | same, shown live |
| Conflict correctness | 50/50 vs naive LWW 13/50 | same |
| Multi-device convergence | 1000/1000 runs, 0 concurrent edits lost | same |
| Privacy | 0 private records / 0 PII matches on the server | same, **on the real Qdrant Server** |
| Residency classifier | 98.3% acc, 0.9 safety recall (60 held-out) | + Cohen's kappa |
| Bandwidth saved vs sync-all | 38.2% (missed 40%) | ≥ 40% target; likely ~60%+ with float16 (**to be measured**) |
| Retrieval quality | not measured | hit@1 / hit@5 / MRR, hybrid vs dense vs BM25 |
| Crash durability | 0 lost (tests) | shown live |
| Demo reliability | 10/10 rehearsals (embedded) | 10/10 in server mode |

Business translation: fewer repeat faults (recall of past fixes in ms), no lost safety reports, less uplink data, DPDP-aligned minimisation.

### 14. What are our biggest risks?

1. **The Qdrant Server path never exercised** (high probability, high impact). Fix first.
2. **Elimination on profile** (GitHub/LinkedIn). Polish the README, CI, per-member commits and posts.
3. **Docker at the venue.** Embedded fallback + video.
4. **Date ambiguity (30 Sep vs 3 Oct).** Freeze on 30 Sep; email the organizers.
5. **A strong rival (AegisEdge)** on durability and security. Counter with Qdrant Edge compliance, story clarity and the live kill beat.

Full matrix: [19](19_RISK_ANALYSIS.md).

### 15. What should we build first?

In order, starting **today (Sat 26 Sep)**:
1. Qdrant Server in Docker → `rehearse --runs 10` in server mode.
2. GitHub Actions CI + badge.
3. README hero GIF + architecture image + credits + "Prove it in 60 s".
4. float16 vector transport → re-run the bandwidth benchmark.
5. Golden-query retrieval eval → BENCHMARKS.md.
6. Record the backup video (server mode).
7. LinkedIn posts from all four members with the GIF and repo link.

### 16. What should we build if we have extra time?

Kill-and-replay UI counters; "Why here?" badges; Cohen's kappa; then, for the final: partial-snapshot mirror refresh (behind a flag); formula/MMR ranking; a self-playing demo mode; a "Prove it" panel; a second physical device. See [14](14_MVP_ROADMAP.md) Phases 2–3.

### 17. What would make the project look production-ready?

- Green CI; pinned versions; one-command start; per-service logs; a status command (mostly done).
- A real Qdrant Server deployment; documented collection schema and payload indexes.
- A crash-safe outbox with idempotent ingest (done), shown live.
- A security roadmap written down (signing, mTLS, OIDC, encryption at rest) with a threat table.
- An honest "Limits" section (small labelled set, 5-device measured scale, no signing yet).
- An ops story: `optimize()` scheduling, retention/compaction plan, upgrade path for the beta Edge API.
- A deployment topology for a pilot plant.

---

## One-page action checklist

- [ ] Email team.geekroom@gmail.com: confirm the submission deliverables and the "3 Oct online" step
- [ ] Qdrant Server (Docker) run + 10/10 rehearsals
- [ ] CI badge
- [ ] README: hero GIF, architecture image, Prove-it block, credits, team LinkedIn links
- [ ] float16 transport + new bandwidth number
- [ ] Retrieval eval (hybrid vs dense vs BM25)
- [ ] Backup video (server mode)
- [ ] LinkedIn posts ×4
- [ ] 5:00 pitch rehearsed ×5 with a timer; Q&A bank drilled ([18](18_JUDGE_PERSPECTIVE.md))
- [ ] Final: travel to Paytm Noida on 11 Oct; demo laptop + charger + USB video
