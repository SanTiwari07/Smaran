# ΣMARAN

**Smaran: *aletheia at the edge.*** Memory that doesn't forget, and doesn't lie.

An offline-first memory layer for edge AI, built on **Qdrant Edge** (Code Cubicle 6.0, PS3). It decides what a device keeps private, what it shares with the cloud, and which version of a fact to believe when devices disagree.

## How it works

| Component | Role |
|---|---|
| **Krypta** | Keeps what's private. This shard has no sync code path, so its contents never leave the device. |
| **Hermes** | Carries everything else to the gateway when the link returns, through a crash-safe outbox that sends the most critical items first. |
| **Agora** | Shares what the fleet knows: a mirror of Qdrant Server on every device. |
| **Themis** | Decides what's true. Version vectors tell *newer* from *concurrent*, so conflicts are flagged, never guessed. |

## Results

All numbers are measured. Methodology and raw output are in [docs/BENCHMARKS.md](docs/BENCHMARKS.md).

| Metric | Result |
|---|---|
| Offline hybrid search, 2,000 memories, 3 shards | **3.9 ms p50 / 5.6 ms p95** (target < 20 / 50 ms) |
| Conflict handling, 50 cases with clock skew | **Themis 50/50** vs naive last-writer-wins 13/50 |
| 5-device convergence, 1,000 random runs | **1000/1000** identical replicas, **0** concurrent edits lost |
| Residency classifier, 60 held-out hand-written notes | **98.3%** accuracy; safety-critical recall 0.9 |
| Personal data on the server after the demo | **0** private records, **0** PII matches |
| Bandwidth vs sync-everything | 38.2% saved (target 40%, missed) |
| Demo rehearsals (4 beats each, automated checks) | **10/10** passed |

## Requirements

- Python 3.10+
- Node.js 18+
- Docker Desktop (optional). It runs the real Qdrant Server; without it, use embedded mode.

## Setup

One-time install. The commands use Windows paths; on macOS and Linux, replace `.venv/Scripts/python` with `.venv/bin/python`.

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r backend/requirements.txt
.venv/Scripts/python scripts/setup_models.py
npm --prefix frontend install
```

`setup_models.py` downloads about 65 MB of models once. After that, everything works offline.

Configuration is optional. Copy `.env.example` to `.env` to override defaults such as `QDRANT_URL`.

## Running

Start the whole stack:

```bash
.venv/Scripts/python scripts/demo.py start-all                     # Qdrant Server via Docker
.venv/Scripts/python scripts/demo.py start-all --qdrant embedded   # no Docker needed
```

Then open **http://localhost:5173**.

| Service | Address |
|---|---|
| Dashboard (Olympus) | http://localhost:5173 |
| Gateway | http://127.0.0.1:8000 |
| Device A | http://127.0.0.1:8001 |
| Device B | http://127.0.0.1:8002 |
| Qdrant Server (Docker) | http://127.0.0.1:6333 |

Each backend service serves interactive API docs at `/docs`, for example http://127.0.0.1:8001/docs.

Other commands:

```bash
.venv/Scripts/python scripts/demo.py status                 # health of every service
.venv/Scripts/python scripts/demo.py stop-all               # stop everything
.venv/Scripts/python scripts/demo.py wipe                   # delete runtime/ state (stop services first)
.venv/Scripts/python scripts/demo.py start-all --no-frontend
```

Service output goes to `logs/<service>.out`.

## Demo

```bash
.venv/Scripts/python scripts/demo.py reset b1        # known state for a beat: base, b1..b4
.venv/Scripts/python scripts/demo.py play b3         # run a beat and check it
.venv/Scripts/python scripts/demo.py rehearse --runs 10
```

The presenter script is in [docs/DEMO.md](docs/DEMO.md).

## Development and testing

```bash
.venv/Scripts/python -m pytest                 # 30 tests, about 25 s, no model files needed
.venv/Scripts/python -m bench.bench            # benchmarks, written to docs/BENCHMARKS.md
.venv/Scripts/python -m ml.train               # retrain the classifier, written to ml/artifacts/
npm --prefix frontend run dev:mock             # dashboard on mock data, no backend needed
```

For logs and tracing, see [docs/DEBUGGING.md](docs/DEBUGGING.md).

## Troubleshooting

**`start-all` says "already started (runtime/pids.json exists)".** A previous run did not shut down cleanly. Run `stop-all`, then `start-all` again.

**Gateway fails to start with a Qdrant `timed out` error in `logs/gateway.out`.** The Qdrant container was still starting when the gateway connected, which is common right after Docker Desktop launches. Wait until `curl http://127.0.0.1:6333/readyz` reports that all shards are ready, then run `stop-all` and `start-all`.

**`UserWarning: Qdrant client version ... is incompatible with server version ...`.** The Python client is newer than the pinned server image (`qdrant/qdrant:v1.15.4` in `infra/docker-compose.yml`). The demo works despite the warning. Upgrade the image tag to remove it.

**Docker is not available.** Use `start-all --qdrant embedded`.

## Project layout

| Folder | Contents |
|---|---|
| `backend/common/` | Shared by all services: `themis.py` (resolver), `pii.py`, `schema.py`, `config.py`, `log.py` |
| `backend/device/` | Edge device: shards, embeddings, Argus router and classifier, search, outbox, Hermes sync |
| `backend/gateway/` | Sync gateway: idempotent ingest, Themis, change feed, audit |
| `backend/tests/` | pytest: Themis property tests, PII, store, end-to-end PS3 story |
| `frontend/` | React dashboard (Olympus): Devices and sync, Memory and search, Conflicts and decisions |
| `ml/` | Labelled notes, training and evaluation for the residency classifier |
| `bench/` | Benchmarks and the 5-device simulation |
| `seed/` | Fleet seed data |
| `scripts/` | Model setup and the demo controller |
| `infra/` | Docker Compose for Qdrant Server |
| `docs/` | [Plan](docs/IMPLEMENTATION_PLAN.md), [Proposal](docs/PROPOSAL.md), [Demo](docs/DEMO.md), [Debugging](docs/DEBUGGING.md), [Benchmarks](docs/BENCHMARKS.md) |

## Known limitations

- Label agreement (kappa) is not measured yet. A second person needs to label `ml/data/handwritten_notes.csv` (columns `residency_2`, `criticality_2`).
- The classifier test set is small (60 notes), and the rule combining model and keyword criticality was chosen after seeing those results.
- Laya, the decision model from the proposal, is not integrated. It would sit behind the same `ResidencyClassifier` interface.
- Mirror refresh uses the gateway's change feed, not Qdrant partial snapshots.
- Each Edge shard pre-allocates tens of MB on disk for its write-ahead log and segments.
