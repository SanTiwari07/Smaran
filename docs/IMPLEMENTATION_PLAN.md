# ΣMARAN — Implementation Plan (Code Cubicle 6.0, PS3)

> ## Smaran: *aletheia at the edge.*
> *Memory that doesn't forget, and doesn't lie.*

Built from: [`PROPOSAL.md`](PROPOSAL.md) + [`reference/problem-statements.pdf`](reference/problem-statements.pdf) (page 3, PS3 · Qdrant), checked against the live Qdrant Edge docs and Qdrant's own Python examples (`qdrant/qdrant` → `lib/edge/python/examples`) on 25 Sep 2026.

---

## Name and identity

- **Smaran** (स्मरण) is Sanskrit for *recall*. The logo is written **ΣMARAN**: the Greek capital sigma (Σ) means "sum" in maths, and here it stands for a fleet of devices adding up to one memory. Say it "Smaran".
- **Aletheia** (ἀλήθεια) is Greek for *truth*, and literally means *un-forgetting* (a- = not, lēthē = forgetting). That's the pitch: edge memory that stays **true**, not just stored.
- **Component names** (use these in the UI, logs, video and README):

| Name | Component | Meaning |
|---|---|---|
| **Krypta** | Private shard | "Hidden place": never leaves the device |
| **Hermes** | Mutable shard + outbox + sync worker | The messenger: carries memories when the link returns |
| **Agora** | Mirror shard | The public square: shared fleet knowledge |
| **Themis** | Conflict resolver | The goddess of fair judgment: flags conflicts, never guesses |

**One-line pitch:** *"Krypta keeps what's private, Hermes carries the rest when the link returns, Agora shares what the fleet knows, and Themis decides what's true when devices disagree."*

---

## Implementation status (26 Sep 2026)

**All P0 items and most P1 items are built and tested.** Measured results are in [BENCHMARKS.md](BENCHMARKS.md), how to run them is in the [README](../README.md), the presenter script is in [DEMO.md](DEMO.md), and troubleshooting is in [DEBUGGING.md](DEBUGGING.md).

| Area | Status | Proof |
|---|---|---|
| Day-0 spike (§9) | Passed on Windows, `qdrant-edge-py` 0.8.0 | create/load, BM25, fusion, filters, `set_payload`, UUID ids |
| 3 shards, hybrid search, offline flag | Done | 3.9 ms p50 / 5.6 ms p95 over 2,000 memories |
| Argus: PII rules → LogReg → dedup | Done | 98.3% residency accuracy on 60 held-out notes |
| Outbox, crash recovery, idempotent `/sync` | Done | `test_crash_recovery_replays_outbox`, `test_sync_is_idempotent` |
| Themis on device + gateway, resolve | Done | Property test; 1000/1000 converged in the 5-device sim |
| Change feed → Agora, cloud escalation, criticality-first | Done | `test_critical_first`, e2e tests |
| Dashboard, 3 views + Chronos + naive-merge comparison + mock mode | Done | Checked in the browser against the live backend |
| `demo.py` start/stop/reset/play/rehearse | Done | 10/10 automated rehearsals |
| Bandwidth ≥ 40% | **Done: 85.7%** with float16 vector transport | Selection alone is still 38.2%; BENCHMARKS reports both |
| Retrieval quality | Done | 40 golden queries: hybrid hit@5 0.975 vs dense 0.95 vs BM25 0.95 |
| Label agreement (kappa) | **Measured with an AI second labeller, not a human**: residency 1.000, criticality 0.661 (below the 0.7 target) | `python -m ml.train`, BENCHMARKS "Residency classifier". A human second labeller is still open |
| Qdrant Server mode (Docker) | **Done**: `qdrant/qdrant:v1.19.1` + `qdrant-client==1.19.1` | 10/10 rehearsals (beats 1–4) and 10/10 (beat 5) against the server, in `logs/rehearsal.log` |
| Crash durability | Done | Beat 5: crash after the gateway stored a batch → resend → 0 duplicates; Krypta journal + Agora re-pull after an unclean shutdown |
| CI | Done | GitHub Actions: pytest on Ubuntu and Windows, dashboard build |
| Laya, partial snapshots, full Docker Compose | P2, not started | |

### Where the code differs from this plan, and why

1. **Search (changes finding #4 in §0).** Native `Fusion.Rrf` per shard, then merging the three shard lists by rank, let a one-note Krypta outrank the real answer, because every shard's #1 counts the same. Search now builds one global dense list (cosine is comparable across shards) and one global BM25 list, and fuses those with RRF. BM25 uses a **device-wide IDF**: shards store plain BM25 weights and `Store` keeps one document-frequency table. Per-shard IDF had pushed fresh notes in the small Hermes shard below old manuals. See `backend/device/search.py` and `store.py`.
2. **Criticality** = safety-critical if the model *or* the safety keywords say so, otherwise the keyword level. The model alone had 0.72 accuracy and keywords alone missed 4 of 10 safety notes; combined: 0.80 accuracy, 0.9 safety recall. This rule was chosen after seeing the test set, and the README says so.
3. **Resets delete points instead of files or collections.** Deleting shard folders took ~15 s on Windows, and qdrant-client's embedded mode brought old points back after `delete_collection`.
4. **Files added:** `backend/device/core.py` (device logic, so `app.py` stays thin), `backend/common/log.py` (renamed from `logging.py`, which would shadow the standard library), `pytest.ini`.
5. **Themis API:** `resolve(versions)` computes statuses from the *set* of versions. `apply()` from §4.4 is built on it, which makes order-independence hold by construction.

### Next steps for the team

The current work plan is [AUDIT_AND_PLAN.md](AUDIT_AND_PLAN.md). Still open for the team:

- [x] Second labels for h001–h060 in `residency_2` / `criticality_2` (done by an AI model, 29 Sep; kappa 1.000 / 0.661).
- [ ] Optional: C or D relabels h001–h060 independently, so agreement is between humans. Criticality is under 0.7, so tighten the level 1 vs 2 definition first.
- [ ] Review `ml/data/handwritten_notes.csv` and `bench/golden_queries.json`; a second person should label the golden queries independently.
- [ ] Record the backup video using [DEMO.md](DEMO.md).

---

## 0. What changed after the analysis (read this first)

| # | Finding | Impact on the plan |
|---|---|---|
| 1 | **The proposal's calendar is off by one day.** 25 Sep 2026 is a **Friday**, not Thursday; 30 Sep 2026 is a **Wednesday**, not Tuesday. The PDF footer also says **"3 OCT ONLINE · 11 OCT OFFLINE"**, and neither date appears in the proposal. | **Confirm the real submission deadline today.** This plan assumes *submit by noon Wed 30 Sep*. If it is actually Tue 29, drop Day 4 (section 6). If it is 3 Oct, you gain 3 days → pull in the P1/P2 items. |
| 2 | **`qdrant-edge-py` 0.8.0 ships a Windows wheel** (`cp310-abi3-win_amd64`, Python ≥ 3.10) plus Linux and macOS wheels. | The "Edge spike eats day 1" risk is much lower. Timebox it to **1 hour**, not 3. |
| 3 | **Qdrant Edge has a built-in BM25 embedder** (`Bm25`, `Bm25Config`), and its token IDs match Qdrant Server's BM25. | **Drop FastEmbed `Qdrant/bm25`** and use Edge's own. That's one less model to download, and the server can score device-made sparse vectors without re-indexing. |
| 4 | Native hybrid search in Edge is `Prefetch` + `Fusion.Rrf(k=…, weights=[…])`. It works **within one shard**. | Smaran queries 3 shards, so we fuse **per shard natively**, then merge the three lists with a **rank-based RRF in Python** (section 4.3). |
| 5 | **RRF scores are rank-based**, so "escalate to cloud if the best local score is below a threshold" can't use them. | The escalation threshold uses the **top dense cosine score**, not the fused score. |
| 6 | Qdrant's reference sync guide uses an **in-memory `Queue`** and a **wall-clock `timestamp` payload** for dedup. | This confirms the proposal's "gap" table. Quote the guide in the README and video. |
| 7 | Laya is on PyPI (`laya` 0.3.20, Python ≥ 3.10). I could **not** verify the 0.36/0.77 accuracy figures. | Keep "measure, don't assume". The **logistic-regression classifier is the default**, and Laya is P2 (section 5). |
| 8 | Free-text notes don't carry an `entity_key` on their own, and conflict detection needs one. | The note form has a **machine dropdown + note type** (status / observation / fix / personal) + free text, so `entity_key` is deterministic and there's no NLP risk. |

---

## 1. Requirement traceability (PS3 goal → feature → proof)

Every PS3 bullet maps to a P0 feature and a check that is visible on screen or in the README.

| PS3 goal (PDF p.3) | Smaran feature | Owner | Acceptance test |
|---|---|---|---|
| Searchable semantic memory on device | 3 Qdrant Edge shards, bge-small dense vectors | A | Write a note offline → it's findable within 1 s |
| Low-latency vector + hybrid search offline | Dense + Edge BM25, per-shard RRF + cross-shard RRF | A | `bench.py`: p50 < 20 ms, p95 < 50 ms on 1k queries, device offline |
| Dynamically decide local vs sync | PII rules → classifier → mirror dedup, with a decision log | A + D | Phone-number note → private shard; server audit = 0 |
| Intermittent connectivity, keep working | Software `online` flag, SQLite outbox, retry with backoff | A | Offline writes queue up; flip online → outbox drains to 0 |
| Sync with Qdrant Server when back | Gateway `/sync` (idempotent) + `/changes` → mirror | B | Device B sees device A's note after both sync |
| Updates + conflicting info | Version-vector resolver; superseded/contested; resolve button | B | Two offline writes to the same entity → *contested* on both devices |
| UI: memory, search, sync, activity | 3-view React dashboard | C | Every view renders against the real APIs |
| Meaningful edge-to-cloud workflow | Mirror of fleet knowledge, cloud escalation, supervisor resolution | B + C | Demo beat 3 + 4 |

---

## 2. Architecture and runtime layout

```
                         ┌──────────────────────── laptop ────────────────────────┐
 Dashboard (Vite :5173) ─┼─► device-A API :8001   device-B API :8002             │
                         │     ├ Edge shards: private/ mutable/ mirror/          │
                         │     ├ SQLite: outbox, decisions, meta                  │
                         │     └ sync worker (only when online flag = true)       │
                         │            │ POST /sync, GET /changes, POST /search    │
                         │            ▼                                           │
                         ├─► gateway :8000 (FastAPI + SQLite seen_ops, server_seq)│
                         │            ▼                                           │
                         │     Qdrant Server :6333 (Docker) collection "smaran"   │
                         └────────────────────────────────────────────────────────┘
```

- **Devices only ever talk to the gateway**, never to Qdrant Server directly. That gives one place for idempotency, conflict resolution and the privacy audit.
- Devices run as **native Python processes** (`python -m backend.device --id A --port 8001`, run from the repo root). Each device keeps its data in `runtime/device-A/`. Only Qdrant Server runs in Docker (`infra/`), which keeps the Windows dev loop fast. Docker Compose for everything is P2.
- The dashboard polls every **1 s**, with no WebSockets. That's simpler and good enough for a demo.

### Repository layout (frontend / backend split, one folder per concern)

```
Smaran/
├── README.md                 # short: what it is, quick start, link to docs/
├── .gitignore  .env.example  # ports, URLs, thresholds in one place
├── docs/                     # ALL project .md files live here
│   ├── IMPLEMENTATION_PLAN.md
│   ├── PROPOSAL.md
│   ├── (later) ARCHITECTURE.md  API.md  DEMO.md  BENCHMARKS.md  DEBUGGING.md
│   └── reference/problem-statements.pdf
├── backend/                  # all Python services
│   ├── requirements.txt
│   ├── common/               # shared by device + gateway + bench (import, never copy)
│   │   ├── config.py         # reads .env: ports, gateway URL, thresholds
│   │   ├── logging.py        # JSON-lines logger → logs/<service>.log
│   │   ├── schema.py         # pydantic: Memory, Version, Decision, SyncBatch
│   │   ├── themis.py         # resolver: version vectors + apply() ← the heart
│   │   └── pii.py            # regex rules (Argus layer 1)
│   ├── device/               # one process per simulated device
│   │   ├── __main__.py       # CLI: --id --port
│   │   ├── app.py            # FastAPI routes only (thin)
│   │   ├── store.py          # Edge shards: Krypta / Hermes (mutable) / Agora
│   │   ├── embed.py          # FastEmbed bge-small + Edge Bm25
│   │   ├── search.py         # per-shard RRF + cross-shard merge + escalation
│   │   ├── router.py         # rules → classifier → dedup → decision log
│   │   ├── classifier.py     # ResidencyClassifier; LogReg; Laya (P2)
│   │   ├── outbox.py         # SQLite outbox (WAL)
│   │   └── hermes.py         # sync worker: push, pull /changes, apply Themis
│   ├── gateway/
│   │   ├── __main__.py
│   │   ├── app.py            # /sync /changes /search /resolve /audit /contested /stats
│   │   └── server.py         # qdrant-client wrapper
│   └── tests/                # pytest: test_themis.py, test_pii.py, test_outbox.py, ...
├── frontend/                 # React + Vite + Tailwind + shadcn/ui (the Olympus dashboard)
│   └── src/
│       ├── api/              # typed clients for device + gateway APIs
│       ├── mock/             # mock API, same contracts as section 3
│       ├── views/            # DevicesSync, MemorySearch, ConflictsDecisions
│       └── components/
├── ml/                       # classifier track (owner D)
│   ├── data/                 # gen_notes.py, labelled_notes.csv, label_guide
│   ├── train.py  eval.py     # baselines, kappa, accuracy table
│   └── artifacts/            # trained classifier (git-ignored)
├── bench/                    # bench.py, naive_merge.py, simulate.py (5-device)
├── seed/                     # demo seed data: manuals/, beats/b1..b4.json
├── scripts/                  # setup_models.py, demo.py (start-all, reset <beat>, stop-all)
├── infra/                    # docker-compose.yml (Qdrant Server)
├── models/                   # downloaded weights         (git-ignored)
├── runtime/                  # shard dirs + SQLite per device/gateway (git-ignored; wiped by reset)
└── logs/                     # one log file per service   (git-ignored)
```

### Debugging conventions (agree on Day 0)

- **One service, one folder, one log file:** `logs/device-A.log`, `logs/device-B.log`, `logs/gateway.log`. Use JSON lines with `ts`, `service`, `level`, `event`, `op_id`, `entity_key`.
- **Follow one memory end to end** by grepping its `op_id` across all logs: router decision → outbox → `/sync` → Themis → `/changes` → Agora.
- **Routes stay thin.** `app.py` only parses and calls functions, so every bug can be reproduced in a pytest without starting servers.
- **All runtime state lives in `runtime/`.** `python scripts/demo.py reset base` deletes it and reseeds, so there's never stale shard state.
- **Frontend debugging:** every view works against `src/mock/` with `VITE_USE_MOCK=1`. If the UI breaks, flip to mock to see whether the bug is in the frontend or the backend.
- **Health endpoints:** each service has `GET /health` returning its config (ports, gateway URL, online flag, shard counts).

---

## 3. Contracts: freeze these on Day 0 so all 4 people can work in parallel

### 3.1 Memory payload (the same on device shards and on the server)

```jsonc
{
  "op_id": "A-000042",                 // device_id + local seq; point id = uuid5(NS, op_id)
  "entity_key": "machine:CNC-07/status", // null for free observations (append-only, no conflicts)
  "machine": "CNC-07",
  "kind": "status | observation | fix | personal | manual",
  "text": "CNC-07 bearing replaced, vibration normal",
  "device_id": "A",
  "author": "tech-A",
  "vv": {"A": 42, "B": 17},            // version vector
  "seq": 42,
  "valid_from": 1790000000.0,           // wall clock, display/history only
  "valid_to": null,
  "superseded_by": null,                // op_id
  "status": "current | superseded | contested",
  "residency": "private | sync | drop",
  "criticality": 0,                     // 0 routine, 1 important, 2 safety-critical
  "decision": {"by": "pii_rule | classifier | dedup", "confidence": 0.93, "reason": "phone number matched"},
  "server_seq": 1234                    // set by gateway only; used by /changes
}
```

Payload indexes on each shard: `status` (keyword), `entity_key` (keyword), `machine` (keyword), `server_seq` (integer; server side, needed for ordering).

### 3.2 Device API (port 800x). The dashboard mock implements exactly this.

| Method | Path | Body / query | Returns |
|---|---|---|---|
| GET | `/state` | – | `{device_id, online, outbox_depth, last_sync, counts:{private,mutable,mirror}}` |
| POST | `/online` | `{online: bool}` | state |
| POST | `/notes` | `{machine, kind, text, author}` | `{memory, decision}` |
| GET | `/search` | `q, include_superseded=false, at=<ts>` | `{results:[{memory, shard, dense_score, rrf_rank}], latency_ms, answered: "local" \| "escalated"}` |
| GET | `/memories` | `shard, status, machine` | list |
| GET | `/decisions` | `limit` | decision log |
| GET | `/history` | `entity_key, at` | versions valid at `at` |
| POST | `/sync-now` | – | push/pull summary |

### 3.3 Gateway API (port 8000)

| Method | Path | Purpose |
|---|---|---|
| POST | `/sync` | `{device_id, ops:[{op_id, point:{vectors, payload}}]}` → per-op `applied \| duplicate \| stale`. Skip seen `op_id`, run the resolver, upsert, bump `server_seq` |
| GET | `/changes?since=N&limit=500` | Scroll points with `server_seq > N`, ordered by `server_seq` |
| POST | `/search` | Cloud escalation (the device sends dense + sparse vectors, not text) |
| GET | `/contested` | Contested groups by `entity_key` |
| POST | `/resolve` | `{entity_key, chosen_op_id \| text}` → a new version whose vv = merge(all contested) + `{"supervisor": n}` |
| GET | `/audit` | `{total, private_count, pii_regex_hits}`; both must be 0 |
| GET | `/stats` | Bytes received, ops by device, for the bandwidth metric |

### 3.4 Outbox (device SQLite, `PRAGMA journal_mode=WAL`)

```sql
CREATE TABLE outbox(op_id TEXT PRIMARY KEY, criticality INT, seq INT,
                    body BLOB, attempts INT DEFAULT 0, next_try REAL DEFAULT 0,
                    state TEXT DEFAULT 'pending');   -- pending | acked
CREATE TABLE decisions(id INTEGER PRIMARY KEY, ts REAL, op_id TEXT, by TEXT,
                       residency TEXT, criticality INT, confidence REAL, reason TEXT);
CREATE TABLE meta(k TEXT PRIMARY KEY, v TEXT);  -- seq counter, last server_seq seen
```
Send order: `ORDER BY criticality DESC, seq ASC`. Reordering is safe **because the resolver is order-independent** (section 4.4). Say this out loud in the demo.

---

## 4. Module specs, with API calls taken from the docs

### 4.1 Edge shards: Krypta, Hermes, Agora (`backend/device/store.py`, owner A)

```python
from qdrant_edge import (EdgeShard, EdgeConfig, EdgeVectorParams, EdgeSparseVectorParams,
                         Distance, Modifier, UpdateOperation, PayloadSchemaType, Point)

def make_config():
    return EdgeConfig(
        vectors={"dense": EdgeVectorParams(size=384, distance=Distance.Cosine)},
        sparse_vectors={"bm25": EdgeSparseVectorParams(modifier=Modifier.Idf)},
    )

def open_shard(path):
    path.mkdir(parents=True, exist_ok=True)
    if any(path.iterdir()):
        return EdgeShard.load(str(path))          # create() fails on non-empty dir
    s = EdgeShard.create(str(path), make_config())
    for f in ("status", "entity_key", "machine"):
        s.update(UpdateOperation.create_field_index(f, PayloadSchemaType.Keyword))
    return s
```
- Write: `shard.update(UpdateOperation.upsert_points([Point(id=pid, vector={"dense": d, "bm25": sp}, payload=p)]))`
- Status change: `UpdateOperation.set_payload(point_ids=[pid], payload={"status": "superseded", ...})`, which is listed in the docs' update-ops table. Check the exact kwargs in the Day-0 spike.
- Call `shard.optimize()` on an **idle timer** (e.g. no writes for 10 s) and after bulk mirror ingest. Edge has no background optimizer.
- Call `shard.close()` on shutdown (FastAPI lifespan).

### 4.2 Embeddings (`backend/device/embed.py`, owner A)

```python
from fastembed import TextEmbedding
from qdrant_edge import Bm25, Bm25Config
dense = TextEmbedding("BAAI/bge-small-en-v1.5", cache_dir="models", local_files_only=True)
bm25  = Bm25(Bm25Config(language="english"))
# notes:   bm25.embed_document(text)   queries: bm25.embed_query(text)   (never mix them up)
```
`scripts/setup_models.py` downloads once. Run devices with `HF_HUB_OFFLINE=1`.

### 4.3 Hybrid query across 3 shards (`backend/device/search.py`, owner A)

```python
from qdrant_edge import QueryRequest, Prefetch, Query, Fusion, Filter, FieldCondition, MatchValue

NOT_SUPERSEDED = Filter(must_not=[FieldCondition(key="status", match=MatchValue(value="superseded"))])

def shard_hybrid(shard, dvec, svec, k=20, flt=NOT_SUPERSEDED):
    pf = lambda q: Prefetch(query=q, limit=k, filter=flt, prefetches=[], params=None, score_threshold=None)
    return shard.query(QueryRequest(
        prefetches=[pf(Query.Nearest(dvec, using="dense")), pf(Query.Nearest(svec, using="bm25"))],
        query=Fusion.Rrf(k=60), limit=k, offset=0, filter=None, score_threshold=None,
        params=None, with_payload=True, with_vector=False))

def search(q):
    dvec, svec = embed_query(q)
    lists = {name: shard_hybrid(s, dvec, svec) for name, s in shards.items()}
    fused = rrf_merge(lists, k=60)              # rank-based, pure Python, dedupe by point id
    top_cos = best_dense_cosine(dvec)           # separate cheap dense query, limit=1
    if online and top_cos < ESCALATE_AT:        # e.g. 0.55; tune on 20 queries
        fused = merge_with_cloud(fused, gateway_search(dvec, svec)); answered = "escalated"
```
For the history slider (`at=ts`), swap the filter for "`valid_from <= ts` and (`valid_to` is null or `> ts`)". If range filters are awkward in Edge, do it in Python over the top 100 results. That's fine at demo scale.

### 4.4 Themis, the resolver (`backend/common/themis.py`, owner B). This is the core; never cut it.

```python
def compare(a: dict, b: dict) -> str:          # 'equal' | 'after' | 'before' | 'concurrent'
    ks = a.keys() | b.keys()
    ge = all(a.get(k, 0) >= b.get(k, 0) for k in ks)
    le = all(a.get(k, 0) <= b.get(k, 0) for k in ks)
    return "equal" if ge and le else "after" if ge else "before" if le else "concurrent"

def merge(*vvs): return {k: max(v.get(k, 0) for v in vvs) for k in set().union(*vvs)}

def apply(live: list[Version], new: Version) -> Plan:
    """live = versions of new.entity_key whose status is current|contested."""
    if any(compare(new.vv, c.vv) == "equal" for c in live):   return Plan.duplicate()
    dominators = [c for c in live if compare(new.vv, c.vv) == "before"]
    if dominators:                                           # arrived late: keep as history
        return Plan.store(new, status="superseded", superseded_by=dominators[0].op_id)
    beaten    = [c for c in live if compare(new.vv, c.vv) == "after"]
    survivors = [c for c in live if c not in beaten] + [new]
    status    = "current" if len(survivors) == 1 else "contested"
    return Plan(store=new, supersede=beaten, set_status={s.op_id: status for s in survivors})
```
- **Local write:** `vv = merge(*[c.vv for c in live_local]); vv[device_id] = next_seq()`. It dominates everything the device has seen.
- **Resolution = just another write** from `"supervisor"`: `vv = merge(*contested) + {"supervisor": n}`. It dominates all contested versions, so every replica converges without special cases.
- **Why it converges:** the final live set is always the *set of maximal version vectors* among the delivered versions. That doesn't depend on delivery order, and duplicates are no-ops. This is exactly what the 5-device simulation checks.
- The **same function** runs in the gateway `/sync` and in the device's mirror ingest.

**Tests (`backend/tests/test_themis.py`):** unit cases (update, stale arrival, concurrent pair, 3-way concurrent, resolution, duplicate) plus a **Hypothesis property test**: random ops × random permutation × random duplication → identical final state. B owns the unit cases; D reuses them for the 50-case conflict-accuracy benchmark.

### 4.5 Residency router (`backend/device/router.py`, owner A; classifier by D)

1. **PII rules** (`backend/common/pii.py`): Indian mobile `(\+91[\s-]?)?[6-9]\d{9}`, email, Aadhaar-like `\b\d{4}\s?\d{4}\s?\d{4}\b`, `kind == "personal"`. A match forces `private` at confidence 1.0.
2. **Classifier** behind one interface:
   ```python
   class ResidencyClassifier(Protocol):
       def predict(self, text: str, emb: list[float]) -> tuple[str, float, int]: ...  # residency, conf, criticality
   ```
   Default `LogRegClassifier`: two scikit-learn `LogisticRegression` heads on the bge-small embedding already computed for storage, so it adds almost no latency. Add a **safety keyword override** (fire, smoke, sparks, leak, injury, lockout, overheating → criticality 2).
3. **Dedup:** a dense query on the **mirror** with `score_threshold=0.95`, `limit=1`. If there's a hit, the note is `drop` (logged, not stored). Skip dedup for `kind == status`, because statuses must go through the resolver.
4. Route: `private` → private shard only (**that module never imports `outbox`**, so privacy is guaranteed by the code structure). `sync` → mutable shard + outbox. `drop` → decision log only.

**Crash safety:** write the outbox row first (`pending`), then upsert to the mutable shard. On startup, re-upsert every pending row (safe, because the point id is deterministic). The gateway dedups by `op_id`, so a retry after a crash is harmless.

### 4.6 Hermes, the sync worker (`backend/device/hermes.py`, owner A for push, B for pull)

Loop every 2 s while `online`:
1. **Push:** up to 20 pending ops in criticality order → `POST /sync`. Mark them `acked` on `applied | duplicate | stale`. On a network error: `attempts += 1`, `next_try = now + min(2**attempts, 30)`.
2. **Pull:** `GET /changes?since=<meta.last_server_seq>`. For each point: upsert into **mirror**, delete the same id from **mutable** (it's now fleet knowledge), and run the resolver for its `entity_key` across local live versions (mutable + mirror) so local statuses match the server.
3. `optimize()` the mirror after pulling more than 50 points.

### 4.7 Gateway (`backend/gateway/`, owner B)

- On startup, create collection `smaran`: `vectors_config={"dense": VectorParams(384, COSINE)}`, `sparse_vectors_config={"bm25": SparseVectorParams(modifier=Modifier.IDF)}`, plus payload indexes `entity_key`, `status`, `server_seq` (integer).
- `seen_ops(op_id PRIMARY KEY)` and a `server_seq` counter in SQLite. Handle `/sync` inside one lock (`asyncio.Lock`). That's plenty for a demo and removes race conditions.
- `/sync`: for each op → skip if seen → fetch live versions for the entity from Qdrant (filter `entity_key` + status ≠ superseded) → `resolver.apply` → upsert new + `set_payload` on changed ones, each with a new `server_seq`.
- **Reject** any payload with `residency == "private"` or a PII regex hit (defence in depth; should never happen). Count rejections in `/stats`.

### 4.8 Olympus dashboard (`frontend/`, owner C)

Build against `src/mock/` (a JSON fixture server, or MSW) on Day 0–1, then switch the base URL.

| View | Components |
|---|---|
| **Devices & sync** | One card per device: online toggle, outbox depth, last sync, shard counts. Gateway card: server point count, **audit (0 private / 0 PII)** in green. Activity feed (merged decision logs + sync events). |
| **Memory & search** | Device selector, search box → results with shard badge (private/mutable/mirror), status badge, dense score, latency ms, "answered locally / escalated". Memory table per shard. **History slider** (P1). "Naive merge vs Smaran" toggle (P1). |
| **Conflicts & decisions** | Contested groups side by side (text, device, vv) + **Resolve** buttons. Decision log table: by / residency / criticality / confidence / reason. |

Required states: empty, loading, device unreachable (red card, no crash).

---

## 5. Classifier track (owner D, helped by C on Day 0–1)

1. **Label guide first (30 min):** one page with a definition and 3 examples per class. `private` = names/phones/personal/HR; `sync` = machine facts, fixes, statuses useful to others; `drop` = chit-chat, "ok", duplicates of the manual. Criticality 0/1/2 with examples.
2. **Data:** `ml/data/gen_notes.py` produces 200 template notes (machines × symptoms × fixes; plus personal notes with synthetic numbers; plus chit-chat). C + D hand-write 100.
3. **Test set** = 60 of the hand-written notes, **labelled independently by C and D** → Cohen's kappa (`sklearn.metrics.cohen_kappa_score`). If kappa < 0.7, tighten the guide and relabel.
4. **Baselines on the test set (Day 1):** rules only → LogReg on bge-small → Laya zero-shot (P2, 1-hour cap to get it running at all).
5. **Laya fine-tune: P2, 3-hour hard cap, only if Day 1 gates are green.** Ship whichever scores highest. Publish every number, including failures.
6. README table: accuracy + macro-F1 for residency, accuracy for criticality, kappa.

---

## 6. Schedule (corrected dates, gates at end of each day)

**Roles:** A = edge core · B = sync & cloud · C = dashboard · D = classifier, bench, demo.

| Day | A · Edge core | B · Sync & cloud | C · Dashboard | D · Classifier & demo | Gate |
|---|---|---|---|---|---|
| **Fri 25 (tonight, ~4 h)** | **Spike, 1 h cap** (section 9 checklist). Then `store.py` + `embed.py` + `setup_models.py` | Repo skeleton, `backend/common/schema.py`, Docker Qdrant up, **freeze the contracts in section 3 together** | Vite + Tailwind + shadcn shell, mock API from section 3.2 | Label guide, `gen_notes.py`, start hand-writing | Spike passes on **both** Windows laptops; contracts committed |
| **Sat 26** | Hybrid search (4.3), outbox + crash recovery, `/notes` `/search` `/state` `/online` | **Resolver + tests green by 4 pm**, then gateway `/sync` (idempotent) | Memory & search view, then Devices & sync view (mock) | 300 notes labelled, kappa, LogReg baseline → `backend/device/classifier.py` | Offline write+search works end to end on one device; resolver property test passes |
| **Sun 27** | Router wired (rules → clf → dedup), mirror ingest + local resolve, cloud escalation, idle `optimize()` | `/changes`, contested flow, `/resolve`, `/audit`, `/stats`; device pull | Conflicts & decisions view; **3 pm: wire all views to real APIs** | `scripts/demo.py reset <beat>` + seed data; `bench.py` latency + 5-device sim | **Full story runs once → FEATURE FREEZE (Sun night)** |
| **Mon 28** | Bug bash (demo-blocking only), crash test | Duplicate-send test, kill-mid-sync test | Polish, empty/error states | 10 rehearsal runs logged; bench: bandwidth, conflict accuracy, audit; README draft; **backup video take tonight** | 10 runs logged; backup video exists |
| **Tue 29** | Fix blockers until 2 pm, then stop | Same | Screenshots, README images | **Final video after 2 pm**, README numbers | Video + README done |
| **Wed 30** | — | — | — | **Submit by noon**; posts | Submitted |

**Swarming rules (unchanged in spirit):** A's spike > 1 h → B joins and asks in the Qdrant mentor channel. Resolver not green by 4 pm Sat → A joins after hybrid search. Views not wired by 3 pm Sun → D joins after `demo.py`. Auto-sync shaky Sun night → the demo uses the **Sync now** button.

---

## 7. Priority tiers (what gets cut, in order)

- **P0: never cut** (the PS3 answer): 3 shards · hybrid search · offline flag · PII rules + LogReg · outbox · idempotent `/sync` · resolver + contested + resolve · `/changes` → mirror · 3 views (basic) · audit · `demo.py reset` · README with latency + conflict accuracy + audit.
- **P1: cut from the bottom if Sunday is late:** history slider · naive-merge side-by-side · criticality-first visible in the activity feed · mirror dedup · cloud escalation · crash test on video · 5-device sim · bandwidth metric · kappa.
- **P2: only with green gates or a later deadline:** Laya zero-shot/fine-tune · partial snapshots for mirror refresh (`snapshot_manifest` + `/snapshot/partial/create` + `update_from_snapshot`) · full Docker Compose · everything in the proposal's "Future scope".

---

## 8. Benchmarks (`bench/bench.py`, owner D)

| Metric | Method | Target |
|---|---|---|
| Search latency p50/p95 | 1,000 queries over ~2k seeded memories, device offline, `time.perf_counter` around `search()` excluding embedding, then also including it; report both | < 20 / 50 ms (search only) |
| Residency accuracy | Section 5 table | Report all |
| Conflict accuracy | 50 scripted cases; Smaran resolver vs `bench/naive_merge.py` (latest wall-clock / top score wins, with injected clock skew) | Resolver 100%; show naive failures |
| Convergence | 1,000 runs × 5 simulated replicas; random offline edits, delivery order, duplicates; assert identical live sets and no lost concurrent version | 1,000/1,000 |
| Bandwidth | 500-note script: bytes sent by Smaran vs sync-everything (gateway `/stats`) | ≥ 40% fewer |
| Privacy | `/audit` after the demo run | 0 / 0 |

---

## 9. Day-0 spike checklist (A, 1 hour, on each Windows laptop)

```bash
python -m venv .venv && .venv/Scripts/activate
pip install qdrant-edge-py==0.8.0 fastembed qdrant-client fastapi uvicorn scikit-learn hypothesis
docker run -d -p 6333:6333 --name qdrant qdrant/qdrant
```
Tick each:
- [ ] `EdgeShard.create` with `dense` (384, cosine) + `bm25` (sparse, IDF) → upsert 3 points → `close()` → `EdgeShard.load()` → points still there
- [ ] `Bm25(...).embed_document/embed_query` + sparse query returns hits
- [ ] `Prefetch` ×2 + `Fusion.Rrf(k=60)` returns fused results with a `must_not status=superseded` filter
- [ ] `set_payload` updates a status and the filter respects it
- [ ] String UUID point ids work (`str(uuid5(...))`)
- [ ] FastEmbed bge-small loads with `local_files_only=True` and Wi-Fi off
- [ ] qdrant-client can create the matching server collection and accept a device-made BM25 sparse vector
- [ ] *(Optional, 15 min)* server shard snapshot → `EdgeShard.unpack_snapshot` → `load`

Any failing box → post in the Qdrant mentor channel within the hour, pin `qdrant-edge-py` to the version that works.

---

## 10. Demo script (maps to proposal section 8)

**Seed state** (`demo.py reset base`): gateway + server holding CNC-07/CNC-12 manual snippets; both devices synced (mirror full), online.

| Beat | Reset | Actions | On screen |
|---|---|---|---|
| 1 Offline memory | `reset b1` | Toggle A offline → log "CNC-07 bearing replaced, vibration normal" → search "CNC-07 bearing trouble" | Result from *mutable*, ~ms latency, "answered locally" |
| 2 Privacy | `reset b2` | A logs "Call Ravi on 98xxxxxxxx about night shift" | Decision log: `pii_rule → private`; `/audit` = 0 after sync |
| 3 Conflict | `reset b3` | A and B both offline; A: status "running normally", B: "still vibrating at high RPM" → both online | Safety note syncs first; CNC-07 **contested** on both devices + dashboard |
| 4 Belief over time | `reset b4` | Supervisor resolves → drag history slider to 10:05 | Superseded versions keep validity windows; "what A believed at 10:05" |

Video only: naive-merge side-by-side, kill-mid-sync restart, metrics screen.

---

## 11. Risks (updated)

| Risk | Likelihood | Mitigation |
|---|---|---|
| Deadline misread (calendar mismatch, see §0) | **High until confirmed** | Confirm today; the plan compresses by removing Day 4 |
| Edge API differs from docs in 0.8.0 | Low–Med | Day-0 checklist; pin the version; per-shard fusion can fall back to two plain queries + Python RRF |
| Cross-shard ranking feels off | Med | Rank-based RRF across shards; dense-cosine threshold for escalation; tune `k` on 20 queries |
| Resolver/mirror interaction bugs (device vs server status disagree) | Med | Same `themis.py` on both sides; property test; the mirror always overwrites status from the server |
| Classifier weak | Med | PII rules decide privacy; LogReg default; report honestly |
| Two-store write not atomic (outbox + shard) | Low | Outbox-first + startup replay + deterministic ids |
| Windows path/process quirks in demo | Med | `demo.py` in Python (not bash); everything on one laptop; software offline flag |
| Team member unavailable | Med | Contracts in §3 + small modules; daily 15-min sync at 10 am and 9 pm |

---

## 12. Definition of done (submission)

- [ ] `python scripts/demo.py start-all` brings up gateway + 2 devices + dashboard on a clean clone (after `setup_models.py`)
- [ ] 4 live beats each run from their own reset, 10/10 rehearsals logged
- [ ] README: problem → gap table (quoting Qdrant's guide) → architecture → the §8 metrics with real numbers → classifier table + kappa → known limitations → future scope
- [ ] 3-minute video uploaded; backup take kept
- [ ] One full run with Wi-Fi physically off
