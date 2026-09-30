# Smaran architecture and decisions

Smaran is a personal AI that remembers you, keeps working when the internet disappears, acts for you through controlled tools, and reconciles itself when connectivity returns. This document records what was built, why each technology was chosen, what is real and what is simulated, and where the limits are. Numbers come from `bench/` and are in [EDGE_BENCHMARKS.md](EDGE_BENCHMARKS.md) and [BENCHMARKS.md](BENCHMARKS.md).

## 1. Where the research summary was wrong or unsuitable

The attached executive summary was written without reading the repository. Checked against the code and the problem statement (PS3, Qdrant):

| Summary said | Actual repository / PS | Decision |
|---|---|---|
| Smaran has no offline mode, no memory, no sync | It already had three Qdrant Edge shards, hybrid search, a crash-safe outbox, version-vector conflicts, a gateway and a dashboard (45 tests) | Keep the engine. Build the missing layers on top |
| Use Realm, Couchbase, Firestore or PouchDB for offline sync | PS3 requires **Qdrant Edge** on device and **Qdrant Server** in the cloud | Keep Qdrant Edge + Server; sync stays our own outbox and change feed |
| Resolve conflicts with last-write-wins or timestamps | Timestamps trust device clocks and silently drop an edit | Keep version vectors. Concurrent edits are flagged, never guessed. The UI shows a *suggestion*, and the user decides |
| Run a quantised 7B model (LLaMA-2, Mistral) | 7B needs 4 GB or more RAM and is slow on CPU | A 3B model through Ollama (llama.cpp). Measured 0.5 s per answered question on this laptop |
| Healthcare worker story | The brief asks for a student or developer story | Personal companion for a student running a final-year project |
| Federated learning, PySyft, LangChain, LlamaIndex | None of it makes the PS visible; all add weight | Not built |

## 2. System

```
              ┌──────────────────────────── DEVICE (works with the link off) ───────────────────────────┐
 you ──chat──▶│ Companion  = agent loop                                                                  │
              │   plan ──▶ retrieve ──▶ route model ──▶ validate ──▶ tool ──▶ verify ──▶ audit          │
              │     │          │            │                          │                                │
              │  rules /   Qdrant Edge   ModelRouter               registered tools only                │
              │  local SLM  hybrid +    local-slm → rules          (read / write / destructive)         │
              │             rerank      (cloud only if allowed)                                         │
              │                                                                                         │
              │  Krypta (private, no sync path)   Hermes (unsynced writes)   Agora (cloud mirror)       │
              │  SQLite: outbox · Krypta journal · encrypted chat log · encrypted audit log             │
              └───────────────┬─────────────────────────────────────────────────────────────────────────┘
                              │ link up: idempotent push (criticality first) + change-feed pull
                       ┌──────▼──────────────┐
                       │ Gateway: Themis      │  version vectors, contested / superseded
                       │ Qdrant Server        │  fleet collection + campus knowledge
                       └─────────────────────┘
```

Code map: `backend/companion/` (agent), `backend/device/` (shards, outbox, Hermes, Argus), `backend/gateway/` (ingest, Themis, change feed), `backend/common/themis.py` (conflict logic shared by both sides).

## 3. Memory

Each memory is a Qdrant Edge point with a dense vector (bge-small, 384-d), a BM25 sparse vector and a payload.

| Layer | What goes in | `kind` values | Behaviour |
|---|---|---|---|
| Episodic | What happened: lectures, meetings, tasks | `event`, `note`, `task` | Ranked by recency |
| Semantic | Facts and decisions about projects | `fact`, `decision` | A `slot` (for example `decision:database`) makes a later "we switched to MySQL" a new *version* of the same fact |
| Procedural | Preferences and habits | `preference` | Persist until contradicted |

Payload fields: `memory_type`, `subject`, `slot`, `importance`, `confidence`, `entities`, `tags`, `source`, `vv` (version vector), `device_id`, `valid_from`, `status` (`current`, `superseded`, `contested`), `residency`, `decision` (why it was placed where it was).

**Write pipeline**: utterance → sentence split → drop questions and greetings → classify (decision, task, schedule fact, preference, fact, episode) → importance score → Argus decides residency (PII rules first, sensitive topics private) → outbox first, then shard → embed and index.

**Read pipeline**: query understanding (kind hints, subject, soft time window) → Qdrant Edge dense + BM25 fused with RRF → rerank with `0.45·meaning + 0.20·rrf + 0.10·recency + 0.10·importance + 0.15·metadata` → context assembly under a character budget → model router. Task questions also read the exact task list (structured retrieval) and hand it to the model as an authoritative block; a model answer that leaves a task out is rejected in favour of the exact list.

Retrieval quality on 25 paraphrased queries over 40 memories (`python -m bench.personal_eval`, `bench/results/personal_eval.json`): see BENCHMARKS. The set was used while fixing extraction bugs, so it is a development set, not a held-out one.

## 4. AI models and routing

| Job | Model | Size | Runtime | Why | Fallback |
|---|---|---|---|---|---|
| Embeddings | bge-small-en-v1.5 (Qdrant's ONNX export) | about 65 MB | FastEmbed / ONNX Runtime, CPU | Small, offline, English retrieval quality; already the repo's choice | `HashEmbedder` in tests only |
| Answer synthesis, planning fallback | `llama3.2:latest` (3B) | about 2 GB | Ollama (llama.cpp), localhost | Already on the dev machine; answers grounded questions in about 0.5 s. `llama3.2:1b` was tried and rejected: it said "I don't have that in memory" for memories it had been given | Rules compose the answer from retrieved memory, no model |
| Cloud enhancement | any OpenAI-compatible endpoint, set by env | n/a | HTTPS | Optional; off unless `CLOUD_LLM_*` is set | Local route |

`ModelRouter` order: local SLM, then rules. Cloud is used only if it is configured, the device is online, the caller asked for it, **and no private (Krypta) memory is in the context**. Every answer records its route, model, latency, reason and any route that failed first. Two guards run on model output: citations must point at retrieved memories, and a list answer must mention every item of the exact list.

Not chosen: WebLLM / Transformers.js (the stack is Python; would mean a second runtime), MLX (Apple only), ExecuTorch and MediaPipe (mobile SDKs, no mobile app here), Phi/Gemma/Qwen (no advantage over the Llama 3.2 3B that is installed; not benchmarked here). No claim is made about phones.

## 5. Agent

`plan → retrieve → route → validate → execute → verify → audit`. Planners produce `{tool, args}` only:

- Rules (default, instant): remember, remind, add task, finish task, cancel task, summarise, sync, connectivity.
- Local SLM: only when a sentence starts with an imperative the rules do not know. Its JSON goes through the same validator as everything else.

Validator: the tool must be registered, arguments must satisfy the pydantic schema, and risk is checked (`read` free, `write` audited, `destructive` requires the user's confirmation). Tools: `search_memory`, `list_tasks`, `summarize_project`, `check_connectivity`, `store_memory`, `create_task`, `set_reminder`, `update_task`, `sync_now`, `cancel_task`. Nothing deletes: cancelling writes a new version and the old one is kept, marked superseded.

Idempotency: a request id plus action index is stored in the audit table; a retry returns the earlier result. Tasks are keyed by title, so creating the same task twice is a no-op. Verification reads the write back from the shard and the outbox. Every action is one audit row (arguments and result encrypted).

## 6. Offline and sync

Everything in section 2 above the gateway line works with no network. Tests use a client whose every call raises, and a restart while offline.

Sync: local write → outbox row first (SQLite, WAL) → shard write → link up → push in batches, safety/deadline items first → gateway ignores op ids it has seen (idempotent) → Themis merges → pull the change feed into Agora → re-run Themis locally. Versioning uses version vectors (`vv`), not clocks. Retry uses exponential backoff up to 30 s. Two devices editing the same slot while apart produce two maximal versions, both marked `contested` on both devices and on the server; nothing is dropped. Resolution writes a new version that supersedes both. The dashboard shows a suggested winner (the later edit by its own clock) labelled as a suggestion because clocks can be wrong.

CRDTs were evaluated and not used: the conflicting data is a single fact per slot, not collaborative text, and a person should decide.

## 7. Privacy and security (what is and is not claimed)

- Sensitive text (phone numbers, emails, ID numbers by rule; salary, health, credentials by topic) goes to Krypta, which has no sync code path. The gateway re-checks and rejects such payloads. A cloud audit counts private records (0 in the story).
- Chat history and audit rows are encrypted at rest with AES-256-GCM. The key is wrapped by Windows DPAPI where available, otherwise a mode-0600 file.
- **Not** encrypted: the Qdrant Edge shard files and the SQLite outbox/journal. Use full-disk encryption. There is no per-user authentication: services bind to 127.0.0.1.
- Private memory is never placed in a cloud prompt.
- Action authorisation is the tool risk policy above; there are no user accounts.

## 8. Real versus simulated

| Real | Simulated |
|---|---|
| Qdrant Edge shards, dense + BM25 hybrid search, embeddings on CPU | The two "devices" are two local processes (Phone and Laptop) on one machine |
| Local SLM inference through Ollama on this machine | "Offline" is a software link switch, not a radio off; the device stops calling the gateway and Hermes stops |
| Outbox, retries, idempotent replay, version vectors, conflict detection | Cloud is Qdrant in embedded mode unless Docker is running; latency to a real WAN is not measured |
| Agent tools, validator, confirmation, audit, encrypted chat log | Cloud model route is coded and unit-tested with a fake endpoint, never run against a real provider here |
| Restart while offline keeps memory | Federated learning, multi-tenant scale, mobile hardware acceleration: not built |

## 9. Known limitations

- Each Edge shard pre-allocates disk: about 620 MB for three shards with 100 memories in the benchmark run. Small memories do not make a small footprint.
- Opening a device with the link off takes several seconds (3 shards, IDF table rebuild, crash recovery), see EDGE_BENCHMARKS.
- Extraction is rules-based English. It handles the demo grammar; free-form text yields fewer structured memories.
- The 3B model sometimes phrases things oddly; the guards catch missing tasks and bad citations, not every wording error.
- Retrieval set is small and author-labelled.
- No mobile build, no real second machine, no authentication.
