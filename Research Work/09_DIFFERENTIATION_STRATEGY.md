# 09 — Differentiation Strategy

← [08 Patterns](08_WINNING_PATTERNS.md) · [Master index](00_MASTER_RESEARCH_INDEX.md) · Next: [10 WOW features](10_WOW_FEATURES.md)

## The question

> **"If 100 teams build solutions for PS3, why should the judges remember OUR project?"**

**Answer (RECOMMENDATION):**

> **Everyone else shows that a device can remember. Smaran shows that the memory stays *correct* and *private* when devices go offline and disagree. It is built on the real Qdrant Edge engine, synced to a real Qdrant Server, and every claim is measured.**

Tagline (existing, keep): **"Qdrant Edge gave devices a memory. Smaran makes that memory trustworthy offline."**

## Where the field is weak (evidence → opportunity)

| Gap observed | Evidence | Smaran's answer | Strength today |
|---|---|---|---|
| Conflicts resolved by timestamp/LWW → silent loss | FieldEdge ("timestamp + vector-checksum"), EdgeSync ("overwrite or merge"), Qdrant reference (timestamp dedup), Couchbase ("most-revisions wins") [06] | **Themis**: version vectors separate *newer* from *concurrent*; concurrent = flagged, never guessed; supervisor resolves; history kept (Chronos) | ★★★ measured 50/50 vs 13/50 |
| "What stays local" is a static rule | EdgeSync "hot/cold", AegisEdge "policy engine" [06] | **Argus**: hard PII rules → learned classifier → dedup, with a reason shown per item; **measured 98.3%** | ★★★ |
| Privacy by policy (bypassable) | Everyone | **Krypta** has *no sync code path*: privacy by structure + a server-side audit (0 private records, 0 PII matches) | ★★★ |
| Not actually Qdrant Edge | AegisEdge uses `qdrant-client` embedded [06] | `qdrant-edge-py` EdgeShard + built-in BM25 | ★★ (must be *said* and *shown*) |
| No real Qdrant Server round trip | AegisEdge "untested"; others unclear | Gateway → Qdrant Server (Docker) | ☆ **not yet run: close this** |
| Official partial-snapshot sync unused | Nobody among rivals | Agora mirror refreshed via `snapshot_manifest()` + partial snapshot | ☆ **not built: P1** |
| Retrieval quality unmeasured | Everyone | Golden-set hit@k / MRR, hybrid vs dense vs BM25 | ☆ **not built: P1** |
| Crash durability invisible | Only AegisEdge shows it | Crash-safe SQLite outbox, replay tests | ★ (tests) → needs a live button |

## Differentiation by axis

### Technical

| Lever | Keep / Add | Why it genuinely improves the solution |
|---|---|---|
| Version-vector conflict detection (Themis) | KEEP, lead with it | The only approach that detects concurrent edits without trusting device clocks (Dynamo lineage) |
| Three-shard layout (Krypta / Hermes / Agora) | KEEP | Maps PS3's "what stays local vs synced" onto *physical* Qdrant Edge shards; mirrors Qdrant's mutable/immutable pattern and extends it with a private tier |
| Device-wide BM25 IDF + global RRF across shards | KEEP, explain it | A real retrieval bug found and fixed (a one-note shard outranked real answers). Shows retrieval depth |
| Criticality-first outbox | KEEP | Safety-critical data moves first on a narrow link |
| **Partial-snapshot mirror refresh** | **ADD (P1)** | Qdrant's own recommended mechanism; cuts pull bandwidth; shows "Qdrant Usage" |
| **float16 / binary vector transport** | **ADD (P1)** | Turns the 38.2% bandwidth miss into a clear win; tiny code change |
| Formula scoring (recency decay) or MMR in Edge | NICE | Uses Edge-native scoring primitives; better "latest fact first" ranking |
| Signing (Ed25519) | AVOID now | AegisEdge owns this; mention as future scope |

### Product

- **Persona-first UI:** "What does device A know about CNC-07?" and not "shard browser".
- **Explainability everywhere:** every memory shows *why* it went where it went (rule / classifier + confidence), *where* it lives (shard), *what* it knows (version vector), and *what it replaced* (Chronos).
- **Human-in-the-loop truth:** the supervisor resolves; the system never guesses. This is the right call for safety.

### Impact

| Claim | Metric | Status |
|---|---|---|
| No silent data loss | 0 concurrent edits lost in 1,000 × 5-device runs | ✓ |
| Privacy | 0 private records / 0 PII on the server | ✓ |
| Works in dead zones | 3.9 ms p50 offline | ✓ |
| Cheaper links | bandwidth saved vs sync-all | 38.2% → target ≥ 60% with float16 |
| Safety | safety-critical recall 0.9; critical notes sync first | ✓ (small test set, disclosed) |

### Business

- **Buyer:** plant operations / OT (and, generalised, fleets of robots, kiosks and vehicles).
- **Value:** less downtime from repeat faults; knowledge retained across shifts; compliance (DPDP).
- **Model (future):** an SDK layer on top of Qdrant Edge + a gateway (per-device licence), or open core + managed gateway. It complements Qdrant rather than competing with it, which is a good message for a Qdrant judge.
- **Integration:** gateway webhooks (n8n / CMMS such as SAP PM or Maximo; future).

### Demo

- **Story, not tour:** 4 beats, each with its own reset (already built).
- **Reveal moment:** the conflict split + "what naive merge would have lost".
- **Physical moment (optional):** kill a device process live; it comes back with nothing lost.
- **Proof moment:** the server audit panel ("0 private records on Qdrant Server"), with the Qdrant Server dashboard open in a second tab.

## Positioning statement (for slides / README)

> For maintenance teams and edge-AI fleets that must work without reliable connectivity, **Smaran** is a memory layer on **Qdrant Edge** that keeps on-device memory **private by construction, correct under conflict, and synced to Qdrant Server** when the link returns. Unlike last-writer-wins sync (Qdrant's reference pattern, Couchbase, most hackathon entries), Smaran **never silently drops a conflicting report** and **proves** its privacy and latency with measured numbers.

## Anti-positioning (what we are NOT)

- Not a chatbot. Not "RAG on a laptop". Not a P2P mesh. Not a new vector database.
