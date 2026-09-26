# 18 — Judge Perspective

← [17 Pitch](17_PITCH_AND_PRESENTATION_STRATEGY.md) · [Master index](00_MASTER_RESEARCH_INDEX.md) · Next: [19 Risks](19_RISK_ANALYSIS.md)

Likely judge types (ANALYST INFERENCE): (1) a Qdrant engineer/DevRel, (2) Geek Room / HackCulture organisers, (3) industry professionals from the host or partner companies (a Paytm-style engineering background), (4) data-science practitioners (as at CC3).

## Timeline of understanding

### Within 10 seconds, they should understand
> "It's an offline memory layer on **Qdrant Edge** that keeps private data on the device and **catches conflicting reports** instead of silently dropping one."

Enablers: the title slide tagline; the README first line; the hero GIF of the conflict card.

### Within 30 seconds
- The user is a **maintenance technician** with bad Wi-Fi; the supervisor decides conflicts.
- There are three places memory lives (**private / mutable / fleet mirror**), and only one of them syncs.
- It syncs to **Qdrant Server** when the link returns.

### Within 2 minutes, they should *believe*
- It **really runs offline** (they saw the switch off and ms-latency answers).
- The privacy guarantee is **structural** (a phone number went to Krypta; the server audit shows 0).
- Conflict detection is **principled** (version vectors) and **better than the default** (13/50 vs 50/50).
- The team **measures** things and **admits misses**.

### After the demo, they should remember
**"The team whose two devices disagreed and the system refused to guess."** Plus one number: **50/50 vs 13/50**.

## The strongest narrative

> Edge memory isn't a search problem; it's a **trust** problem: what may leave, what is true, and what was true when. Qdrant Edge solves storage and retrieval. Smaran solves trust, and proves it with numbers.

## Anticipated judge questions (with answers)

| # | Likely question | Answer (short, evidence-backed) |
|---|---|---|
| 1 | "Are you actually using Qdrant Edge or just the Python client?" | "`qdrant-edge-py` 0.8.0. Three `EdgeShard`s, the built-in `Bm25`, filters, scheduled `optimize()`. Here's `store.py`." |
| 2 | "Does it really sync to Qdrant Server?" | (After 1.6) "Yes. Here's the Qdrant Web UI; the point count went from N to N+3 when we reconnected." |
| 3 | "Why not use Qdrant's reference sync pattern?" | "We extend it: mutable shard + mirror, like the docs, plus a private tier, a persistent outbox (the docs' sample queue is in-memory) and version vectors instead of timestamp dedup." |
| 4 | "Why version vectors and not timestamps / CRDTs?" | "Clocks drift: with ±10 min skew, timestamps got 13/50. CRDTs auto-merge text, but two technicians' opposite reports shouldn't be merged. A human should decide." |
| 5 | "How does it 'dynamically decide' what syncs?" | "PII rules first (non-overridable), then a classifier (98.3% on 60 held-out hand-written notes), then dedup against fleet knowledge. Every decision shows its reason." |
| 6 | "Isn't 60 test notes tiny?" | "Yes. We say so in the README; the criticality rule was tuned after seeing results, so treat it as optimistic. Label agreement (kappa) is [value / in progress]." |
| 7 | "What happens on a crash mid-sync?" | "The SQLite WAL outbox replays on restart; the gateway dedups by op-id. Tested (`test_crash_recovery_replays_outbox`, `test_sync_is_idempotent`) [+ live kill beat]." |
| 8 | "How does it scale to 1,000 devices?" | "One Edge Shard per device; a server collection with a device-id payload partition (Qdrant multitenancy); Themis is O(versions per entity). The 5-device simulation converged 1000/1000; beyond that is design, not measured." |
| 9 | "What if a malicious device sends fake ops?" | "Not covered in the MVP. Next step: Ed25519 device signing + enrolment. We scoped it out deliberately." |
| 10 | "Why is bandwidth only 38%?" | "Vectors travel as JSON text (~9 KB/op). [After 2.1: float16 transport → X%.] The savings come purely from what we don't send." |
| 11 | "Where's the AI?" | "Three AI decisions on-device: embeddings for meaning, hybrid retrieval, and a learned residency/criticality classifier. We deliberately kept an LLM out of the loop: no hallucinated facts in a maintenance log." |
| 12 | "How is search quality measured?" | (After 2.2) "hit@5 on N golden queries: hybrid X vs dense Y vs BM25 Z." Otherwise: "Latency is measured; quality eval is our next step." (Try hard not to need this fallback.) |
| 13 | "What does partial snapshot give you?" | (If shipped) "The mirror downloads only changed segments: X KB vs Y MB." |
| 14 | "Who pays for this?" | "Plant operations: fewer repeat faults, knowledge retained across shifts, DPDP compliance. Delivered as an SDK layer over Qdrant Edge plus a gateway." |
| 15 | "What would you build next?" | Signing; multimodal notes (photos, voice on-device); CMMS integration; multilingual embeddings. |

## Judge "red flags" to avoid

- Hesitation on Q1 or Q2 (the Qdrant specifics).
- Numbers without denominators.
- A demo that needs the internet.
- Over-claiming ("any edge device", "guaranteed").
