# 07 — Previous Winners Analysis

← [06 Competitors](06_COMPETITOR_ANALYSIS.md) · [Master index](00_MASTER_RESEARCH_INDEX.md) · Next: [08 Winning patterns](08_WINNING_PATTERNS.md)

Purpose: learn **patterns**, not copy projects. There are two evidence pools:

- **A. Code Cubicle winners**: how Geek Room's juries have decided.
- **B. Qdrant hackathon winners**: how the PS3 owner judges vector-search work.

A third, qualitative pool (C) covers Qdrant's own showcase demos, which set the presentation bar.

---

## A. Code Cubicle

### A1. Code Cubicle 3.0 (Sep 2024, Mastercard, Gurugram): 107 projects; winners from Devfolio [D3]

| Project | Problem selection | Solution | AI usage | Presentation signals (tagline) |
|---|---|---|---|---|
| **EduSync** | Speech therapy access for neurodiverse students | Pronunciation analysis, real-time feedback, conversational practice | Speech AI | Names a specific underserved user; "Empowering Neurodiversity" |
| **Vizcureot** | Hobbyist/IoT sensor setup is hard | Detect the sensor → generate code and wiring diagrams | Vision + code generation | Concrete, tangible hardware angle |
| **FinWise AI** | Financial literacy | AI financial guidance | LLM | Matches the sponsor's domain (Mastercard) |
| **DeepTrace** | Deepfakes / misinformation | "Predicting what's true in a world of fakes" | Detection models | **Trust / verification** narrative |
| MediMind (listing order; winner tag not confirmed) | Mental health | Personal guide | LLM | Human-centred |

Judges: Mastercard AI Garage (a Director, a VP of Data Science, a Brand & Creative Manager), an H2O.ai data scientist (2× Kaggle Grandmaster), an Evalueserve data-science manager [D3].

**Pattern (ANALYST):** Winners had a **specific person with a specific pain** plus **an AI capability that visibly works**. Where the sponsor was the domain owner (Mastercard → fintech), a domain-aligned project won.

### A2. Code Cubicle 1.0, 2.0, 4.0, 5.0

- **1.0 (May 2024):** open, domain-themed problem statements (edtech, healthcare, fintech, fraud) [C2]. Winners **NOT FOUND**. The Devfolio project list exists: https://code-cubicle.devfolio.co/projects
- **2.0 (Aug 2024, Microsoft):** a report on Scribd titled "Code Cubicle 2.0 Hackathon Report" (not accessed). Winners **NOT FOUND**.
- **4.0 (Jul 2025, Microsoft Hyderabad)** and **5.0 (Sep 2025, Microsoft Bangalore, Pathway title sponsor):** winners **NOT FOUND — REQUIRES VERIFICATION.** These are mostly on LinkedIn; Bing blocked us with a CAPTCHA.
- **Format evidence (5.0):** a 5-minute pitch + 2-minute Q&A online; the top 15 do an 8-hour on-site build [U5]. See [03](03_ORGANIZER_RESEARCH.md).

## B. Qdrant hackathons (the PS3 owner's revealed preferences)

### B1. Vector Space Hackathon 2025 (winners announced 26 Sep 2025, Berlin). Criteria: **Creativity, Technical Depth, Qdrant Usage** [Q7]

| Place | Project | What | Why it likely won (ANALYST) |
|---|---|---|---|
| 1st ($5,000 + Neo4j credits) | **Vector Vintage** | E-commerce discovery as an explorable **3D terrain**: embeddings → Qdrant → Neo4j curation → UMAP → React Three Fiber; LLM guide narrates 7 items | Unforgettable visual; retrieval is the core, not a wrapper |
| **2nd ($3,000)** | **RoboBank** | **Robot trajectory memory**: banks sensor-action sequences as vectors, **labels them safe/unsafe**, retrieves the safest neighbour for the next move; 2D simulator | **Edge/robotics memory + safety.** The closest analogue to PS3 and to Smaran's safety-critical-first design |
| 3rd ($2,000) | **Spatio-Temporal NPCs** | NPCs with place/event memory; CLIP + MiniLM; whisper.cpp; Piper TTS; **runs locally on ~3 GB VRAM**, <$1/day | Local-first, measured cost and latency |
| Category | ReMap (CrewAI), CosmicTwin (Mistral), Bachata Vibes (Superlinked), Qlassroom (TwelveLabs) | Hybrid search + geo/temporal filters; personality matching; choreography; multimodal classroom | Partner-tech bonus prizes reward real integration |

### B2. "Think Outside the Bot" Hackathon 2026 (5 weeks, $10k; winners at Vector Space Day 2026). Criteria: **Innovation, Creativity, Technical Depth**; **no RAG or simple chatbots** [Q6]

| Place | Project | Key technique | Why it likely won (ANALYST) |
|---|---|---|---|
| 1st | **MemoryAtlas** | **Six named vectors per point** (semantic, emotion, prosody, linguistic, dissonance, audio); a custom transformer over 14-day sequences; the **Recommend API with negative examples + datetime payload filter** to retrieve the "recovery window" | Deep use of Qdrant-specific primitives; the user never asks, the system finds it |
| 2nd | **Crowd Whisperer** | 532-d hybrid persona vectors; per-15-second reward drift; 2D projection of the crowd | A novel simulation; strong visual |
| 3rd | **Synthara** | RPG with a vector "soul history"; Gemini dialogue grounded in past deeds | Memory as a game mechanic |
| HM | **DejaPlay** | Football possession embeddings, metadata filters, side-by-side pitch animation | Domain-expert UX |
| HM | **Cardinal** | "The language model is touched only twice … Everything in between is Qdrant doing the work": Recommend, multi-vector prefetch + RRF, filtered HNSW, Discovery API; deterministic and inspectable | **LLM minimisation + determinism + inspectability** is explicitly praised |

### B3. Sketch & Search (Nov 2025, with Google DeepMind + Freepik; $25k+). Criteria: creative quality, **effective search and similarity**, **UX trade-offs**, **guardrails**, **real-world applicability** [Q8]

Winners: Prometheus (protein → cinematic trailer; Qdrant reuses the best prompt templates), Roast My Snack (vision + semantic search + **transparent risk scoring**), AutoScape (image → build-ready landscape plan grounded in a curated catalog). Qdrant's own summary: *"treat retrieval as an engineering primitive — not a bolt-on feature"*.

## C. Showcase-level demos (presentation bar)

- **Qdrant Edge Mission Control:** a live-demo URL; a **self-playing `?auto` mode** for recording; per-frame timing strips; honest labelling ("The cloud round-trip band … is a labeled typical range for comparison, not a measurement") [GH-demos].
- **AegisEdge (rival):** "PROVE IT" buttons; a crash GIF at the top of the README; CI-verified claims; a "What does not work" section [R1].

## Cross-pool analysis

| Dimension | What winners did | What average entries do (from rivals in [06](06_COMPETITOR_ANALYSIS.md)) |
|---|---|---|
| Problem selection | A specific user plus a consequential pain (therapy, safety, misinformation) | Generic "edge devices need AI" |
| Naming | Evocative, short, memorable (MemoryAtlas, RoboBank, DeepTrace) | "EdgeSync AI", "Edge-Mind-AI" (generic, easily confused) |
| README | Hero image/GIF at the top; one-line promise; measured results; how to verify | Feature lists with adjectives |
| Demo | One unforgettable visual moment (3D terrain, crash recovery, crowd map) | A dashboard walkthrough |
| Architecture diagram | One clear flow, labelled with the sponsor's primitives | Box soup or none |
| AI usage | AI where it makes a decision; LLM minimised | "Integrated LLM", chatbot |
| Metrics | Measured, with methodology and caveats | Adjectives ("lightning-fast") |
| Sponsor tech | Deep, idiomatic use (named vectors, Recommend, Discovery) | Name-dropping |
| Real-world applicability | Clear deployment story and cost | "Scalable" |
| Honesty | Limits stated (AegisEdge, Mission Control) | Claims unqualified |

Detailed patterns are in [08](08_WINNING_PATTERNS.md).

## Sources

| ID | Source | URL | Accessed | Info | Reliability |
|---|---|---|---|---|---|
| D3 | Devfolio CC 3.0 projects + lineup | https://code-cubicle-3.devfolio.co/projects | 2026-09-26 | Winners, judges | HIGH |
| C2 | Code Cubicle 1.0 site | https://codecubicle.netlify.app/ | 2026-09-26 | PS themes | MEDIUM |
| U5 | Unstop CC 5.0 | https://unstop.com/hackathons/code-cubicle-5-geek-room-1537583 | 2026-09-26 | Format | MEDIUM |
| Q6 | Qdrant 2026 hackathon winners | https://qdrant.tech/blog/vector-space-hackathon-winners-2026/ | 2026-09-26 | Criteria, winners | HIGH |
| Q7 | Qdrant 2025 hackathon winners | https://qdrant.tech/blog/vector-space-hackathon-winners-2025/ | 2026-09-26 | Criteria, winners | HIGH |
| Q8 | Sketch & Search winners | https://qdrant.tech/blog/sketch-n-search-winners/ | 2026-09-26 | Criteria, winners | HIGH |
| GH-demos | edge-mission-control README | https://github.com/qdrant-labs/edge-mission-control | 2026-09-26 | Demo craft | HIGH |
| R1 | AegisEdge README | https://github.com/akshatinnovate-png/AegisEdge | 2026-09-26 | Rival craft | HIGH |
