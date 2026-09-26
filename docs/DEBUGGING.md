# Debugging guide

## Where things are

| Service | Port | Log (JSON lines) | Raw output | State |
|---|---|---|---|---|
| Gateway | 8000 | `logs/gateway.log` | `logs/gateway.out` | `runtime/gateway/`, Qdrant (`runtime/qdrant-embedded/` or Docker) |
| Device A | 8001 | `logs/device-A.log` | `logs/device-A.out` | `runtime/device-A/` (3 shards + `device.db`) |
| Device B | 8002 | `logs/device-B.log` | `logs/device-B.out` | `runtime/device-B/` |
| Dashboard | 5173 | browser console | `logs/frontend.out` | none |

- `python scripts/demo.py status` checks every `/health` and Qdrant Server.
- Every service has interactive API docs at `/docs` (FastAPI), e.g. http://127.0.0.1:8001/docs.
- `.out` files hold tracebacks. `.log` files hold events.

## Follow one memory end to end

Every memory has an `op_id` like `A-000003`. Search for it across all logs:

```bash
grep -h '"op_id": "A-000003"' logs/*.log
```

You'll see: `decision` (Argus, with its reason) → `synced` (gateway result: applied / stale / duplicate / rejected) → gateway `stored` (with Themis status) → `pulled` on the other device → `conflict` if any.

## Is it the frontend or the backend?

```bash
npm --prefix frontend run dev:mock
```

The dashboard then runs on in-memory mock data (a gold **mock API** badge appears in the header). If the bug still happens, it's in `frontend/`. If not, call the backend directly at `/docs`.

## Reproduce without servers

`app.py` files only parse and call. The logic lives in `backend/device/core.py` and `backend/gateway/core.py`, which tests drive directly (see `backend/tests/conftest.py`: in-memory Qdrant, a hash embedder, and devices wired to the gateway through FastAPI's TestClient). Copy a test from `test_e2e.py` to reproduce a bug in seconds.

## Known pitfalls (all hit during development)

| Symptom | Cause | Fix |
|---|---|---|
| `failed to connect to the docker API … dockerDesktopLinuxEngine` | Docker Desktop not running, or waiting on a prompt in its window | Open Docker Desktop and finish its startup, or use `--qdrant embedded` |
| Old points reappear after a gateway reset (embedded mode) | qdrant-client local mode on Windows restores points after `delete_collection` | Reset deletes points and keeps the collection (`FleetServer.reset`) |
| Device reset takes ~15 s | Deleting shard folders is slow on Windows once shards were used | Reset deletes points instead (`Store.clear`) |
| `There is not enough space on the disk` / `Can't init WAL` | Each Edge shard pre-allocates tens of MB | Tests delete shards after each test; run `scripts/demo.py wipe` for old runtime state |
| Every HTTP call from a script takes ~0.2 s | Creating a new httpx client per call builds an SSL context | Reuse one `httpx.Client` |
| A fresh note ranks below old manuals | Per-shard BM25 IDF penalised small shards | Fixed: device-wide IDF (`Store.idf_query`) |
| `Embedding model not found in models/` | Model not downloaded | `python scripts/setup_models.py` once, with internet |
| Shard config errors after pulling new code | Shards on disk were made with an older config | `scripts/demo.py stop-all`, `scripts/demo.py wipe`, `start-all` |

## Useful one-liners

```bash
curl -s localhost:8001/state | python -m json.tool          # device counters
curl -s localhost:8001/outbox | python -m json.tool         # what's waiting to sync, in send order
curl -s localhost:8000/contested | python -m json.tool      # conflicts on the server
curl -s localhost:8000/audit | python -m json.tool          # privacy audit
curl -s -X POST localhost:8001/sync-now                     # push + pull now
```
