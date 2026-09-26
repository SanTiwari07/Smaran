# 08 — Winning Patterns

← [07 Previous winners](07_PREVIOUS_WINNERS_ANALYSIS.md) · [Master index](00_MASTER_RESEARCH_INDEX.md) · Next: [09 Differentiation](09_DIFFERENTIATION_STRATEGY.md)

Everything here is **ANALYST INFERENCE** distilled from [03](03_ORGANIZER_RESEARCH.md), [04](04_PS3_ORGANIZATION_RESEARCH.md), [06](06_COMPETITOR_ANALYSIS.md) and [07](07_PREVIOUS_WINNERS_ANALYSIS.md). Each pattern cites its evidence.

## P1. One sentence, one user, one consequence

Winners open with a human and a stake: "neurodiverse students", "robot's next move … safest neighbour", "proof from the user's own history" [D3][Q6][Q7].
→ Smaran: *"Two technicians report opposite things about the same machine while the Wi-Fi is down. Today, one report silently disappears. With Smaran, the supervisor sees both."*

## P2. The sponsor's primitives are visibly doing the work

The Qdrant winners are praised for named vectors, the Recommend API with negatives, Discovery, and multi-vector prefetch plus RRF. Cardinal is praised because "everything in between is Qdrant doing the work" [Q6][Q7][Q8]. The judging criteria literally include **"Qdrant Usage"** [Q7].
→ Smaran must show, on a slide and in the UI, which Qdrant Edge calls run at each step. See [12](12_TECHNICAL_ARCHITECTURE.md) §4.

## P3. LLMs minimised; retrieval as an engineering primitive

"No RAG or simple chatbots" [Q6]; "retrieval as an engineering primitive — not a bolt-on feature" [Q8].
→ Smaran's decision to cut the Ollama chat is **correct**. Keep answers as **cited retrieval results**.

## P4. One unforgettable visual moment

Vector Vintage's 3D terrain, Crowd Whisperer's crowd map, Mission Control's live detection boxes, AegisEdge's SIGKILL GIF.
→ Smaran's candidate: **two devices reconnect and the conflict card "splits" into two side-by-side reports with version vectors, next to a "naive merge" box showing what would have been lost.** A second candidate: **pull the plug (kill device A mid-sync), restart, and the outbox replays with 0 duplicates.**

## P5. Claims you can falsify on the spot

AegisEdge: "Six claims, each with the button that falsifies it". Mission Control labels a comparison band "not a measurement". The CC3 judges were data scientists [D3][R1][GH-demos].
→ Every number on Smaran's slides has a command (`bench.bench`, `demo.py rehearse`) and, ideally, a button in the dashboard.

## P6. Honest limits increase credibility

AegisEdge's "What does not work", Smaran's "Bandwidth 38.2% (target 40%, missed)", and the Mission Control disclaimers.
→ Keep the "missed" row. Judges trust teams that report misses.

## P7. The README is the first pitch (especially here)

CC 6.0 selection is based on **GitHub and LinkedIn profiles** [S1]. Top READMEs lead with a hero image/GIF, a one-line promise, a results table, "prove it in 60 s" commands and a CI badge [R1][GH-demos].
→ Smaran's README has the results table but **no hero GIF, no CI badge, and no architecture image**.

## P8. Narrow scope, deep execution beats breadth

RoboBank won 2nd with one mechanism (trajectory memory + safety labels) in a 2D simulator [Q7]. AegisEdge's 103 modules are impressive but hard to explain in 5 minutes.
→ Smaran's four beats are the right size. Don't add a P2P mesh, a knowledge graph or signing just to match.

## P9. Measured business effect

The video-anomaly demo claims "~6× less cloud processing while catching ~95% of true anomalies" [Q-blog-anomaly]. The 3rd-place NPCs cost "<$1/day" [Q7].
→ Smaran: "X% less bandwidth, 0 private records on the server, 0 lost edits, N ms offline". Tie each to money or safety in the pitch.

## P10. Domain alignment with the host

Mastercard → the fintech project won at CC3 [D3].
→ Qdrant's stated edge domains are robotics, industrial IoT, kiosks, mobile and voice [Q3]. **Industrial maintenance is squarely in Qdrant's list**, so keep it. Paytm hosts: reliability language.

## P11. Demo engineering (reliability is a feature)

Mission Control ships `?auto` scripted mode and a headless `make test`. Smaran has `demo.py reset/play/rehearse` with 10/10 passes [GH-demos].
→ Smaran is already at the showcase level here. Add a **recorded fallback video** and a **self-playing mode**.

## P12. What average teams do (and lose on)

From the rival scan [06]: generic names; adjective-heavy READMEs; timestamp LWW conflicts; "decides what to sync" as a static rule; no measured accuracy; `qdrant-client` instead of Qdrant Edge; no real server; a dashboard walkthrough in place of a story.

## Pattern → Smaran checklist

| # | Pattern | Smaran status | Action |
|---|---|---|---|
| P1 | One user, one stake | ✓ technician/supervisor | Open the pitch with it |
| P2 | Qdrant doing the work | ◐ uses Edge, BM25, filters | Add a "Qdrant calls" overlay/slide; partial snapshots |
| P3 | LLM minimised | ✓ | Say it explicitly |
| P4 | Unforgettable moment | ◐ conflict view exists | Stage the conflict reveal + live kill/restart |
| P5 | Falsifiable claims | ◐ CLI only | Add a "Prove it" panel |
| P6 | Honest limits | ✓ | Keep |
| P7 | README as pitch | ✗ no GIF / CI | **P0 before 30 Sep** |
| P8 | Narrow and deep | ✓ | Resist scope creep |
| P9 | Business effect | ◐ | Translate the metrics into ₹ and risk |
| P10 | Domain alignment | ✓ industrial | — |
| P11 | Demo engineering | ✓ | Add a video and auto mode |

Sources: see [07](07_PREVIOUS_WINNERS_ANALYSIS.md) and [21](21_SOURCE_DATABASE.md).
