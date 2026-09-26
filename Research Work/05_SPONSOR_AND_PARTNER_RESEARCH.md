# 05 — Sponsor and Partner Research

← [04 Qdrant](04_PS3_ORGANIZATION_RESEARCH.md) · [Master index](00_MASTER_RESEARCH_INDEX.md) · Next: [06 Competitors](06_COMPETITOR_ANALYSIS.md)

Rule applied: **don't force sponsor tech into the solution.** Each partner below gets a verdict on whether it gives Smaran a *genuine* technical advantage.

## Summary verdicts

| Partner | Role (FACT [S1]) | Genuine advantage for PS3? | Verdict |
|---|---|---|---|
| **Qdrant** | Technology Partner, PS3 owner | Mandatory | **USE DEEPLY** (see [04](04_PS3_ORGANIZATION_RESEARCH.md)) |
| **Pathway** | Technology Partner (CC5 title sponsor) | Possible: streaming change feed on the gateway | **OPTIONAL / future scope.** Do not add before 30 Sep |
| n8n | License Partner (100 × $60 Cloud Pro) | Weak: alerting to supervisors on conflict or a safety-critical event | **AVOID in the core demo**; mention as an integration point (already cut in the proposal) |
| Cloudinary | Track Sponsor (PS2 prizes) | None for text memory; a photo-evidence extension would add a cloud dependency, against offline-first | **AVOID** |
| Omnidimension | Credits (100 × $50 voice AI) | Weak: voice capture for gloved technicians is attractive, but cloud voice breaks offline-first | **AVOID** (future: an on-device ASR such as whisper.cpp) |
| Logitech | Experience Partner (5 mice) | None | n/a |
| Wayzyy | Travel Partner (villa stay, per Devpost) | None | n/a |
| Eventopia | Media Partner | None | n/a |
| Paytm | Final venue host | Indirect: potential audience or judges from a fintech / large-scale engineering org | Pitch reliability and "no silent data loss", which fintech engineers value |

## 1. Pathway

| Field | Value | Label | Source |
|---|---|---|---|
| What | "Frontier AI lab building architectures and models that autonomously reason, learn, and evolve". Current homepage features **BDH (Dragon Hatchling)**, a "post-transformer" architecture with persistent state | FACT (self) | [PW1] |
| Developer product | **Pathway Live Data Framework**: Python API, Rust engine, unified batch + streaming, 300+ connectors, **real-time RAG templates** (question-answering, **Adaptive RAG** "up to 4x" token savings, **Private RAG with Mistral + Ollama**, multimodal RAG) | FACT (self) | [PW2] |
| Company | "Palo Alto–based … founded around 2020 … CEO Zuzanna Stamirowska, CTO Jan Chorowski, CSO Adrian Kosowski … backed by Łukasz Kaiser"; customers "NATO, Intel, DB Schenker, Formula 1 teams" | SOURCE-REPORTED (Geek Room's Unstop listing) | [U5] |
| Hackathon history | **Title sponsor of Code Cubicle 5.0** (Sep 2025) | FACT (listing) | [U5] |
| Why involved (ANALYST) | Developer adoption of the Live Data framework; talent pipeline | INFERENCE | |

**Genuine fit?** Pathway's pitch is "live" indexing of changing data. PS3's "handle continuously changing data" overlaps. However, Pathway runs as a server-side streaming engine, and Smaran's gateway already has an idempotent change feed. Adding Pathway would put a second retrieval engine next to Qdrant. That muddies the PS3 story, which is about Qdrant Edge, and adds integration risk in the last four days.
**RECOMMENDATION:** Name Pathway only as a possible future cloud-side stream processor (for example, fleet analytics over the change feed). Do not implement it.

## 2. n8n

| Field | Value | Label | Source |
|---|---|---|---|
| What | "AI Workflow Automation Platform": visual + code workflows, AI agents, self-hostable (Docker), hosted cloud | FACT | [N1] |
| Scale | "205.9k stars" on GitHub, "200k+ community members" (homepage) | FACT (self-reported) | [N1] |
| Role here | License Partner: 100 × $60 n8n Cloud Pro credits | FACT | [S1] |
| Why involved (ANALYST) | Credits drive trial-to-paid conversion; PS1 (workflow-building data platform) is n8n-shaped | INFERENCE | |

**Genuine fit?** A conflict or safety-critical event could trigger an n8n webhook (Slack/email to a supervisor). That is cloud-side and runs only when online, so it is acceptable, but it is one more service to fail on stage. The proposal already cut it.
**RECOMMENDATION:** Expose a generic `POST /webhooks` on the gateway (future), and say "plugs into n8n". No live dependency.

## 3. Cloudinary

| Field | Value | Label | Source |
|---|---|---|---|
| What | Image and video management, transformation and delivery APIs; AI tagging; DAM. "used by more than 4M developers and 13,000 brands"; founded 2012 | FACT (self) | [C1] |
| Role | Track Sponsor: PS2 prizes ₹1.2L + ₹40K (the largest prizes of the event) | FACT | [S1] |

**Genuine fit for PS3?** No. PS3 is about on-device memory that works offline. Cloudinary is a cloud media pipeline.
**Observation (ANALYST):** The PS2 prize is ten times the PS3 prize. Many strong teams will pick PS2, and some teams (for example "ORCHESTRA · IMPACTOS") are submitting to multiple PSs. PS3's field is therefore likely smaller and more technical.

## 4. Omnidimension

| Field | Value | Label | Source |
|---|---|---|---|
| What | "OmniDimension Voice AI": build, test and deploy voice assistants from natural-language descriptions; templates for lead generation, appointments, support, collections; white-label | FACT (self) | [O1] |
| Role | 100 × $50 voice AI credits | FACT | [S1] |

**Fit?** Cloud voice agents contradict offline-first. **AVOID.**

## 5. Logitech, Wayzyy, Eventopia

- **Logitech:** Experience Partner; five wireless mice for "Top participants" [S1].
- **Wayzyy:** Goa short-term rentals, "0% booking commission", "Connecting 100,000+ developers & travelers with verified Goa homestays" [W1]. This is almost certainly the source of the "villa stay in Goa" winner prize (ANALYST INFERENCE from [S3] and [W1]).
- **Eventopia:** a student event-discovery site, "50K+ Students reached, 38+ Campuses, 223+ Events" [E1]. Media partner.

None has technical relevance.

## 6. Paytm (venue)

**FACT:** The final is at Paytm's Noida office [S1]. **NOT FOUND:** whether Paytm engineers judge.
**ANALYST INFERENCE:** If they do, Paytm runs payments at national scale. Idempotency, crash-safe queues, exactly-once effects and audit trails are their daily concerns. Smaran's idempotent `/sync`, crash-replay outbox and "0 concurrent edits lost" are directly legible to that audience. Keep one slide sentence ready: *"Same guarantees your payments stack needs: idempotent, crash-safe, auditable."*

## Sources

| ID | Source | URL | Accessed | Info | Reliability |
|---|---|---|---|---|---|
| S1 | HackCulture CC 6.0 page | https://hackculture.io/hackathons/code-cubicle-6-0 | 2026-09-26 | Partner roles, prizes | HIGH |
| S3 | Devpost CC 6.0 | https://code-cubicle-6-0.devpost.com/ | 2026-09-26 | Villa prize | MEDIUM |
| PW1 | Pathway homepage | https://pathway.com/ | 2026-09-26 | BDH, positioning | HIGH (self) |
| PW2 | Pathway Live Data Framework templates | https://pathway.com/developers/templates | 2026-09-26 | RAG/ETL templates | HIGH (self) |
| U5 | Unstop CC 5.0 listing | https://unstop.com/hackathons/code-cubicle-5-geek-room-1537583 | 2026-09-26 | Pathway company blurb, title sponsorship | MEDIUM |
| N1 | n8n homepage | https://n8n.io/ | 2026-09-26 | Product, scale | HIGH (self) |
| C1 | Cloudinary About | https://cloudinary.com/about | 2026-09-26 | Company facts | HIGH (self) |
| O1 | OmniDimension homepage | https://www.omnidim.io/ | 2026-09-26 | Product | MEDIUM (self) |
| W1 | Wayzyy homepage | https://wayzyy.com/ | 2026-09-26 | Business | MEDIUM (self) |
| E1 | Eventopia homepage | https://www.eventopia.in/ | 2026-09-26 | Reach | MEDIUM (self) |
