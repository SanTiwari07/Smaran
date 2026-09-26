# 11 — WHAT WE SHOULD NOT BUILD

← [10 WOW features](10_WOW_FEATURES.md) · [Master index](00_MASTER_RESEARCH_INDEX.md) · Next: [12 Architecture](12_TECHNICAL_ARCHITECTURE.md)

Evidence base: PS3's anti-requirement ("rather than simply running a local vector database"), Qdrant's "no RAG or simple chatbots" rule for its own hackathon [Q6], rival patterns [06], and demo-risk reasoning.

## 1. Overused ideas (the judges will see them many times)

| Idea | Why it's weak for PS3 |
|---|---|
| "Offline chatbot over my PDFs" | It is RAG with the network cable pulled. It fails the "meaningful edge-to-cloud workflow" test |
| Smart-glasses / "find my keys" visual memory | This is **Qdrant's own demo** (qdrant/qdrant-edge-demo). Parity at best |
| Robot object-memory viewer | **Qdrant Labs' Mission Control** already does it beautifully |
| "Edge AI dashboard" with a network toggle and a queue bar | Every rival has one. It is table stakes, not a differentiator |

## 2. Generic AI features to avoid

- **A local LLM chat / "ask your device"** (Ollama, llama.cpp): latency, RAM, hallucination risk, and it moves attention away from Qdrant.
- **LLM-generated summaries of memories** in the core demo: non-deterministic output on stage.
- **LLM as conflict judge** ("the AI decides which report is true"): unsafe for maintenance, unverifiable, and it contradicts "flagged, never guessed". *Maybe* as a clearly labelled suggestion in future scope.
- **"Agentic" orchestration layers** (CrewAI/LangGraph) around a simple pipeline.

## 3. Features that don't solve the core problem

- Cloudinary media pipelines, n8n alert flows or Omnidimension voice agents in the live path (see [05](05_SPONSOR_AND_PARTNER_RESEARCH.md)).
- User accounts, login and RBAC screens. They are not in the PS, cost time, and are a demo risk. Mention them as production scope.
- A mobile app rewrite (React Native / Flutter bridge). High risk in the time left. FieldEdge chose this path.
- Blockchain / ledger audit trails.

## 4. Unnecessary complexity

| Tech | Why not now |
|---|---|
| P2P mesh gossip, IBLT, Merkle range sync | Solves device↔device-without-cloud; PS3 frames edge↔**cloud**; the rival already owns it |
| CRDT text merging of memories | Semantic facts are not text documents. Automatic merge ≠ truth |
| Kubernetes, Kafka, microservice sprawl | A gateway + Qdrant Server is enough; more boxes add more failure modes |
| Fine-tuning Laya (the LLM classifier) before 30 Sep | The LogReg classifier already scores 98.3%. Diminishing returns |
| Pathway streaming layer | A second retrieval/stream engine muddies the Qdrant story |
| HNSW parameter tuning / quantization experiments | Latency is already ~4 ms. Tavus: "architecture beats micro-optimizations" |

## 5. Features likely to fail during the demo

- **Anything needing venue Wi-Fi or a cloud API** (hosted LLMs, Qdrant Cloud over the internet, Cloudinary). Run Qdrant Server locally in Docker.
- **Live model downloads** (FastEmbed first run). Pre-cache the models (`setup_models.py`) and verify with the network off.
- **Docker Desktop cold start on Windows.** Start it 30 minutes early; keep `--qdrant embedded` as the fallback.
- **Multi-laptop networking at the venue.** Use one laptop with a software link switch as the default.
- **Long first-time `optimize()` on large shards** during a beat. Pre-warm.
- **Deleting shard folders on Windows** (~15 s, locks). Already avoided by deleting points.

## 6. Claims that cannot be demonstrated (don't make them)

- "Runs on any edge device / Raspberry Pi / Jetson" unless it was run and measured there.
- "Scales to millions of devices." Say "designed for per-device shards + server multitenancy" instead.
- "Military-grade security / end-to-end encrypted." There is no signing or TLS in the MVP.
- "Zero data loss guaranteed." Say "0 acknowledged writes lost across N crash tests".
- "AI understands everything." Say "98.3% on 60 held-out notes; safety recall 0.9; small test set".
- Bandwidth "40% saved" while measuring 38.2%. Report the measured number.

## 7. Features judges may consider superficial

- Animated charts with no underlying measurement.
- A "3D embedding galaxy" with no decision attached.
- Twenty dashboard tabs. Three views covering the four PS nouns (memory, search, sync, activity) are enough.
- Buzzword architecture slides ("agentic, multimodal, federated") unrelated to what runs.

## 8. The cut list (already decided in PROPOSAL.md v2, which we endorse)

Local LLM (Ollama), n8n alerts, 6→3 dashboard views, HLC clocks, 8 live beats → 4, Presidio, MCP, consolidation. Research supports every cut.
