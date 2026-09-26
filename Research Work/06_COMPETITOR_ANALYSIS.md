# 06 — Competitor Analysis

← [05 Sponsors](05_SPONSOR_AND_PARTNER_RESEARCH.md) · [Master index](00_MASTER_RESEARCH_INDEX.md) · Next: [07 Previous winners](07_PREVIOUS_WINNERS_ANALYSIS.md)

Three rings of competition:

1. **Direct rivals**: other Code Cubicle 6.0 PS3 teams with public repos (these are the teams we must beat)
2. **Reference implementations**: Qdrant's own Edge demos (the bar judges hold)
3. **Market**: commercial and open-source edge databases, sync engines and agent-memory products (the "why not just use X?" questions)

> ⚠ **Note:** Smaran's repo `SanTiwari07/Smaran` is **public** and turned up in our GitHub searches. Rivals can read it too. Keep committing honest, incremental work; don't reveal final-round surprises in the repo until after the submission deadline.

---

## Ring 1: Direct rivals (CC 6.0, PS3), found via the GitHub search API, 26 Sep 2026

### 1.1 AegisEdge (akshatinnovate-png/AegisEdge): **the strongest rival**

| Aspect | Finding (FACT: from their README / requirements.txt [R1]) |
|---|---|
| Created / activity | Created 22 Sep 2026; **42 commits**; pushed 26 Sep; public **CI** (GitHub Actions) |
| Pitch | "An offline-first edge brain. It remembers locally, answers in single-digit milliseconds with no network, decides for itself what may leave the device, and reconciles with its peers the moment a radio comes back." |
| Demo hooks | **"Kill it and watch it come back"**: a GIF of SIGKILL → 6 memories recovered in 3.6 s. A three-mode console: **USE IT / PROVE IT / INSPECT IT**. "Six claims, each with the button that falsifies it" |
| Claims | 1,599 q/s unique queries on 4 cores; 60 acked writes, SIGKILL, 60 recovered; **0 invariant failures in 3,000 simulated executions**; a deterministic fleet simulator in CI that **fails the build if the unsigned control comes back clean** |
| Tech | FastAPI; ONNX Runtime; `wordllama`; **`qdrant-client>=1.9` ("Qdrant, embedded by default, or a server via AEGIS_QDRANT_URL")**; Ed25519 signing (`cryptography`); CRDT op-log, Merkle range digests, IBLT reconciliation; P2P mesh "with no cloud and no coordinator"; bitemporal knowledge graph; conformal abstention; SLO ladder; 103 modules; **332 tests** |
| Honesty section | "What does not work": ~25 KB per memory unexplained; memory growth per query; ingest decays; **"A remote Qdrant Server round trip … untested here"** |
| **Weaknesses (ANALYST)** | **(a) It does not appear to use Qdrant Edge.** `requirements.txt` lists only `qdrant-client` (embedded local mode). No `qdrant-edge-py`. PS3 says "uses Qdrant Edge" twice. A Qdrant judge will check. **(b) The server round trip is untested**, although PS3 explicitly names Qdrant Server. (c) Extreme breadth (103 modules, IBLT, conformal, …) is hard to explain in 5 minutes and risks "complexity for its own sake". (d) The P2P mesh sidesteps the PS's edge↔**cloud** framing |
| **Strengths to respect** | Falsifiable-claims UX; a visible crash-recovery demo; a CI-verified simulator; security (signed ops); ruthless honesty about limits. **This is the same "trust" positioning as Smaran.** |

**Head-to-head (ANALYST INFERENCE):**

| Dimension | AegisEdge | Smaran | Who wins today |
|---|---|---|---|
| Uses Qdrant Edge (R1) | ✗ (qdrant-client embedded) | ✓ `qdrant-edge-py` EdgeShard + built-in BM25 | **Smaran** (decisive if judges check) |
| Real Qdrant Server sync (R6) | ✗ untested | ✗ code done, not run on Docker | Tie; **whoever runs it first wins** |
| Conflict semantics | CRDT + "arbiter escalates genuine semantic conflicts" | Version vectors + human supervisor resolution + Chronos history | Tie on paper; Smaran's is **easier to show** |
| Privacy governance | Policy engine; sensitivity labels | Structural private shard with no sync path + PII rules + audit | Smaran is clearer to explain |
| Crash durability demo | **Live SIGKILL button + GIF** | Tests only; video-only plan | **AegisEdge** |
| Security (signing) | **Ed25519, fleet enrolment** | None | **AegisEdge** |
| Verification culture | CI + deterministic simulator + control run | pytest (30), Hypothesis, 1000-run convergence sim, 10/10 rehearsals; **no CI badge** | AegisEdge (visible), Smaran (substantive) |
| Explainability to judges in 5 min | Hard | Designed for it (4 beats, one story) | **Smaran** |
| Retrieval quality eval | Not stated | Not measured | Neither |

### 1.2 FieldEdge (choksi2212/code-cubicle-qdrant)

- **What:** "Offline-first AI platform for field workers — Android edition". It captures photos, embeds them with CLIP ViT-B/32 through ONNX, stores them in **Qdrant Edge via a custom Rust↔React Native bridge**, searches offline, and syncs to Qdrant Cloud. "Conflicts by timestamp + vector-checksum heuristics." [R2]
- **Strengths:** Runs on a **real phone** with a tangible demo (airplane mode ON → photos → search → airplane mode OFF → sync). Multimodal. A document pack (PRD, TRD, architecture).
- **Weaknesses (ANALYST):** Timestamp-based conflicts are exactly the naive merge Smaran's benchmark beats (13/50). The README says "hackathon (2025)", which is sloppy. A custom native bridge is a high demo risk. No governance of what syncs is described beyond "decides".

### 1.3 EdgeSync AI (lakshay2425/code-cubicle-ps-03)

- **What:** Next.js dashboard; "Qdrant Edge / Embedded"; hybrid search; "timestamp or vector-divergence logic to overwrite or merge"; "Deterministic Hot/Cold Storage"; a network-disruption toggle. [R3]
- **Weaknesses (ANALYST):** A marketing-heavy README with generic claims ("lightning-fast", "rugged"); conflict handling overwrites; the same team also has a PS2 repo, so effort is split. **Typical average entry.**

### 1.4 Edge-Mind-AI (theerthan-bg/Edge-Mind-AI)

- **What:** "Offline-first AI-powered edge memory and intelligence platform built for Code Cubicle 6.0". No README was retrievable (404). **NOT FOUND — REQUIRES VERIFICATION.**

### 1.5 Patterns across direct rivals (ANALYST INFERENCE)

1. **Everyone does the same three beats:** offline toggle → local search → sync on reconnect.
2. **Conflict handling is mostly timestamp/LWW** ("overwrite or merge", "timestamp + checksum"). Only AegisEdge does something principled.
3. **"Dynamically decide what stays local"** is usually a static rule ("hot/cold", "sensitivity label"). Nobody reports a **measured** accuracy.
4. **Real Qdrant Server sync is weak everywhere.** It is untested (AegisEdge) or replaced by "Qdrant Cloud" with no evidence shown.
5. **Qdrant Edge usage is shallow or absent.** Some use `qdrant-client` embedded mode; nobody uses **partial snapshots**, the flagship Edge sync API.
6. **Retrieval quality is never evaluated.** Only latency is reported.

→ These gaps are the differentiation map in [09](09_DIFFERENTIATION_STRATEGY.md).

---

## Ring 2: Qdrant's own reference demos (the bar)

| Name | Team | Problem | Tech | Strengths | What it leaves open (our opportunity) |
|---|---|---|---|---|---|
| Smart Glasses × Qdrant Edge | Qdrant | Find your keys offline | CLIP; mutable + immutable Edge Shards; **SQLite persistent queue**; server HNSW; partial snapshot sync; MMR | The canonical two-shard pattern, done right | No governance (everything syncs); no conflict semantics (visual memory has none) |
| Edge Mission Control | Qdrant Labs | Robot object memory | YOLOE, SigLIP2, Florence-2, Edge dense + BM25 + RRF, facets | Cinematic demo; sub-ms; `?auto` mode; `make test` | Single device; sync "on its own terms", but no multi-device truth |
| Video anomaly edge-to-cloud | Qdrant + Twelve Labs + NVIDIA + Vultr | Detect unseen anomalies | Jetson, two shards, kNN distance, cloud escalation | A measured business effect (~6× less cloud volume) | Needs a GPU and Marengo |

**ANALYST INFERENCE:** Judges have seen "a device remembers and searches offline" done beautifully by Qdrant itself. **Parity on that is table stakes. Differentiation has to come from what these demos don't do:** multi-device conflicts, privacy governance, durability, measured decisions.

---

## Ring 3: Market landscape

| Product | Org | Core | Vector search | Sync / conflicts | Strength | Gap vs PS3 / Smaran | Source |
|---|---|---|---|---|---|---|---|
| **Qdrant Edge** | Qdrant | In-process vector engine | ✓ dense, sparse, hybrid, MMR, formula | Snapshots and partial snapshots (server → edge); dual-write left to the app | Same engine as the server; ~11 MB | No governance or conflict layer (**that is what Smaran adds**) | Qdrant docs |
| Couchbase Lite + Sync Gateway | Couchbase | Mobile JSON DB + replication | ✓ (Enterprise) | Document revisions; **"most-revisions wins", LWW on save, "Deletes always win"**; custom resolvers possible | Mature, enterprise | Conflict default loses data; vector search is enterprise-only | Couchbase docs |
| ObjectBox | ObjectBox | "the edge vector database" (embedded object DB + HNSW) | ✓ | ObjectBox Sync (commercial) | Very fast on mobile/IoT | Proprietary sync; no semantic-conflict layer | objectbox.io |
| Ditto | Ditto | Edge-native mesh sync DB (CRDT), "Servers & Cloud Optional" | ✗ (not a vector store) | CRDT mesh | Works device-to-device offline | No semantic retrieval | ditto.com |
| PowerSync | JourneyApps | Postgres/Mongo ↔ on-device SQLite sync | via SQLite extensions | Server-authoritative | Easy adoption | Not vector-native | MongoDB migration page |
| MongoDB Atlas Device Sync (Realm) | MongoDB | Mobile sync | ✗ | — | — | **End-of-life, removed 30 Sep 2025**; MongoDB points users to Ditto / PowerSync | MongoDB docs |
| sqlite-vec | Alex Garcia (OSS) | SQLite vector extension, pure C, "runs anywhere" | ✓ (brute force + IVF / DiskANN variants) | none | Tiny, universal | Pre-v1; no hybrid fusion or sync | GitHub |
| LanceDB | LanceDB | Embedded multimodal lakehouse | ✓ | none native | Columnar, multimodal | Not edge-sync oriented | lancedb.com |
| Chroma / Milvus Lite / FAISS | various | Local vector stores | ✓ | none | Popular in tutorials | "Simply running a local vector database", which PS3 warns against | — |
| Google AI Edge RAG SDK | Google | On-device RAG for Android with LLM Inference API | ✓ | none | On-device LLM | **Marked "Deprecated"** on its own guide page | ai.google.dev |
| Mem0 (OSS / Platform) | Mem0 | Agent memory layer (LLM extracts memories) | via pluggable stores | Server-centric | Popular agent-memory API | Cloud/LLM-dependent; no offline or fleet conflict semantics | docs.mem0.ai |

### Market patterns (ANALYST INFERENCE)

1. **Vector search and sync live in different products.** Vector stores don't sync. Sync engines don't do semantic retrieval.
2. **Default conflict policies lose data** (LWW, most-revisions, deletes win), and the loss is silent.
3. **The market is consolidating.** Realm Sync is EOL. Google's edge RAG SDK is deprecated. There is room for "retrieval + governance + sync" as one layer. That is Smaran's business story.
4. **Agent-memory products (Mem0 and similar) assume the cloud and an LLM.** None is offline-first.

## Research references (academic grounding for our design choices)

| Topic | Reference | Why it matters |
|---|---|---|
| Version vectors / conflict detection | DeCandia et al., "Dynamo: Amazon's Highly Available Key-value Store", SOSP 2007: https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf | Vector clocks to detect concurrent writes and surface them to the application; Smaran's Themis follows this lineage |
| CRDTs | Shapiro et al., "Conflict-free Replicated Data Types", 2011: https://inria.hal.science/inria-00609399 | What AegisEdge uses; explains why automatic merge ≠ semantic truth |
| Local-first software | Kleppmann et al. (Ink & Switch), 2019: https://www.inkandswitch.com/essay/local-first/ | The seven ideals (offline, collaboration, ownership …); good pitch vocabulary |
| Edge RAG | "EdgeRAG: Online-Indexed RAG for Edge Devices", arXiv:2412.21023 (Dec 2024): https://arxiv.org/abs/2412.21023 | Memory-constrained on-device indexing; supports scheduling index work on edge devices (title and date verified; contents not reviewed) |

(These references are cited from bibliographic knowledge; only the EdgeRAG arXiv entry was re-fetched in this session. Reliability MEDIUM-HIGH.)

## Sources

| ID | Source | URL | Accessed | Info | Reliability |
|---|---|---|---|---|---|
| R1 | AegisEdge README + backend/requirements.txt + GitHub API | https://github.com/akshatinnovate-png/AegisEdge | 2026-09-26 | Rival design, claims, deps | HIGH (primary, self-reported claims) |
| R2 | FieldEdge README | https://github.com/choksi2212/code-cubicle-qdrant | 2026-09-26 | Rival design | HIGH (primary) |
| R3 | EdgeSync AI README | https://github.com/lakshay2425/code-cubicle-ps-03 | 2026-09-26 | Rival design | HIGH (primary) |
| R4 | Edge-Mind-AI (GitHub search result) | https://github.com/theerthan-bg/Edge-Mind-AI | 2026-09-26 | Existence only | LOW |
| R5 | GitHub search API ("code cubicle", "qdrant edge", date filters) | https://api.github.com/search/repositories | 2026-09-26 | Rival discovery | HIGH |
| Q-demos | qdrant/qdrant-edge-demo; qdrant-labs/edge-mission-control; qdrant/video-anomaly-edge | GitHub | 2026-09-26 | Reference demos | HIGH |
| CB | Couchbase Lite conflict docs; vector search docs | https://docs.couchbase.com/couchbase-lite/current/c/conflict.html | 2026-09-26 | Conflict defaults | HIGH |
| OB | ObjectBox | https://objectbox.io/ | 2026-09-26 | Positioning "edge vector database" | MEDIUM |
| DT | Ditto | https://www.ditto.com/ | 2026-09-26 | Edge-native sync | MEDIUM |
| MDB | MongoDB Device Sync deprecation | https://www.mongodb.com/docs/atlas/app-services/sync/device-sync-deprecation/ | 2026-09-26 | EOL 30 Sep 2025; alternatives | HIGH |
| SV | sqlite-vec | https://github.com/asg017/sqlite-vec | 2026-09-26 | Pre-v1, pure C | HIGH |
| GAE | Google AI Edge RAG guide | https://ai.google.dev/edge/mediapipe/solutions/genai/rag | 2026-09-26 | Marked deprecated | HIGH |
| M0 | Mem0 OSS overview | https://docs.mem0.ai/open-source/overview | 2026-09-26 | Library/server model | HIGH |
| LDB | LanceDB | https://lancedb.com/ | 2026-09-26 | Positioning | MEDIUM |
