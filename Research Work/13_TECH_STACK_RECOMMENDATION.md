# 13 — Technology Stack Recommendation

← [12 Architecture](12_TECHNICAL_ARCHITECTURE.md) · [Master index](00_MASTER_RESEARCH_INDEX.md) · Next: [14 MVP roadmap](14_MVP_ROADMAP.md)

**RECOMMENDATION: do not change the stack.** It is already built, tested and measured, and it matches what PS3 names. Changes are limited to *running* the pieces we have (Qdrant Server) and *small* additions.

| Layer | Technology | Why selected | Alternatives | Trade-offs | Hackathon feasibility |
|---|---|---|---|---|---|
| **Edge vector engine** | **Qdrant Edge** `qdrant-edge-py==0.8.0` (pinned) | **Mandatory for PS3.** In-process, offline, same engine as the server, built-in BM25 | `qdrant-client` local mode (what AegisEdge uses), sqlite-vec, Chroma, LanceDB, ObjectBox | Beta API, so pin the version; no background optimizer (we schedule `optimize()`); restore-only snapshots | ✅ built |
| Cloud vector DB | **Qdrant Server** `qdrant/qdrant` (Docker) | PS3 names "Qdrant Server"; source of partial snapshots | Qdrant Cloud free tier (needs internet at the venue), embedded mode (not a server) | Docker Desktop on Windows can fail (it did once) | ⚠ run and rehearse now |
| Dense embeddings | FastEmbed `BAAI/bge-small-en-v1.5` (384-d, ONNX, CPU) | Small, fast, offline; Qdrant's own documented Edge path ("On-Device Embeddings") | all-MiniLM-L6-v2, nomic-embed, e5-small | English-centric; Hindi/Hinglish notes are weaker (future: multilingual-e5-small) | ✅ |
| Sparse embeddings | Qdrant Edge built-in `Bm25` with device-wide IDF | Server-compatible token IDs; no extra model | FastEmbed `Qdrant/bm25`, SPLADE, miniCOIL | BM25 needs the IDF handling we added | ✅ |
| Classifier | scikit-learn LogReg on embeddings + PII regex + safety keywords | 98.3% held-out accuracy; trains in seconds; deterministic | Laya (fine-tuned), small LLM zero-shot | Small labelled set (disclosed) | ✅ |
| Device durability | SQLite (WAL) | Crash-safe, zero-ops; the same choice as Qdrant's glasses demo | LMDB, RocksDB, files | Single-writer | ✅ |
| Backend | Python 3.10+ / FastAPI / Uvicorn / Pydantic | The Qdrant Edge Python bindings live here; fast to build | Rust (Edge crate; faster, slower to build), Node | GIL (irrelevant at demo scale) | ✅ |
| Consistency | Themis: pure Python version vectors | Deterministic, testable, shared by device and gateway | CRDT libs (Automerge/Yjs), HLC | Needs human resolution for concurrent facts (**intentional**) | ✅ |
| Frontend | React + Vite + TypeScript (plain CSS "operations console" after the latest commit) | Fast iteration; a mock mode exists | Next.js, Streamlit | — | ✅ |
| Testing | pytest (30 tests) + Hypothesis property tests; benchmark suite; `demo.py rehearse` | Evidence for every claim | — | — | ✅ |
| **CI** | **GitHub Actions: pytest + (optional) bench on push** | Selection by GitHub profile; the rival shows a CI badge | none | ~1 h setup; models needed only for some tests (tests run without model files) | ➕ **add before 30 Sep** |
| Deployment | Local: `scripts/demo.py start-all` (Docker or `--qdrant embedded`) | One command; per-beat resets | Docker Compose for everything | Compose on Windows adds risk | ✅ |
| Monitoring | JSON logs per service; UI activity feed; `demo.py status`; Qdrant Web UI (`:6333/dashboard`) | Visible system activity (a PS3 UI requirement) | Prometheus/Grafana | Overkill for the demo | ✅ (+ open the Qdrant dashboard during the demo) |
| Vector transport | JSON floats → **float16 base64 / binary** | ~5× smaller ops (BENCHMARKS note); turns 38.2% into a clear win | Server-side re-embedding | Minor precision loss (negligible for cosine) | ➕ small change |

## Explicitly rejected additions

| Tech | Reason |
|---|---|
| Ollama / local LLM | Latency, RAM, non-determinism, and not what Qdrant rewards |
| Pathway | A second streaming/retrieval engine; muddies the story; integration risk |
| n8n, Cloudinary, Omnidimension in the live path | Cloud dependencies; off-PS |
| Kubernetes / Kafka | Unnecessary moving parts |
| React Native / Flutter mobile | Rewrite risk with 4 days left |

## Version pins to double-check (RECOMMENDATION)

- `qdrant-edge-py==0.8.0`: keep pinned. Check PyPI for a newer release *only* after the 30 Sep freeze, and don't upgrade before the final unless a bug forces it.
- `qdrant/qdrant` Docker image `v1.15.4` (per README) vs the `qdrant-client` version: the README notes a compatibility warning. Pick one pair, pin both, and document it.
- FastEmbed model cache: verify `HF_HUB_OFFLINE=1` works on the demo laptop with Wi-Fi physically off.
