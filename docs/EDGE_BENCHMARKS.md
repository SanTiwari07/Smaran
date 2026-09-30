# Edge benchmark (personal companion)

Measured 2026-09-30 07:53 on: Windows-11-10.0.26200-SP0, Python 3.14.2, 12 CPU threads. Command: `python -m bench.edge`. Every number below was measured by that command; nothing is estimated.

| Measure | Result |
|---|---|
| Embedder load (bge-small ONNX, CPU) | 310 ms |
| Query embedding p50 / p95 | 4.44 / 5.2 ms (100 runs) |
| Document embedding p50 / p95 | 4.45 / 5.39 ms |
| Retrieval (embed + hybrid search + rerank) @ 100 memories, p50 / p95 | 8.14 / 9.29 ms (60 queries, 622.1 MB on disk) |
| Retrieval (embed + hybrid search + rerank) @ 1000 memories, p50 / p95 | 8.68 / 9.93 ms (60 queries, 626.8 MB on disk) |
| Retrieval (embed + hybrid search + rerank) @ 3000 memories, p50 / p95 | 8.78 / 31.0 ms (60 queries, 635.7 MB on disk) |
| Agent: create task with verify p50 / p95 | 161.97 / 189.35 ms (30 runs) |
| Agent: list tasks p50 / p95 | 7.63 / 15.71 ms (30 runs) |
| Agent: chat remember end to end p50 / p95 | 219.44 / 247.28 ms (20 runs) |
| Agent: chat ask rules end to end p50 / p95 | 383.39 / 433.84 ms (20 runs) |
| Sync push of 3148 queued ops | 35371 ms (sent 3148) |
| Sync pull after push | 20535 ms (3156 points) |
| Replay of the same 3148 ops (idempotency) | 8324 ms, results {'duplicate': 3148} |
| Offline restart (link off): open device + companion / to first answered question | 3213 / 3234 ms with 100 memories |
| Offline restart, larger memory | 4284 / 4730 ms with 3158 memories |
| Process memory (working set) | 147 MB at start, 278 MB with the embedder, 384 MB at the end |
| On-disk size at 3158 memories | 1281.3 MB |
| Local SLM `llama3.2:latest` (Ollama (llama.cpp)): load / first token | 602 ms |
| Question answered on device (retrieve + generate) p50 / p95 | 1652 / 1772 ms (5 questions; SLM answered 5/6) |
| Questions where the SLM answer was rejected or failed and rules answered | 1 |

Notes:
- Retrieval and agent rows run with the SLM disabled so they show the cost of memory and tools alone.
- Sync rows use the gateway's real HTTP routes in-process, not a network; add your LAN or mobile latency on top.
- Memory notes are synthetic lecture sentences (`Lecture note N: ...`) plus the 15-utterance story.
