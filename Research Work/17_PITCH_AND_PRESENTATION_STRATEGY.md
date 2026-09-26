# 17 — Pitch and Presentation Strategy

← [16 Demo](16_DEMO_STRATEGY.md) · [Master index](00_MASTER_RESEARCH_INDEX.md) · Next: [18 Judge perspective](18_JUDGE_PERSPECTIVE.md)

## What winning presentations do (ANALYST INFERENCE from [07](07_PREVIOUS_WINNERS_ANALYSIS.md) and [08](08_WINNING_PATTERNS.md))

| Aspect | Observed in winners | Implication |
|---|---|---|
| Slide count | Qdrant winners submit ~2–5-minute videos; CC5 online slots were 5 minutes | **8–10 slides** for 5 minutes; the demo carries the middle |
| Storytelling | Person → pain → mechanism → proof (MemoryAtlas: "the user never asks a question. The system finds the answer anyway.") | Open on the technician, not the tech |
| Technical detail | One mechanism explained well (RoboBank: safest-neighbour retrieval), using the sponsor's primitives by name | Explain Themis in one picture: `{A:1}` vs `{B:1}` → concurrent |
| Architecture | One diagram, labelled with the sponsor's components | The 3-shard diagram with Qdrant labels |
| Impact | A measured effect (~6× less cloud volume; <$1/day) | The results table with measured numbers and one "missed" row |
| Innovation | Contrast with the default (Cardinal: "LLM touched only twice") | Contrast with LWW: "13/50 vs 50/50" |
| Honesty | "What does not work" sections | One line on limits (small test set; signing is future scope) |

## Proposed deck (10 slides + hidden backups)

| # | Slide | Content | Time |
|---|---|---|---|
| 1 | **Title** | ΣMARAN. "Memory that doesn't forget, and doesn't lie." Team names; Code Cubicle 6.0 · PS3 · Built on Qdrant Edge | 0:05 |
| 2 | **The moment** | One image: two technicians, one machine, Wi-Fi off, two opposite reports | 0:15 |
| 3 | **Why today's answers fail** | Cloud RAG / local store / timestamp sync (incl. Qdrant's reference pattern), each with the specific failure | 0:20 |
| 4 | **Smaran in one picture** | Krypta · Hermes · Agora + gateway + Qdrant Server; the 3 guarantees: private by structure, correct under conflict, synced when connected | 0:25 |
| 5 | **LIVE DEMO** (switch to the dashboard) | 4 beats | 2:30 |
| 6 | **How Themis decides** | Version vectors: newer vs concurrent; supersede vs contest; the human resolves; history kept | 0:15 |
| 7 | **Qdrant doing the work** | The table of Edge/Server calls ([12](12_TECHNICAL_ARCHITECTURE.md) §4) | 0:15 |
| 8 | **Measured, not claimed** | Latency, conflicts, convergence, privacy, bandwidth, classifier (with caveats), retrieval quality | 0:25 |
| 9 | **PS3 checklist** | R1–R10 all ticked with where each is shown | 0:10 |
| 10 | **Where it goes** | Pilot topology; roadmap (signing, multimodal, CMMS); who buys | 0:15 |
| — | Close | Tagline | 0:05 |
| B1–B5 | Hidden backups | Beat screenshots; classifier methodology; IDF/RRF bug story; security roadmap; bandwidth details | Q&A |

## Speaking roles (4 members)

| Member | Role in the pitch |
|---|---|
| Presenter (most fluent) | Slides 1–4, 10, close |
| Demo driver | Beats 1–4 (hands on keyboard; the presenter narrates, or the driver narrates) |
| Tech lead (Themis/gateway) | Slides 6–7; Q&A on sync and conflicts |
| ML/bench lead | Slide 8; Q&A on the classifier, metrics and methodology |

## Language rules

- Say **"vector search engine"** (Qdrant's preferred term), "Edge Shard", "partial snapshot", "hybrid query with RRF".
- Say "**flagged, never guessed**" and "**superseded, not deleted**".
- Numbers always come with their denominator ("50 of 50 scripted cases", "60 held-out notes").
- No "revolutionary", "military-grade", "any device".

## Pitch-ready one-liners

- Hook: "Two technicians. One machine. No Wi-Fi. Opposite reports. Which one does your AI believe?"
- Contrast: "Last-writer-wins got 13 of 50 right. Smaran got 50 of 50, because it doesn't trust clocks."
- Privacy: "Private notes can't sync. Not because a rule says no, but because there's no code path."
- Close: "Qdrant Edge gave devices a memory. Smaran makes that memory trustworthy offline."
