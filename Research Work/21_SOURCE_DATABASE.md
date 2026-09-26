# 21 — Source Database

← [20 Final strategy](20_FINAL_PROJECT_STRATEGY.md) · [Master index](00_MASTER_RESEARCH_INDEX.md)

All sources were accessed on **2026-09-26**. Reliability: **HIGH** = official or primary; **MEDIUM** = reputable secondary or self-published marketing; **LOW** = aggregator, snippet or unverified.

## Method notes

- The built-in WebFetch/WebSearch tools failed in this session (a model configuration error). Research used: (a) the in-app browser (HackCulture, Devpost, Devfolio, Unstop, Bing results), (b) direct HTTP fetches of pages and of Qdrant's `index.md` markdown docs, (c) the GitHub REST API, (d) the arXiv API, (e) local PDF text extraction and rendering.
- Bing began serving a CAPTCHA partway through. **We did not solve or bypass it.** LinkedIn-only facts (CC4/CC5 winners) are therefore **NOT FOUND**.
- The official PS PDF hosted on HackCulture (1 page, PS3, Qdrant-branded) differs in file hash from the local 3-page copy. Both were rendered and read; the PS3 wording is identical.

## Sources

| ID | Source name | URL | What was obtained | Reliability | Used in |
|---|---|---|---|---|---|
| S1 | HackCulture: Code Cubicle 6.0 | https://hackculture.io/hackathons/code-cubicle-6-0 | Organizer, dates, stages, rules, prizes, partners, FAQ, contact, venue, registrations | HIGH | 01, 03, 05, 15 |
| S2 | Official PS PDF (hosted) | https://hackcultureplatform.blob.core.windows.net/event-assets/hackathons/6a9084220579dffec28137de/problem_explanation_piovxkhlbtb.pdf | Verbatim PS3, Qdrant logo, "3 OCT ONLINE · 11 OCT OFFLINE" | HIGH | 01, 02, 04 |
| S2b | Local PS PDF (3 PS) | `docs/reference/problem-statements.pdf` | PS1–PS3 text; the PS2 Cloudinary badge | HIGH | 01 |
| S3 | Devpost: CC 6.0 mirror | https://code-cubicle-6-0.devpost.com/ ; /rules | Requirements, villa prize, 3–11 Oct, truncated judging criteria, team 2–4 | MEDIUM | 01, 05, 15 |
| S5 | SheKunj listing (snippet) | https://www.shekunj.com/hackathons/code-cubicle-6-0 | Villa in Goa, hiring, mentorship | LOW | 01 |
| G1 | Geek Room: About | https://geekroom.framer.website/about-us | Founders, milestones, members, contact | HIGH (self-reported figures) | 03 |
| D1 | Devfolio: Code Cubicle 1.0 | https://code-cubicle.devfolio.co/ | Dates, venue, sponsors | HIGH | 03 |
| D3 | Devfolio: Code Cubicle 3.0 (+ /projects, /prizes) | https://code-cubicle-3.devfolio.co/projects | Mastercard partnership, judges, 107 projects, winners | HIGH | 03, 07 |
| U4 | Unstop: Code Cubicle 4.0 | https://unstop.com/hackathons/code-cubicle-40-geek-room-1478969 | Microsoft Hyderabad, dates, 2,910 registrations | MEDIUM | 03 |
| U5 | Unstop: Code Cubicle 5.0 | https://unstop.com/hackathons/code-cubicle-5-geek-room-1537583 | Pathway title sponsor, HackCulture co-organizer, format (5-min pitch; 8-hour on-site), rules | MEDIUM | 01, 03, 05, 07 |
| C2 | Code Cubicle 1.0 site | https://codecubicle.netlify.app/ | Earlier problem themes | MEDIUM | 03, 07 |
| H1 | HackCulture home/about | https://hackculture.io/ ; /about | Business model, scale | MEDIUM | 03 |
| GH | GitHub API: GeekRoom org | https://api.github.com/users/GeekRoom | No central org GitHub | HIGH | 03 |
| Q1 | Qdrant Edge docs | https://qdrant.tech/documentation/edge/ | Beta, SQLite analogy, sync purposes | HIGH | 02, 04 |
| Q-doc-vs | Edge vs Qdrant Cluster | https://qdrant.tech/documentation/edge/edge-vs-qdrant-cluster/ | Capability table | HIGH | 02, 04, 12 |
| Q-doc-sync | Data Synchronization Patterns | https://qdrant.tech/documentation/edge/edge-data-synchronization-patterns/ | Snapshot / partial snapshot / dual-write code | HIGH | 02, 04, 10, 12 |
| Q-doc-guide | Synchronize with a Server | https://qdrant.tech/documentation/edge/edge-synchronization-guide/ | Mutable + immutable pattern; timestamp dedup | HIGH | 02, 04 |
| Q-doc-bm25 | BM25 with Qdrant Edge | https://qdrant.tech/documentation/edge/edge-bm25/ | Built-in BM25; server compatibility | HIGH | 04, 13 |
| Q-llms | Qdrant llms.txt index | https://qdrant.tech/llms.txt | Discovery of Edge docs and blogs | HIGH | method |
| Q2 | Qdrant Series B blog | https://qdrant.tech/blog/series-b-announcement/ | $50M, AVP lead, investors, customers, strategy | HIGH | 04 |
| P1 | Business Wire / FinSMEs / AVP / Bosch press (search results) | https://www.businesswire.com ; https://www.finsmes.com ; https://avpcap.com ; https://www.bosch-presse.de | Cross-check: 12 Mar 2026, $50M, Berlin | MEDIUM | 04 |
| Q3 | Qdrant Edge product page | https://qdrant.tech/edge/ | Use cases, lineup, beta access | HIGH | 04 |
| Q4 | Qdrant Edge private beta blog | https://qdrant.tech/blog/qdrant-edge/ | Three waves; design targets | HIGH | 02, 04 |
| Q-blog-memory | "Memory at the Edge" | https://qdrant.tech/blog/qdrant-edge-on-device-vector-search/ | Five edge constraints; ~11 MB; demo internals | HIGH | 02, 04 |
| Q-blog-anomaly | Video anomaly edge-to-cloud | https://qdrant.tech/blog/video-anomaly-detection-edge-to-cloud/ | Two-shard Jetson design; ~6× cloud reduction | HIGH | 02, 06, 08 |
| Q5 / Q-recap | Vector Space Day SF 2026 recap | https://qdrant.tech/blog/vector-space-day-2026-recap/ | Leadership names/roles; strategy; retrieval-eval emphasis | HIGH | 02, 04 |
| Q6 | Qdrant 2026 hackathon winners | https://qdrant.tech/blog/vector-space-hackathon-winners-2026/ | Criteria; no-chatbot rule; winners | HIGH | 04, 07, 08, 11 |
| Q7 | Qdrant 2025 hackathon winners | https://qdrant.tech/blog/vector-space-hackathon-winners-2025/ | Criteria incl. Qdrant Usage; RoboBank | HIGH | 04, 07 |
| Q8 | Sketch & Search winners | https://qdrant.tech/blog/sketch-n-search-winners/ | Criteria; "retrieval as an engineering primitive" | HIGH | 04, 07 |
| Tavus | Tavus case study | https://qdrant.tech/blog/case-study-tavus/ | Edge retrieval latency; "architecture beats micro-optimizations" | HIGH | 04, 11 |
| GH-demo1 | qdrant/qdrant-edge-demo | https://github.com/qdrant/qdrant-edge-demo | Two-shard + SQLite queue reference | HIGH | 04, 06 |
| GH-demo2 | qdrant-labs/edge-mission-control | https://github.com/qdrant-labs/edge-mission-control | Robot memory demo; demo-craft practices | HIGH | 04, 06, 07 |
| GH-demo3 | qdrant/video-anomaly-edge | https://github.com/qdrant/video-anomaly-edge | Reference tutorial repo | HIGH | 04 |
| R1 | AegisEdge (rival) | https://github.com/akshatinnovate-png/AegisEdge | Design, claims, `qdrant-client` dependency, CI | HIGH (claims self-reported) | 06, 07 |
| R2 | FieldEdge (rival) | https://github.com/choksi2212/code-cubicle-qdrant | Android + Qdrant Edge; timestamp conflicts | HIGH | 06 |
| R3 | EdgeSync AI (rival) | https://github.com/lakshay2425/code-cubicle-ps-03 | Next.js dashboard; overwrite/merge | HIGH | 06 |
| R4 | Edge-Mind-AI (rival) | https://github.com/theerthan-bg/Edge-Mind-AI | Existence only | LOW | 06 |
| R5 | GitHub search API | https://api.github.com/search/repositories | Rival discovery | HIGH | 06 |
| PW1 | Pathway home | https://pathway.com/ | BDH positioning | HIGH (self) | 05 |
| PW2 | Pathway templates | https://pathway.com/developers/templates | Live Data framework RAG/ETL templates | HIGH (self) | 05 |
| N1 | n8n home | https://n8n.io/ | Product, community size | HIGH (self) | 05 |
| C1 | Cloudinary About | https://cloudinary.com/about | Company facts | HIGH (self) | 05 |
| O1 | OmniDimension home | https://www.omnidim.io/ | Voice AI product | MEDIUM (self) | 05 |
| W1 | Wayzyy home | https://wayzyy.com/ | Goa rentals | MEDIUM (self) | 05 |
| E1 | Eventopia home | https://www.eventopia.in/ | Student event reach | MEDIUM (self) | 05 |
| CB | Couchbase Lite conflict docs | https://docs.couchbase.com/couchbase-lite/current/c/conflict.html | Default conflict rules | HIGH | 02, 06 |
| CBV | Couchbase Lite vector search | https://docs.couchbase.com/couchbase-lite/current/c/vector-search.html | Vector search (Enterprise) | HIGH | 06 |
| OB | ObjectBox | https://objectbox.io/ | "Edge vector database" | MEDIUM | 06 |
| DT | Ditto | https://www.ditto.com/ | Edge-native sync | MEDIUM | 06 |
| MDB | MongoDB Device Sync deprecation | https://www.mongodb.com/docs/atlas/app-services/sync/device-sync-deprecation/ | EOL 30 Sep 2025; Ditto/PowerSync alternatives | HIGH | 06 |
| SV | sqlite-vec | https://github.com/asg017/sqlite-vec | Pre-v1 C extension | HIGH | 06 |
| GAE | Google AI Edge RAG | https://ai.google.dev/edge/mediapipe/solutions/genai/rag | Marked deprecated | HIGH | 06 |
| M0 | Mem0 OSS | https://docs.mem0.ai/open-source/overview | Library/server memory | HIGH | 06 |
| LDB | LanceDB | https://lancedb.com/ | Positioning | MEDIUM | 06 |
| AX1 | arXiv: EdgeRAG (2412.21023) | https://arxiv.org/abs/2412.21023 | Title/date verified | HIGH (bibliographic) | 06 |
| REF-Dynamo | Dynamo paper (SOSP 2007) | https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf | Version-vector lineage (from prior knowledge; not re-fetched) | MEDIUM-HIGH | 06, 12 |
| REF-CRDT | Shapiro et al., CRDTs (2011) | https://inria.hal.science/inria-00609399 | CRDT background (not re-fetched) | MEDIUM-HIGH | 06 |
| REF-LF | Ink & Switch: Local-first software (2019) | https://www.inkandswitch.com/essay/local-first/ | Pitch vocabulary (not re-fetched) | MEDIUM-HIGH | 06 |
| SM | Smaran repo docs | `README.md`, `docs/PROPOSAL.md`, `docs/IMPLEMENTATION_PLAN.md`, `docs/BENCHMARKS.md`, `docs/DEMO.md`, `backend/requirements.txt` | The current state of our own project | HIGH (our measurements) | 02, 09, 12–20 |

## Conflicts between sources

| Topic | Conflict | Resolution |
|---|---|---|
| Submission/online window | HackCulture: 21–30 Sep; PDF footer: "3 OCT ONLINE"; Devpost: 3–11 Oct | HackCulture (the registration platform) is most authoritative → freeze on 30 Sep; confirm 3 Oct by email |
| Team size | HackCulture 1–4; Devpost 2–4 | HackCulture |
| Geek Room size | 50,000+ members (own site) vs 100,000+ developers (Unstop 2025) | Different dates and definitions; quote both with their source |
| Code Cubicle total registrations | 7,000+ (CC4 listing) vs 20,000+ (CC5 listing) | Cumulative claims growing over time; self-reported |
| Prize amounts | HackCulture ₹12k/10k/8k general + Cloudinary ₹1.2L/40k; Devpost $200/$65/$35 | HackCulture is authoritative; the Devpost mirror appears to be a scaled-down copy |
