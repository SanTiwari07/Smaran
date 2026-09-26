# 15 — Judging Strategy

← [14 MVP roadmap](14_MVP_ROADMAP.md) · [Master index](00_MASTER_RESEARCH_INDEX.md) · Next: [16 Demo strategy](16_DEMO_STRATEGY.md)

## What is official

| Stage | Criteria | Label |
|---|---|---|
| Elimination (21–30 Sep) | "selected based on Github and Linkedin profiles"; "overall GitHub and LinkedIn profiles of the team members" | **FACT** [S1] |
| Final (11 Oct) | "The final winners will be selected by the hackathon jury based on the evaluation criteria." The criteria themselves are not published | FACT (that they're unpublished) [S1] |
| Devpost mirror | "Innovation & Creativity – Uniqueness and originality of the idea; Technical Implementation – Quality, functionality, and technical…" (truncated at the source) | SOURCE-REPORTED [S3] |
| PS3 owner's own hackathons | Creativity, Technical Depth, **Qdrant Usage** (2025); Innovation, Creativity, Technical Depth (2026); + search effectiveness, UX trade-offs, guardrails, real-world applicability (Sketch & Search) | FACT for Qdrant's events [Q6–Q8]; **ANALYST INFERENCE** that similar values apply here |

## Working rubric (ANALYST INFERENCE)

Built from the official fragments + Qdrant's rubrics + CC's history. Weights are our estimate.

| Area | Est. weight | What judges need to see | How we demonstrate it |
|---|---|---|---|
| **Innovation & creativity** | 25% | Something beyond "local vector DB + sync" | Version-vector conflicts vs LWW (the side-by-side "naive merge" box); a structural private shard; Chronos belief history |
| **Technical implementation / depth** | 25% | It works live; the design is principled; the numbers are real | Live 4-beat demo on the real Qdrant Server; 3.9 ms p50; 1000/1000 convergence; 30 tests + CI; the IDF/RRF bug story |
| **Qdrant usage** (PS-specific) | 15% | Real Qdrant Edge, used idiomatically; real Qdrant Server | A "Qdrant calls" slide (see [12](12_TECHNICAL_ARCHITECTURE.md) §4); partial snapshots if shipped; open the Qdrant Web UI during the demo |
| **PS3 requirement coverage** | 15% | Every PS3 bullet ticked | A one-slide traceability matrix (R1–R10 from [02](02_PROBLEM_STATEMENT_3_ANALYSIS.md)) |
| **Impact / real-world applicability** | 10% | A real user, a real cost, deployable | The technician/supervisor story; bandwidth %; 0 private records; the DPDP angle; the pilot deployment topology |
| **UX** | 5% | Clear, explainable UI | 3 views; "Why here?" badges; the conflict card |
| **Presentation** | 5% | Crisp, on time, Q&A handled | 5:00 rehearsed; a backup video; a judge Q&A bank ([18](18_JUDGE_PERSPECTIVE.md)) |

## Elimination round: optimise the profile (FACT-driven)

| Asset | What a reviewer scanning for 60 seconds should see |
|---|---|
| Repo home | The name + one-line promise; **hero GIF** of the conflict reveal; a **CI badge**; a results table; a "Prove it in 60 s" block; an architecture diagram |
| Commit history | Many meaningful commits by several members (not one giant dump). *Currently 3 commits, all by SanTiwari07*. **RECOMMENDATION:** future commits from each member's own account for their area; keep messages descriptive |
| Docs | PROPOSAL, IMPLEMENTATION_PLAN, BENCHMARKS, DEMO, DEBUGGING (already strong) |
| LinkedIn (all 4 members) | A post announcing the project with the GIF + repo link; the project added to "Projects"; tag Geek Room / Qdrant / #codecubicle6 |
| Credits | Third-party acknowledgements (a rule requirement) |

## Final round: map every claim to evidence

| Claim | Evidence shown | Where |
|---|---|---|
| Works offline | The link switch is off; search answers in ms | Beat 1 |
| Decides what stays local | Phone number → Krypta with "PII rule phone_in"; the audit shows 0 on the server | Beat 2 |
| Syncs to Qdrant Server | Points count rises in the Qdrant Web UI | Beat 3 |
| Handles conflicts | CONTESTED card; version vectors; naive-merge box | Beat 3 |
| Evolving memory | Supervisor resolve → superseded + Chronos | Beat 4 |
| Low latency | The on-screen latency per query; the BENCHMARKS table | Beats 1 and 4 + slide |
| Correctness at scale | 1000/1000 5-device simulation | Slide |
| Retrieval quality | hit@k hybrid vs single-mode | Slide (if 2.2 is shipped) |

## Clearly-labelled strategic inferences

- A Qdrant representative is likely involved in evaluating PS3 finalists (the PS carries Qdrant branding). **Speak Qdrant's vocabulary precisely.**
- Paytm-hosted: reliability language (idempotency, crash safety) plays well.
- Past CC juries included data scientists, so methodology questions (test-set size, leakage, kappa) are likely. Pre-empt them.
