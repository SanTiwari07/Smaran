# ΣMARAN

[![CI](https://github.com/SanTiwari07/Smaran/actions/workflows/ci.yml/badge.svg)](https://github.com/SanTiwari07/Smaran/actions/workflows/ci.yml)

**Smaran: *aletheia at the edge.*** Memory that doesn't forget, and doesn't lie.

> Everyone shows that a device can remember. **Smaran keeps that memory correct and private when devices go offline and disagree.** It runs on **Qdrant Edge**, syncs to a real **Qdrant Server**, and every claim below is measured.

Code Cubicle 6.0 · Problem Statement 3 (AI-Powered Edge Memory & Intelligence Platform).

## The moment

Two maintenance technicians report opposite things about machine CNC-07 while the factory Wi-Fi is down. When the devices reconnect, a timestamp-based sync (Qdrant's reference pattern, most sync databases, most hackathon entries) keeps one report and silently drops the other. Smaran flags both, lets the shift supervisor decide, and keeps the history of what each device believed.

## How it works

| Component | Role |
|---|---|
| **Krypta** | Keeps what's private. This Edge Shard has no sync code path, so its contents never leave the device. |
| **Hermes** | Carries everything else to the gateway when the link returns, through a crash-safe outbox that sends the most critical items first. |
| **Agora** | Shares what the fleet knows: a mirror of Qdrant Server on every device. |
| **Themis** | Decides what's true. Version vectors tell *newer* from *concurrent*, so conflicts are flagged, never guessed. |
| **Argus** | Decides where each note lives: PII rules first (no model can override them), then a learned classifier, then dedup against fleet knowledge. Every decision shows its reason. |

```mermaid
flowchart LR
  subgraph DEV["Edge device (one process, works fully offline)"]
    N["Technician note / query"] --> E["Embed on device<br/>bge-small (dense) + Qdrant Edge Bm25 (sparse)"]
    E --> R{"Argus<br/>PII rules → classifier → dedup"}
    R -- private --> K[("Krypta<br/>Edge Shard, no sync path")]
    R -- sync --> H[("Hermes<br/>Edge Shard")]
    R -- sync --> O[["SQLite outbox<br/>criticality-first, crash-safe"]]
    A[("Agora<br/>fleet mirror Edge Shard")]
    S["Hybrid search<br/>dense + BM25, device-wide IDF, RRF"] --> K & H & A
  end
  O == "online: idempotent batches, float16 vectors" ==> G["Sync gateway<br/>Themis · change feed · privacy audit"]
  G --> Q[("Qdrant Server")]
  Q -- "change feed" --> A
  D["Olympus dashboard"] --- DEV
  D --- G
```

## Qdrant doing the work

| Step | Qdrant feature | Where |
|---|---|---|
| On-device store | `qdrant-edge-py` `EdgeShard.create/load`, three shards, named `dense` + sparse `bm25` vectors | `backend/device/store.py` |
| Keyword vectors | Qdrant Edge built-in `Bm25` (token ids match Qdrant Server's BM25) | `backend/device/embed.py` |
| Hybrid query | `QueryRequest` nearest-neighbour on each vector, fused with RRF across shards; device-wide IDF | `backend/device/search.py` |
| Filters | `Filter` / `FieldCondition` / `MatchValue` on keyword and integer payload indexes | `store.py` |
| Maintenance | `optimize()` on an idle timer (Edge has no background optimizer) | `backend/device/hermes.py` |
| Mutations | `UpdateOperation.upsert_points`, `set_payload` for status transitions | `store.py` |
| Edge → server | Outbox → gateway → `qdrant-client` upsert into a single-shard collection with payload indexes | `backend/gateway/server.py` |
| Server-side search | Prefetch dense + BM25 (IDF modifier), `FusionQuery(RRF)` for cloud escalation | `server.py` |

## Results

All numbers are measured. Methodology and raw output are in [docs/BENCHMARKS.md](docs/BENCHMARKS.md).

| Metric | Result |
|---|---|
| Offline hybrid search, 2,000 memories, 3 shards | **3.0 ms p50 / 4.0 ms p95** (target < 20 / 50 ms) |
| Retrieval quality, 40 golden queries | hybrid **hit@5 0.975**, hit@1 0.875 · dense-only hit@5 0.95 · BM25-only hit@5 0.95 |
| Conflict handling, 50 cases with clock skew | **Themis 50/50** vs naive last-writer-wins 13/50 |
| 5-device convergence, 1,000 random runs | **1000/1000** identical replicas, **0** concurrent edits lost |
| Residency classifier, 60 held-out hand-written notes | **98.3%** accuracy; safety-critical recall 0.9 |
| Personal data on Qdrant Server after the demo | **0** private records, **0** PII matches |
| Bandwidth vs syncing every note | **85.7% saved** (selection alone: 38.2%, which missed the 40% target; float16 vectors do the rest) |
| Crash between "gateway stored" and "device acked" | 3 of 3 ops resent, **0** duplicate memories, fleet mirror rebuilt |
| Demo rehearsals on the real Qdrant Server v1.19.1 | **10/10** (beats 1–4) · **10/10** (beat 5, the crash) |

## PS3 checklist

| PS3 goal | Where Smaran shows it |
|---|---|
| Searchable semantic memory on an edge device | Three Qdrant Edge shards per device (beat 1) |
| Low-latency vector **and hybrid** search without network | Dense + BM25 with RRF, device offline, ~3 ms (beat 1, latency benchmark) |
| Dynamically decide what stays local and what syncs | Argus, with a "Why here" reason on every memory (beat 2) |
| Intermittent connectivity, keep working offline | Link switch, SQLite outbox, crash recovery (beats 1, 3, 5) |
| Sync with **Qdrant Server** when connectivity returns | Gateway → Qdrant Server in Docker; points visible at `localhost:6333/dashboard` (beat 3) |
| Evolving memory, updates, conflicting information | Themis version vectors, supervisor resolution, Chronos history (beats 3, 4) |
| UI for memory, search results, sync status, activity | Olympus: Devices and sync · Memory and search · Conflicts and decisions |
| A meaningful edge-to-cloud workflow, not just a local vector DB | Agora fleet mirror, change feed, cloud escalation, privacy audit on the server |

## Prove it in 60 seconds

```bash
.venv/Scripts/python -m pytest                                    # 45 tests: Themis properties, PII, sync, crash recovery, float16, retrieval
.venv/Scripts/python -m bench.bench conflicts convergence          # 50/50 vs 13/50; 1000/1000 converged
.venv/Scripts/python scripts/demo.py play b3                      # live conflict on the running stack, with checks
.venv/Scripts/python scripts/demo.py play b5                      # crash mid-sync, restart, 0 duplicates
```

`play` needs the stack running (`start-all`, below). The first two need nothing but the Python environment.

## Requirements

- Python 3.10+ (CI runs 3.13)
- Node.js 18+ (CI runs 22)
- Docker Desktop, for the real Qdrant Server (`qdrant/qdrant:v1.19.1`, matching the pinned `qdrant-client==1.19.1`). Without Docker, use embedded mode.

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
| Qdrant Server (Docker) | http://127.0.0.1:6333 (web UI at `/dashboard`) |

Each backend service serves interactive API docs at `/docs`, for example http://127.0.0.1:8001/docs.

Other commands:

```bash
.venv/Scripts/python scripts/demo.py status                 # health of every service
.venv/Scripts/python scripts/demo.py kill A                 # hard-kill device A (no clean shutdown)
.venv/Scripts/python scripts/demo.py start A                # start device A again
.venv/Scripts/python scripts/demo.py stop-all               # stop everything
.venv/Scripts/python scripts/demo.py wipe                   # delete runtime/ state (stop services first)
.venv/Scripts/python scripts/demo.py start-all --no-frontend
```

Service output goes to `logs/<service>.out`.

## Demo

```bash
.venv/Scripts/python scripts/demo.py reset b1        # known state for a beat: base, b1..b5
.venv/Scripts/python scripts/demo.py play b3         # run a beat and check it
.venv/Scripts/python scripts/demo.py rehearse --runs 10                        # beats 1-4
.venv/Scripts/python scripts/demo.py rehearse --runs 10 --beats b1 b2 b3 b4 b5 # with the crash beat
```

Every rehearsal is logged to `logs/rehearsal.log` with the Qdrant target and git commit. The presenter script is in [docs/DEMO.md](docs/DEMO.md).

## Development and testing

```bash
.venv/Scripts/python -m pytest                 # 45 tests, no model files or Docker needed
.venv/Scripts/python -m bench.bench            # benchmarks, written to docs/BENCHMARKS.md
.venv/Scripts/python -m ml.train               # retrain the classifier, written to ml/artifacts/
npm --prefix frontend run dev:mock             # dashboard on mock data, no backend needed
```

For logs and tracing, see [docs/DEBUGGING.md](docs/DEBUGGING.md).

## Troubleshooting

**`start-all` says "already started (runtime/pids.json exists)".** A previous run did not shut down cleanly. Run `stop-all`, then `start-all` again.

**Gateway fails to start with a Qdrant `timed out` error in `logs/gateway.out`.** The Qdrant container was still starting. Wait until `curl http://127.0.0.1:6333/readyz` says all shards are ready, then run `stop-all` and `start-all`. The gateway finishes any collection or index setup a timed-out start left behind.

**Upgrading from the old `qdrant/qdrant:v1.15.4` image.** The compose file now uses fresh volumes (`qdrant_storage`), because Qdrant can't skip minor versions when upgrading storage. The old `qdrant_data` volume held demo data only and can be removed with `docker volume rm infra_qdrant_data`.

**Docker is not available.** Use `start-all --qdrant embedded`.

## Project layout

| Folder | Contents |
|---|---|
| `backend/common/` | Shared by all services: `themis.py` (resolver), `pii.py`, `schema.py`, `vectors.py` (float16 transport), `config.py`, `log.py` |
| `backend/device/` | Edge device: shards, embeddings, Argus router and classifier, search, outbox and Krypta journal, Hermes sync |
| `backend/gateway/` | Sync gateway: idempotent ingest, Themis, change feed, audit |
| `backend/tests/` | pytest: Themis properties, PII, store, float16, retrieval, end-to-end PS3 story, crash recovery |
| `frontend/` | React dashboard (Olympus): Devices and sync, Memory and search, Conflicts and decisions |
| `ml/` | Labelled notes, training and evaluation for the residency classifier |
| `bench/` | Benchmarks, the 5-device simulation, the golden retrieval queries |
| `seed/` | Fleet seed data |
| `scripts/` | Model setup and the demo controller |
| `infra/` | Docker Compose for Qdrant Server |
| `docs/` | [Plan](docs/IMPLEMENTATION_PLAN.md), [Proposal](docs/PROPOSAL.md), [Demo](docs/DEMO.md), [Debugging](docs/DEBUGGING.md), [Benchmarks](docs/BENCHMARKS.md), [Audit and plan](docs/AUDIT_AND_PLAN.md) |

## Known limitations

- Label agreement (kappa) was measured against an AI second labeller (Claude), not a human: residency 1.000, criticality 0.661 (below our 0.7 target; disagreements are all one level apart). A human second labeller has not yet labelled `ml/data/handwritten_notes.csv`. See [BENCHMARKS](docs/BENCHMARKS.md).
- The classifier test set is small (60 notes), and the rule combining model and keyword criticality was chosen after seeing those results.
- The 40 golden retrieval queries were written and labelled by the team against a known corpus; treat those numbers as indicative.
- Convergence is measured for 5 simulated devices; larger fleets are a design claim, not a measurement.
- No device signing, authentication or TLS yet: services bind to 127.0.0.1. Planned: Ed25519 device keys, mTLS, OIDC for supervisors.
- Mirror refresh uses the gateway's change feed, not Qdrant partial snapshots.
- Qdrant Edge keeps recent writes in memory until a flush (1–2 s on the dev laptop), so SQLite is the durable log: the outbox and a local Krypta journal are replayed on start, and Agora is re-pulled after an unclean shutdown.
- Each Edge shard pre-allocates tens of MB on disk for its write-ahead log and segments.

## Credits

Built by the team on these open-source projects and models (hackathon rules require crediting third-party work):

| Project | Licence | Used for |
|---|---|---|
| [Qdrant Edge](https://qdrant.tech/documentation/edge/) (`qdrant-edge-py`) | Apache-2.0 | On-device vector search, Edge Shards, built-in BM25 |
| [Qdrant](https://github.com/qdrant/qdrant) server and [`qdrant-client`](https://github.com/qdrant/qdrant-client) | Apache-2.0 | Fleet collection, server-side hybrid search |
| [FastEmbed](https://github.com/qdrant/fastembed) | Apache-2.0 | On-device ONNX embeddings |
| [BAAI/bge-small-en-v1.5](https://huggingface.co/BAAI/bge-small-en-v1.5) (Qdrant's quantized ONNX export) | MIT | Dense 384-d embeddings |
| [ONNX Runtime](https://github.com/microsoft/onnxruntime) | MIT | Model inference (via FastEmbed) |
| [scikit-learn](https://scikit-learn.org/) | BSD-3-Clause | Residency / criticality classifier |
| [NumPy](https://numpy.org/) | BSD-3-Clause | float16 vector transport |
| [FastAPI](https://fastapi.tiangolo.com/), [Pydantic](https://docs.pydantic.dev/) | MIT | Device and gateway APIs |
| [Uvicorn](https://www.uvicorn.org/), [HTTPX](https://www.python-httpx.org/), [python-dotenv](https://github.com/theskumar/python-dotenv) | BSD-3-Clause | Serving, HTTP client, configuration |
| [pytest](https://pytest.org/) | MIT | Tests |
| [Hypothesis](https://hypothesis.works/) | MPL-2.0 | Property tests for Themis |
| [React](https://react.dev/), [Vite](https://vite.dev/), [Tailwind CSS](https://tailwindcss.com/) | MIT | Dashboard |
| [TypeScript](https://www.typescriptlang.org/) | Apache-2.0 | Dashboard |

Design references: Qdrant's [Edge synchronization guide](https://qdrant.tech/documentation/edge/edge-synchronization-guide/) (the mutable + mirror shard pattern we extend) and DeCandia et al., *Dynamo* (SOSP 2007), for version vectors. The maintenance notes and manuals in `ml/data/` and `seed/` were written by the team (the training templates are generated by `ml/data/gen_notes.py`); names and phone numbers in them are synthetic.
