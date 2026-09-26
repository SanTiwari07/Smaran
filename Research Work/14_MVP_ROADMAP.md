# 14 — MVP Roadmap

← [13 Tech stack](13_TECH_STACK_RECOMMENDATION.md) · [Master index](00_MASTER_RESEARCH_INDEX.md) · Next: [15 Judging strategy](15_JUDGING_STRATEGY.md)

Context: as of **Sat 26 Sep 2026**, Smaran's P0 and most P1 items are built and tested (`docs/IMPLEMENTATION_PLAN.md`). This roadmap is therefore about **closing research-identified gaps**, not building from zero.

Key dates: **Wed 30 Sep 23:59** submission freeze (HackCulture) · **~Sat 3 Oct** possible online pitch (PDF footer; to be confirmed) · **Sun 11 Oct 09:00–18:00** offline final at Paytm Noida (possibly with on-site build time, per the CC5 format).

Owners follow the implementation plan's A/B/C/D split (A: device/Edge, B: gateway/Themis, C: dashboard, D: ML/bench).

---

## Phase 1: Core MVP (must work perfectly). **Deadline: 29 Sep EOD**

| # | Item | Status | Owner | Done when |
|---|---|---|---|---|
| 1.1 | Offline memory + hybrid search on Qdrant Edge (3 shards) | ✅ | A | — |
| 1.2 | Argus residency decisions with reasons | ✅ | A/D | — |
| 1.3 | Crash-safe outbox + idempotent gateway sync | ✅ | A/B | — |
| 1.4 | Themis conflicts + supervisor resolve + Chronos | ✅ | B/C | — |
| 1.5 | Dashboard: 4 PS nouns (memory, search, sync, activity) | ✅ | C | — |
| **1.6** | **Run the full stack against the real Qdrant Server (Docker)**; `rehearse --runs 10` passes in server mode; pin a compatible image/client pair | ❌ | A+B | 10/10 in server mode, logged in BENCHMARKS.md |
| **1.7** | **Record the backup demo video** (4 beats, ≤ 3 min) in server mode | ❌ | C | MP4 in the repo release / linked in the README |
| **1.8** | **README as first-round pitch**: hero GIF (conflict reveal), a 1-line promise, results table (exists), architecture image, "Prove it in 60 s" commands, credits section, team + LinkedIn links | ◐ | C | The README renders well on GitHub |
| **1.9** | **CI badge**: GitHub Actions running `pytest` on push | ❌ | B | A green badge on the README |
| 1.10 | Credits / third-party acknowledgements (rules require it): Qdrant Edge, FastEmbed + BGE model, scikit-learn, React, etc. | ❌ | D | A section in the README |

## Phase 2: Competitive features (differentiate). **Deadline: 30 Sep 18:00 (freeze buffer)**

| # | Item | Why (research) | Owner | Effort | Cut rule |
|---|---|---|---|---|---|
| 2.1 | **float16/binary vector transport** → bandwidth ≥ 40% (likely ~60%+) | Turns a reported miss into a win | A | ~2–3 h | Cut if tests break |
| 2.2 | **Retrieval quality eval**: 30–50 golden queries; hit@1/@5/MRR for dense vs BM25 vs hybrid | Qdrant's "similarity ≠ relevance" emphasis; no rival has it | D | ~4 h | Cut only if labelling can't finish; report whatever is measured |
| 2.3 | **"Why here?" badge** on each memory (rule/classifier, confidence, shard) | Makes R4 visible | C | ~2 h | — |
| 2.4 | **Kill-and-replay beat**: `demo.py kill a` / restart + UI counters (acked / replayed / duplicates) | Parity with AegisEdge's headline, on a clearer story | A+C | ~3 h | Keep it video-only if flaky |
| 2.5 | Label agreement (Cohen's kappa) on the 60 test notes | Methodology credibility with data-scientist judges | C+D | ~2 h | — |

## Phase 3: WOW features (only if Phases 1–2 are green). **Window: 1–10 Oct (after the freeze, for the final)**

**Note (RECOMMENDATION):** work done after 30 Sep may not count for the elimination round. Since the CC5 rules said "all code must be written during the hackathon", keep post-freeze work on a clearly dated branch and be transparent about it at the final.

| # | Item | Effort | Risk |
|---|---|---|---|
| 3.1 | **Partial-snapshot Agora refresh** (`snapshot_manifest` → partial snapshot → `update_from_snapshot`), with a bytes-saved counter; the scroll fallback stays behind a flag | 1 day spike | Beta API; Windows file locks |
| 3.2 | Recency-aware ranking with Edge **formula scoring** or **MMR** diversity | ½ day | Low |
| 3.3 | Self-playing "auto" demo mode (like Mission Control's `?auto`) | ½ day | Low |
| 3.4 | Second physical device (laptop/RPi) over a hotspot you can switch off | 1 day | Venue networking |
| 3.5 | "Prove it" panel: each headline claim with a button that re-runs its check | ½–1 day | Low |
| 3.6 | **On-site build readiness:** a checklist of plausible judge requests (add a new note type, new PII rule, new machine, multilingual note) with rehearsed ≤ 30-min implementations | ongoing | — |

## Phase 4: Future production version (say it, don't build it)

- Signed operations (Ed25519) + device enrolment; mTLS; OIDC/RBAC for supervisors.
- Real devices: an Android/iOS app via the Qdrant Edge Rust crate or community RN/Flutter bindings; Jetson/RPi builds.
- Multimodal memory: photos of machine plates, audio notes (on-device ASR), with Qdrant named vectors.
- CMMS integration (SAP PM, IBM Maximo) and webhooks (n8n).
- Multilingual (Hindi/Hinglish) embeddings; per-plant fine-tuned classifier; active learning from supervisor overrides.
- Fleet analytics on the server (optionally Pathway streaming over the change feed).
- Policy-as-code for residency, with a signed policy distributed via the mirror.
- Log compaction and retention (DPDP "storage limitation").

## Daily plan to the freeze (RECOMMENDATION)

| Day | A (device) | B (gateway) | C (dashboard) | D (ML/bench) |
|---|---|---|---|---|
| **Sat 26 Sep** | Docker Qdrant Server bring-up (1.6) | CI workflow (1.9) | README hero + architecture PNG (1.8) | Golden query set drafting (2.2) |
| **Sun 27 Sep** | float16 transport (2.1) | Server-mode rehearsals, fix issues (1.6) | "Why here?" badge (2.3) | Retrieval eval script + numbers (2.2) |
| **Mon 28 Sep** | Kill/replay helper (2.4) | Credits + docs (1.10) | Kill/replay UI counters (2.4) | Kappa (2.5); regenerate BENCHMARKS |
| **Tue 29 Sep** | Freeze features; bug fixes | Full `rehearse --runs 10` | Record video (1.7) | Update README numbers |
| **Wed 30 Sep** | Buffer | Buffer | Final README polish, LinkedIn posts | Submission form, links check (by 18:00) |
