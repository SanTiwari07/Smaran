# ΣMARAN

**Smaran: *aletheia at the edge.*** Memory that doesn't forget, and doesn't lie.

An offline-first memory layer for edge AI, built on **Qdrant Edge** (Code Cubicle 6.0, PS3). It decides what a device keeps private, what it shares with the cloud, and which version of a fact to believe when devices disagree.

- **Krypta** keeps what's private. That shard has no sync code path.
- **Hermes** carries the rest to the gateway when the link returns: a crash-safe outbox, most critical first.
- **Agora** shares what the fleet knows: a mirror of Qdrant Server on every device.
- **Themis** decides what's true. Version vectors tell *newer* from *concurrent*, so conflicts are flagged, never guessed.

## Results (measured, see [docs/BENCHMARKS.md](docs/BENCHMARKS.md))

| | Result |
|---|---|
| Offline hybrid search, 2,000 memories, 3 shards | **3.9 ms p50 / 5.6 ms p95** (target < 20 / 50 ms) |
| Conflict handling, 50 cases with clock skew | **Themis 50/50** vs naive last-writer-wins 13/50 |
| 5-device convergence, 1,000 random runs | **1000/1000** identical replicas, **0** concurrent edits lost |
| Residency classifier, 60 held-out hand-written notes | **98.3%** accuracy; safety-critical recall 0.9 |
| Personal data on the server after the demo | **0** private records, **0** PII matches |
| Bandwidth vs sync-everything | 38.2% saved (target 40%, missed) |
| Demo rehearsals (4 beats each, automated checks) | **10/10** passed |

## Quick start (Windows, macOS, Linux)

Needs Python 3.10+, Node 18+, and optionally Docker Desktop for the real Qdrant Server.

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r backend/requirements.txt     # macOS/Linux: .venv/bin/python
.venv/Scripts/python scripts/setup_models.py                       # one-time 65 MB download; then works offline
npm --prefix frontend install
```

Run everything (gateway :8000, device A :8001, device B :8002, dashboard :5173):

```bash
.venv/Scripts/python scripts/demo.py start-all                     # Qdrant Server via Docker
.venv/Scripts/python scripts/demo.py start-all --qdrant embedded   # no Docker needed
```

Open **http://localhost:5173**. Stop with `scripts/demo.py stop-all`.

## Demo

```bash
.venv/Scripts/python scripts/demo.py reset b1        # known state for a beat: base, b1..b4
.venv/Scripts/python scripts/demo.py play b3         # run a beat and check it
.venv/Scripts/python scripts/demo.py rehearse --runs 10
```

The presenter script is in [docs/DEMO.md](docs/DEMO.md).

## Develop and test

```bash
.venv/Scripts/python -m pytest                 # 30 tests, ~25 s, no model files needed
.venv/Scripts/python -m bench.bench            # benchmarks -> docs/BENCHMARKS.md
.venv/Scripts/python -m ml.train               # retrain classifier -> ml/artifacts/
npm --prefix frontend run dev:mock             # dashboard on mock data, no backend
```

Each service serves interactive API docs at `/docs` (e.g. http://127.0.0.1:8001/docs). For logs and tracing, see [docs/DEBUGGING.md](docs/DEBUGGING.md).

## Layout

| Folder | What's inside |
|---|---|
| `backend/common/` | Shared by all services: `themis.py` (resolver), `pii.py`, `schema.py`, `config.py`, `log.py` |
| `backend/device/` | Edge device: shards, embeddings, Argus router + classifier, search, outbox, Hermes sync |
| `backend/gateway/` | Sync gateway: idempotent ingest, Themis, change feed, audit |
| `backend/tests/` | pytest: Themis property tests, PII, store, end-to-end PS3 story |
| `frontend/` | React dashboard (Olympus): Devices & sync · Memory & search · Conflicts & decisions |
| `ml/` | Labelled notes, training and evaluation for the residency classifier |
| `bench/` | Benchmarks and the 5-device simulation |
| `seed/`, `scripts/`, `infra/` | Fleet seed data, setup and demo scripts, Docker Compose |
| `docs/` | [Plan](docs/IMPLEMENTATION_PLAN.md) · [Proposal](docs/PROPOSAL.md) · [Demo](docs/DEMO.md) · [Debugging](docs/DEBUGGING.md) · [Benchmarks](docs/BENCHMARKS.md) |

## Known limitations

- The label agreement score (kappa) isn't measured yet. A second person needs to label `ml/data/handwritten_notes.csv` (columns `residency_2`, `criticality_2`).
- The classifier test set is small (60 notes). The rule combining model and keyword criticality was chosen after seeing those results.
- Laya (the proposal's decision model) isn't integrated. It would sit behind the same `ResidencyClassifier` interface.
- Mirror refresh uses the gateway's change feed, not Qdrant partial snapshots.
- Each Edge shard pre-allocates tens of MB on disk (write-ahead log and segments).
