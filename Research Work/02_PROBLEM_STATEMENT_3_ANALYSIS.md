# 02 — Problem Statement 3: Deep Analysis

← [01 Overview](01_HACKATHON_OVERVIEW.md) · [Master index](00_MASTER_RESEARCH_INDEX.md) · Next: [03 Organizer](03_ORGANIZER_RESEARCH.md)

## 1. Exact official text (FACT, verbatim from the Qdrant-branded PDF [S2 in 01])

> **PROBLEM STATEMENT 03 · [Qdrant logo]**
> **AI-Powered Edge Memory & Intelligence Platform**
>
> AI applications increasingly need to operate in environments where network connectivity is limited, latency is critical, and sensitive data cannot always leave the device. Robots, industrial systems, kiosks, vehicles, mobile devices, and other edge applications need to search and reason over locally generated information without continuously depending on a cloud service.
>
> Building such systems is challenging because applications need to maintain local vector memory, perform fast semantic retrieval, work offline, handle continuously changing data, and synchronize relevant information with the cloud when connectivity becomes available.
>
> The challenge is to build an AI-powered edge intelligence platform that uses Qdrant Edge to provide local semantic memory and retrieval, while intelligently managing the relationship between on-device data and centralized cloud knowledge.
>
> **GOAL** — Build an offline-first AI application powered by Qdrant Edge that can:
> / Maintain searchable semantic memory directly on an edge device.
> / Perform low-latency vector and hybrid search without network access.
> / Dynamically decide what information should remain local and what should be synchronized.
> / Support intermittent connectivity and continue operating offline.
> / Synchronize data between edge devices and Qdrant Server when connectivity returns.
> / Handle evolving local memory, updates, and conflicting information.
> / Provide a user-facing interface to inspect device memory, search results, synchronization status, and system activity.
> / Demonstrate a meaningful edge-to-cloud AI workflow, rather than simply running a local vector database.
>
> **EXPECTED OUTCOME** — A complete edge-native AI product that can remember, retrieve, operate offline, and synchronize intelligently when connected.

The short version on the event page is identical to the third paragraph.

## 2. Requirement decomposition (the checklist a judge can tick)

| ID | Requirement (official words) | Hard or soft | What a judge must see to tick it | Where Smaran answers it today |
|---|---|---|---|---|
| R1 | "uses **Qdrant Edge**" / "powered by Qdrant Edge" | **HARD, named tech** | `qdrant-edge-py` / `EdgeShard` in code, not `qdrant-client` local mode | ✅ `qdrant-edge-py==0.8.0`, `EdgeShard.create/load`, built-in `Bm25` (`backend/device/store.py`, `embed.py`) |
| R2 | "searchable semantic memory directly on an edge device" | HARD | Memories written and searched in-process | ✅ 3 shards (Krypta, Hermes, Agora) |
| R3 | "low-latency **vector and hybrid** search without network access" | HARD, "hybrid" named | Dense + sparse fusion; a latency number measured offline | ✅ 3.9 ms p50 / 5.6 ms p95 over 2,000 memories (`docs/BENCHMARKS.md`) |
| R4 | "**Dynamically decide** what … remain local and what … synchronized" | HARD, the "intelligence" | A per-item decision with a reason, not a static config | ✅ Argus: PII rules → classifier → dedup; 98.3% held-out accuracy |
| R5 | "Support intermittent connectivity and continue operating offline" | HARD | A link toggle; the app keeps working; the queue fills | ✅ Offline switch, SQLite outbox, crash replay tests |
| R6 | "Synchronize … between edge devices and **Qdrant Server**" | **HARD, named tech** | A real Qdrant Server receiving points; multiple devices | ⚠ **Code done, never run against the Docker Qdrant Server**; verified only in `qdrant-client` embedded mode (IMPLEMENTATION_PLAN status table) |
| R7 | "Handle evolving local memory, updates, and **conflicting information**" | HARD | Two offline devices disagree; the system detects it and does not silently overwrite | ✅ Themis version vectors, 50/50 vs naive 13/50; Chronos history |
| R8 | "user-facing interface to inspect device memory, search results, sync status, and system activity" | HARD, four named views | UI panels for each of the 4 nouns | ✅ 3 views + activity feed |
| R9 | "meaningful edge-to-cloud AI workflow, rather than simply running a local vector database" | **Anti-requirement** | A story where the cloud adds value back to the edge | ✅ Agora fleet mirror + change feed; ⚠ story strength depends on the demo |
| R10 | "Expected outcome: complete edge-native AI **product**" | Soft | Feels like a product for a user, not a library demo | ⚠ Framed as a maintenance copilot; needs a persona in the pitch |

**ANALYST INFERENCE:** R1, R3, R6 and R9 are the requirements a Qdrant engineer on the panel is most likely to probe. They are named Qdrant products or features, or an explicit warning. **R6 is the single largest open gap for Smaran.**

## 3. The problem

**A. What exactly is the problem?** Edge AI systems produce information locally: notes, frames, sensor events, conversations. They must recall it by meaning, instantly, with or without a network. Their knowledge must also stay coherent with a central system and with sibling devices. The hard part is not storing vectors. It is **governing, reconciling and trusting** memory that lives in many places and changes while disconnected.

**B. Root causes** (ANALYST INFERENCE, supported by Qdrant's own material)

1. **Physics and economics of connectivity.** Qdrant's launch post names latency, connectivity, cost, privacy and isolation as the five reasons cloud-first retrieval breaks at the edge [Q-blog-memory]. A 50-camera site produces 432,000 clips a day, far too many to ship upstream [Q-blog-anomaly].
2. **Vector search engines were built as servers.** Qdrant Edge exists because "Traditional vector stores — designed for large server environments — are not suitable" [Q-blog-edge].
3. **The sync layer is left to the developer.** Qdrant's documentation gives primitives (snapshots, partial snapshots, dual-write) and a reference two-shard pattern. The docs say plainly that "you may want to set up a background job or a message queue", and their sample uses an **in-memory queue** with the comment "For production use cases consider persisting changes" [Q-doc-sync]. Deduplication uses a **wall-clock timestamp** and **point ID** [Q-doc-guide]. Nothing addresses governance (what may leave) or semantic conflicts (two devices asserting different facts).
4. **Edge Shards have no background optimizer.** Optimisation is manual (`optimize()`), and "new points are brute-force searchable until then" [Q-doc-vs]. Applications must schedule maintenance.
5. **Edge Shards restore snapshots but cannot create them** [Q-doc-vs]. Edge→server data must be application-level writes. Only server→edge can use snapshots.

**C. Current process (how teams solve it today)**

| Approach | How | Problem |
|---|---|---|
| Cloud-only RAG | Every query goes to a hosted vector DB | Fails offline; 50+ ms round-trip; raw data leaves the device |
| Local-only store | sqlite-vec / Chroma / FAISS on the device | No fleet knowledge; no backup; no multi-device coherence |
| Qdrant reference pattern | Mutable + immutable Edge Shards, dual-write queue, partial snapshots | Syncs everything (no governance); in-memory queue; timestamp dedup (clock skew, silent loss of concurrent edits) |
| General mobile sync DBs | Couchbase Lite + Sync Gateway, Ditto, PowerSync, (Realm, now EOL) | Document-level conflict rules such as "most-revisions wins" or "deletes always win" [Couchbase]; vector search is a side feature or absent; no semantic memory layer |

**D–E. Existing solutions and their limits:** see [06 Competitor analysis](06_COMPETITOR_ANALYSIS.md).

## 4. Users and stakeholders

| Role | Who (for our chosen framing: factory maintenance) | What they need |
|---|---|---|
| **Primary user** | Shop-floor maintenance technician with a tablet or handheld, where Wi-Fi is poor | Log observations and fixes; instantly recall "what happened last time on CNC-07"; works in a dead zone |
| Secondary user | Shift supervisor | See conflicting reports; decide which is true; a safety-critical item reaches them first |
| Administrator | Plant IT / OT engineer | Configure privacy policy; audit what left the device; fleet status |
| Business | Plant operations / manufacturer | Less downtime, knowledge retention across shifts, compliance |
| Regulator / institution | Data-protection regime (India's DPDP Act 2023), safety auditors | Personal data minimised; audit trail |
| Platform vendor | Qdrant | A showcase that Qdrant Edge solves a real edge-to-cloud problem |

The same engine generalises to other PS3-listed environments: robots, kiosks, vehicles and mobile devices (see [09](09_DIFFERENTIATION_STRATEGY.md)).

## 5. Pain points (ranked, ANALYST INFERENCE)

1. **Silent data loss when devices disagree.** Last-writer-wins drops one technician's report. This is a safety issue in industrial settings.
2. **Private data leaking to the cloud** because sync is all-or-nothing.
3. **Lost work after a crash or reboot** while offline, because of in-memory queues.
4. **Search that is slow or wrong offline**: pure keyword search misses paraphrases; pure dense search misses part numbers such as "CNC-07".
5. **No visibility.** Nobody can see what the device knows, what is pending or what conflicted.
6. **Bandwidth and cost** of shipping everything.

## 6. Constraints

| Type | Constraint | Implication for the design |
|---|---|---|
| Technical | Qdrant Edge is **beta** ("API and functionality may change") [Q-doc-edge]; Python and Rust bindings only; single shard per `EdgeShard`; manual `optimize()`; restore-only snapshots; `query_groups` / `search_matrix` Rust-only [Q-doc-vs] | Pin versions (`qdrant-edge-py==0.8.0`); call `optimize()` on a schedule; keep a thin adapter |
| Cost | Hackathon: free tiers only; CPU laptops | Small embedding model (FastEmbed, 384-d); no GPU dependency |
| Infrastructure | Venue Wi-Fi is unreliable; Docker Desktop may not start (it did not on the dev laptop) | Offline is a software switch; the embedded fallback stays; test Docker before the day |
| Data | No public dataset of factory maintenance notes | Hand-written, labelled notes (100 now); disclose the size and the labelling limits |
| Security | Sync endpoints could be spoofed | Idempotency keys now; signing is future scope (AegisEdge already does Ed25519, see [06](06_COMPETITOR_ANALYSIS.md)) |
| Privacy | Phone numbers and names in notes; DPDP Act | Hard PII rules before any model; a private shard with **no sync code path** |
| Scalability | Edge Shard is single-device; the server scales | Per-device shard + server collection with a device-id payload (Qdrant multitenancy) |
| Geographic | Indian plants: patchy connectivity | Offline-first is the default, not a fallback |
| Regulatory | DPDP Act 2023 (personal data minimisation) | Residency decision + audit report |
| Adoption | Technicians will not type long notes | Short notes, quick types, search-first UI; voice is future scope |

## 7. Success metrics (with why each matters)

| Metric | Why it matters | Smaran today | Target for the final |
|---|---|---|---|
| Offline hybrid search p50 / p95 | R3 says "low-latency". Qdrant markets sub-ms in-shard latency, so we must show ms-level end-to-end | 3.9 / 5.6 ms (search), 11.5 / 14.5 ms incl. embedding | Keep; show live on screen |
| **Retrieval quality** (hit@1, hit@5, MRR on a golden query set; hybrid vs dense vs BM25) | Qdrant's community stresses "similarity ≠ relevance" and "measure hit rate, precision, recall" [Q-recap] | **Not measured** | Add: ≥ 30 golden queries; show that hybrid beats each single mode |
| Conflict correctness vs naive LWW | R7 is the core of "trust" | 50/50 vs 13/50 | Keep |
| Convergence across N devices | R6 multi-device | 1000/1000 | Keep |
| Residency accuracy / safety recall | R4 "dynamically decide" | 98.3% / 0.9 (60 held-out notes) | Add inter-labeller kappa; state the caveats |
| PII on server after the demo | Privacy claim, R4 | 0 / 0 | Keep; show the audit live |
| Bandwidth saved vs sync-everything | "synchronize relevant information" | 38.2% (target 40% missed) | ≥ 60% with float16 / binary vectors |
| Crash durability (acked writes lost after a kill) | R5 | 0 lost (test) | Show live |
| **Qdrant Server round trip** (points visible on the server; partial-snapshot bytes) | R6 names Qdrant Server | Not exercised | Run on Docker; show the server's dashboard/points count |
| Demo reliability | Final-round risk | 10/10 rehearsals | 10/10 on the demo laptop, venue conditions |

## 8. Interpretation: what "intelligently managing the relationship" means (ANALYST INFERENCE)

The phrase has three separable parts. Most teams will do only the first.

1. **Placement intelligence:** what lives where (private / shared / dropped / escalated).
2. **Consistency intelligence:** what is true when copies diverge (conflict detection, not only dedup).
3. **Flow intelligence:** what moves first, and how cheaply (priority, idempotency, partial snapshots, compression).

Smaran covers 1 and 2 strongly. Flow is partly covered (criticality-first outbox, idempotent sync). It still misses Qdrant's own partial-snapshot mechanism and efficient vector encoding. See the gap list in [20](20_FINAL_PROJECT_STRATEGY.md).

## Sources

| Tag | Source | URL | Accessed | Info | Reliability |
|---|---|---|---|---|---|
| S2 | Official PS PDF | see [01](01_HACKATHON_OVERVIEW.md) | 2026-09-26 | Verbatim PS3 | HIGH |
| Q-doc-edge | Qdrant Edge docs, overview | https://qdrant.tech/documentation/edge/ | 2026-09-26 | Beta status, "SQLite for vector search", sync purposes | HIGH |
| Q-doc-vs | Edge vs Qdrant Cluster | https://qdrant.tech/documentation/edge/edge-vs-qdrant-cluster/ | 2026-09-26 | Manual optimize, restore-only snapshots, Rust-only features | HIGH |
| Q-doc-sync | Data Synchronization Patterns | https://qdrant.tech/documentation/edge/edge-data-synchronization-patterns/ | 2026-09-26 | Snapshot init, partial snapshots, dual-write, in-memory queue comment | HIGH |
| Q-doc-guide | Synchronize with a Server | https://qdrant.tech/documentation/edge/edge-synchronization-guide/ | 2026-09-26 | Mutable + immutable shards, timestamp dedup, merge by score + ID | HIGH |
| Q-blog-edge | "Qdrant Edge (Private Beta)" | https://qdrant.tech/blog/qdrant-edge/ | 2026-09-26 | Rationale; use cases | HIGH |
| Q-blog-memory | "Memory at the Edge" | https://qdrant.tech/blog/qdrant-edge-on-device-vector-search/ | 2026-09-26 | Five reasons cloud-first breaks; ~11 MB footprint; sub-ms hybrid | HIGH |
| Q-blog-anomaly | Video anomaly edge-to-cloud | https://qdrant.tech/blog/video-anomaly-detection-edge-to-cloud/ | 2026-09-26 | 432k clips a day; ~6× cloud reduction via edge triage | HIGH |
| Q-recap | Vector Space Day SF 2026 recap | https://qdrant.tech/blog/vector-space-day-2026-recap/ | 2026-09-26 | "similarity and relevance are not the same thing" (Arize talk) | HIGH |
| Couchbase | Couchbase Lite: Handling Data Conflicts | https://docs.couchbase.com/couchbase-lite/current/c/conflict.html | 2026-09-26 | Most-revisions-wins, LWW, deletes always win | HIGH |
| Smaran docs | `docs/BENCHMARKS.md`, `docs/IMPLEMENTATION_PLAN.md` | local repo | 2026-09-26 | Current measured status | HIGH (our own measurements) |
