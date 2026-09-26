# 19 — Risk Analysis

← [18 Judge perspective](18_JUDGE_PERSPECTIVE.md) · [Master index](00_MASTER_RESEARCH_INDEX.md) · Next: [20 Final strategy](20_FINAL_PROJECT_STRATEGY.md)

Scale: Probability / Impact = Low · Med · High. Items are sorted by priority (P × I).

| # | Risk | Category | P | I | Mitigation | Backup plan |
|---|---|---|---|---|---|---|
| 1 | **Never run against the real Qdrant Server** before the judges ask | Integration / compliance | **High** (not yet done) | **High** (PS3 names it) | Phase 1.6: Docker bring-up, pinned image/client pair, 10 rehearsals in server mode | Embedded mode + a pre-recorded server beat; say so honestly |
| 2 | **Not selected in the elimination** because the GitHub/LinkedIn profile is weak | Selection | Med | **High** | Hero GIF, CI badge, credits, per-member commits, LinkedIn posts by all 4 (Phase 1.8–1.10) | — |
| 3 | Docker Desktop fails on the demo laptop at the venue | Deployment | Med | High | Start 30 min early; test on venue power; keep Docker images pulled | `start-all --qdrant embedded` |
| 4 | A live demo beat fails | Demo | Low–Med (10/10 rehearsals) | High | Per-beat resets; the exact scripted inputs; a rehearsal on the day | Reset (~5 s); the backup video |
| 5 | Date confusion (30 Sep vs 3 Oct) → a missed submission or pitch | Time | Med | High | Treat 30 Sep 23:59 as the freeze; email organizers | — |
| 6 | Rival (AegisEdge) out-presents on durability/security | Competition | Med | Med | Kill-and-replay beat; emphasise the Qdrant Edge compliance gap and a clearer story | Q&A answers #1, #9 |
| 7 | Qdrant Edge beta API changes / a bug in partial snapshots | Technical / API | Med | Med | Pin `qdrant-edge-py==0.8.0`; partial snapshots behind a flag | The scroll-based mirror refresh (built) |
| 8 | Judges challenge the small labelled set / leakage | Data | High | Med | State the caveats; test only on hand-written notes; compute kappa | Show rules-only vs model to make the value of each layer clear |
| 9 | On-site build task at the final (CC5 had 8 h) | Time | Med | Med | Rehearse likely extensions (new PII rule, new note type, new machine, multilingual) | Scope the answer; show tests passing |
| 10 | Model download needed offline (cache missing) | Technical | Low | High | `setup_models.py` run and verified with Wi-Fi off; `HF_HUB_OFFLINE=1` | Copy the model cache from another laptop (USB) |
| 11 | Scope creep after research (building too many WOW items) | Time | Med | Med | The Phase 2 cut rules; a feature freeze on 29 Sep EOD | Drop Phase 3 entirely |
| 12 | AI misclassifies a private note as sync live | AI error | Low | High | PII rules run first and are non-overridable; demo inputs are rehearsed | Explain the layered design; show the audit |
| 13 | Search returns the wrong top result live | AI / retrieval | Low | Med | Scripted queries; the device-wide IDF fix; the golden-set eval | Show #2 result and explain the RRF scores |
| 14 | Security questions (spoofing, auth) | Security | Med | Low–Med | An honest "not in MVP" + a concrete roadmap (Ed25519, mTLS, OIDC) | — |
| 15 | Privacy of the demo data (real names/phone numbers) | Privacy | Low | Med | Synthetic names/numbers only | — |
| 16 | Scalability claims challenged | Scalability | Med | Low | Say "measured to 5 devices × 1000 runs; design for more" | — |
| 17 | The public repo lets rivals copy ideas before the final | Competition | Med | Low | Keep committing; the edge is in execution + measurements | — |
| 18 | Team availability / travel to Noida on 11 Oct (no reimbursement in CC5) | Logistics | Low–Med | High | Confirm travel now; at least 2 members must be able to present | Present with the available members + video |
| 19 | Windows-specific issues (file locks on shard dirs, paths) | Technical | Med | Low | Already mitigated (delete points, not folders) | `wipe` + restart |
| 20 | Hallucination | AI | Very low (no LLM in the loop) | — | Keep the LLM out | — |
