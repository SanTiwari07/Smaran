# Smaran: Audit and Implementation Plan

Audit date: **Sat 26 Sep 2026**. Audited against the research in [`Research Work/`](../Research%20Work/00_MASTER_RESEARCH_INDEX.md) and the rules in [`AGENT.md`](../AGENT.md). The demo video is out of scope for this plan by team decision.

How the audit was done: read all 22 research files; read the README, `docs/`, and the device, gateway, search, router, sync and dashboard code; ran `pytest` (**30/30 pass**); checked Docker (**daemon 29.7.2 now runs** on the dev laptop); read `logs/gateway.log` and `logs/rehearsal.log`; searched every tracked file and the git history for tool attribution (**none found**).

---

## 1. Where we stand

### 1.1 Verdict

Smaran's core is built, tested and measured, and it sits in the white space the research identified (governance, conflict semantics, durability). **The gaps are proof and presentation, not features.** Four items decide the elimination round: a real Qdrant Server run, a README + CI that sell the project in 30 seconds, the bandwidth miss, and a retrieval-quality number.

### 1.2 PS3 requirement matrix (R1–R10)

| ID | Requirement | Status | Evidence in the repo | Gap |
|---|---|---|---|---|
| R1 | Uses Qdrant Edge | ✅ | `qdrant-edge-py==0.8.0`, `EdgeShard`, built-in `Bm25` (`backend/device/store.py`, `embed.py`) | Say it on a slide and in the README "Qdrant calls" table |
| R2 | Semantic memory on device | ✅ | Krypta / Hermes / Agora shards | — |
| R3 | Low-latency vector + hybrid search offline | ✅ | 3.9 ms p50 / 5.6 ms p95, 2,000 memories (`docs/BENCHMARKS.md`) | No retrieval-**quality** number |
| R4 | Dynamically decide local vs sync | ✅ | Argus: PII → LogReg → dedup; 98.3% on 60 held-out notes; `decision.reason` stored | Kappa not measured; reason not shown on every memory row |
| R5 | Intermittent connectivity | ✅ | Online flag, SQLite WAL outbox, crash-replay tests | Crash recovery not visible in the UI |
| R6 | Sync with **Qdrant Server** | ⚠ **open** | Gateway code supports server mode; `gateway.log` shows **1 start against `127.0.0.1:6333` vs 7 in embedded mode**; the 10/10 rehearsal log does not record which mode it ran in | No documented 10/10 in server mode; client 1.19.1 vs image v1.15.4 version warning |
| R7 | Evolving memory and conflicts | ✅ | Themis 50/50 vs naive 13/50; 1000/1000 convergence; Chronos | — |
| R8 | UI for memory, search, sync, activity | ✅ | 3 views + activity feed | — |
| R9 | Meaningful edge-to-cloud workflow | ✅ | Agora mirror, change feed, cloud escalation | Mirror uses the change feed, not Qdrant's partial snapshots |
| R10 | A complete product | ◐ | Maintenance-copilot framing | Persona must lead the README |

### 1.3 Research checklist vs repo

| Research item | Source | Status | Notes |
|---|---|---|---|
| Real Qdrant Server run, 10/10 rehearsals | 14 §1.6, 20 #15.1 | ❌ | Docker now works, so this is unblocked |
| Pinned client/image pair | 13 | ❌ | `qdrant-client` unpinned (1.19.1 installed); image `v1.15.4` |
| GitHub Actions CI + badge | 14 §1.9 | ❌ | No `.github/` folder |
| README: hero GIF, architecture diagram, "Prove it in 60 s", credits, team + LinkedIn | 14 §1.8, §1.10 | ❌ | README has results and commands only; **no Credits section (a rules requirement)** |
| float16 vector transport, bandwidth ≥ 40% | 14 §2.1 | ❌ | Dense vectors travel as JSON floats (~9 KB/op); 38.2% measured |
| Retrieval eval (hit@1, hit@5, MRR; hybrid vs dense vs BM25) | 14 §2.2 | ❌ | Nothing in `bench/` |
| "Why here?" badge on every memory | 14 §2.3 | ◐ | Reason shown on write result and in the decision log, not on memory rows or search hits |
| Kill-and-replay beat + counters | 14 §2.4 | ◐ | Replay logic and tests exist (`device/core.py` counts `recovered`); no `demo.py kill`, no UI counters |
| Cohen's kappa | 14 §2.5 | ◐ | Code exists in `ml/train.py`; needs a second labeller's columns |
| Payload indexes on every shard and the server | 12 §3 | ✅ | `store.py:59-60`, `gateway/server.py` |
| `optimize()` on an idle timer | 12 §4 | ✅ | `hermes.py` |
| Partial-snapshot mirror refresh | 14 §3.1 | ❌ | Post-freeze item |
| Formula / MMR ranking, auto demo mode, Prove-it panel | 14 §3.2–3.5 | ❌ | Post-freeze items |
| Per-member commits | 15 | ❌ | All 5 commits are from one account |
| Organizer email (deliverables, "3 Oct online") | 20 checklist | ❌ | Human task |
| LinkedIn posts ×4 | 20 checklist | ❌ | Human task |
| No tool attribution anywhere | AGENT.md §0 | ✅ | Files and git history are clean |

### 1.4 Other findings

- **Stale docs.** `docs/IMPLEMENTATION_PLAN.md` still says "`git init` … the folder isn't a repository yet" and "Docker Desktop didn't start". Update after the server run.
- **Rehearsal log has no mode or commit field.** An earlier 10-run set in `logs/rehearsal.log` failed b1 in several runs before the clean 10/10. Recording the mode and commit makes the "10/10" claim checkable.
- **Local Docker has unrelated containers** from other projects. Stop them before the demo so they don't compete for RAM or ports.

---

## 2. Implementation plan

Owners follow the existing split: **A** device/Edge · **B** gateway/Themis · **C** dashboard/docs · **D** ML/bench. Each work package (WP) lists files, steps and a done-when check. Priorities: **P0** must ship before the freeze, **P1** should ship before the freeze, **P2** is for the final (post-freeze branch).

### Phase 1: P0, by Tue 29 Sep EOD

#### WP1. Real Qdrant Server round trip (R6). Owner A+B. ~3 h

1. **Pin the pair.** Choose the `qdrant/qdrant` image tag whose minor version matches the installed `qdrant-client` (or pin `qdrant-client` down to match `v1.15.x`). Verify the tag with `docker pull`. Pin `qdrant-client==<x.y.z>` in `backend/requirements.txt` and the tag in `infra/docker-compose.yml`. The version warning must disappear.
2. **Collection layout for later partial snapshots.** In `backend/gateway/server.py::ensure`, create the collection with `shard_number=1` explicitly.
3. **Record the mode.** In `scripts/demo.py::rehearse`, add `"mode"` (from the gateway's `describe()`, exposed through `/stats`) and the short git commit to every `rehearsal.log` line.
4. **Server stats.** Make the gateway `/stats` return the server `points_count` (from `get_collection`), so the dashboard and demo can show the count rising.
5. **Run it.** `docker compose -f infra/docker-compose.yml up -d` → `demo.py start-all` → `demo.py status` → `demo.py rehearse --runs 10`.
6. **Audit against the server.** Re-run the privacy audit and the bench personal-data section in server mode.
7. **Document it.** Add a "Qdrant Server mode" row to `docs/BENCHMARKS.md` (10/10, image tag, date). Update the README troubleshooting (remove the version-warning note) and the status table in `docs/IMPLEMENTATION_PLAN.md`.

**Done when:** 10/10 rehearsals logged with `mode=server`; audit shows 0 private / 0 PII on the real server; no version warning.

#### WP2. CI on GitHub Actions. Owner B. ~1 h

1. Add `.github/workflows/ci.yml`, triggered on push and pull request:
   - Job `backend` (ubuntu-latest, Python 3.11): `pip install -r backend/requirements.txt` → `pytest -q`. Tests don't need model files.
   - Job `frontend` (Node 20): `npm ci --prefix frontend` → `npm --prefix frontend run build` (type-checks the TSX).
   - Optional job `windows-backend` (windows-latest) because Windows is the demo platform.
2. Cache pip and npm.
3. Add the badge to the top of the README.

**Done when:** a green badge on `main`.

#### WP3. README as the first-round pitch. Owner C (+D for numbers). ~4 h

Restructure `README.md` (keep the existing sections below the new top):

1. **Top block:** name, CI badge, one-line promise ("Everyone shows a device can remember. Smaran keeps that memory correct and private when devices go offline and disagree."), and the **hero GIF** of the conflict reveal (a 10–15 s screen capture saved as `docs/assets/conflict.gif`; this is a README asset, separate from the excluded demo video).
2. **The moment (3 lines):** two technicians, one machine, Wi-Fi down, opposite reports.
3. **Architecture:** the mermaid diagram from `Research Work/12` §1 (GitHub renders mermaid; no image file needed).
4. **Qdrant calls table** (from `Research Work/12` §4): `EdgeShard`, named dense + sparse vectors, built-in `Bm25`, RRF, filters + payload indexes, `optimize()`, upsert to Qdrant Server.
5. **Results table** (existing) with the new rows from WP4, WP5 and WP1.
6. **"Prove it in 60 seconds":** four commands (`pytest`, `bench.bench`, `demo.py rehearse --runs 3`, `demo.py play b3`) with what each proves.
7. **PS3 checklist:** R1–R10 with where each is shown.
8. **Credits** (rules requirement): Qdrant Edge + Qdrant Server + `qdrant-client` (Apache-2.0), FastEmbed and `BAAI/bge-small-en-v1.5` (MIT), scikit-learn (BSD-3), FastAPI, Uvicorn, Pydantic, httpx, Hypothesis, pytest, React, Vite, TypeScript. Add anything else found in `backend/requirements.txt` and `frontend/package.json`.
9. **Team:** names, roles, GitHub and LinkedIn links.
10. **Known limitations:** keep and update.

**Done when:** the README renders on GitHub with the GIF, diagram, badge and credits; every number matches `BENCHMARKS.md`.

#### WP4. float16 vector transport (bandwidth miss → win). Owner A. ~3 h

1. `backend/common/schema.py`: let `VectorsJson` accept either `dense: list[float]` or `dense_f16: str` (base64 of little-endian float16 bytes). Add `encode_dense()` / `decode_dense()` helpers in `backend/common/` so the device and gateway share one implementation.
2. Device (`backend/device/core.py` where the outbox body is built): send `dense_f16` when `settings.vector_transport == "f16"` (new setting, default `f16`, fallback `json`).
3. Gateway (`backend/gateway/core.py` / `server.py`): decode to `list[float]` before `upsert`. The change feed (`vectors_json`) can send f16 too; the device decodes before writing to Agora.
4. Tests: round-trip encode/decode (max abs error < 1e-3); cosine between original and decoded > 0.9999; e2e sync still passes with both settings.
5. Re-run `bench.bench`; replace the bandwidth row in README and BENCHMARKS with the measured number. If it is still under 40%, report it as measured.

**Done when:** tests pass in both modes; rehearsals 10/10; a new measured bandwidth number.

#### WP5. Retrieval-quality eval. Owner D. ~4 h

1. `bench/golden_queries.json`: 40 queries over the seeded corpus (`seed/manuals/fleet.json` + bench notes): 15 paraphrases, 10 part numbers / machine IDs (such as "CNC-07"), 5 typos, 10 mixed. Each lists the expected `op_id`(s). Two members label independently; resolve disagreements.
2. `backend/device/search.py`: add a `mode` argument (`hybrid` default, `dense`, `bm25`) that skips the other list before fusion. No behaviour change for the default.
3. `bench/retrieval.py` (called from `bench.bench`): hit@1, hit@5 and MRR per mode; write a "Retrieval quality" section into `docs/BENCHMARKS.md` with the query count and categories.
4. Test: the eval runs on a tiny fixture and returns numbers in [0, 1].
5. Report the numbers as they come out, even if hybrid does not win every category.

**Done when:** a table of hybrid vs dense vs BM25 in BENCHMARKS and a row in the README results.

### Phase 2: P1, by Wed 30 Sep 18:00 (each has a cut rule)

#### WP6. "Why here?" on every memory (R4 made visible). Owner C. ~2 h

1. Make sure `/memories` and `/search` results include `decision` (it is stored in the payload).
2. `frontend/src/views/MemorySearch.tsx`: on memory rows and search hits, show a compact badge `Krypta · pii_rule phone_in` or `Hermes · classifier 0.94 · critical`, with the full reason on hover.
3. Update `frontend/src/mock/mock.ts` so mock mode shows it too.

Cut rule: none; it is small.

#### WP7. Kill-and-replay beat. Owner A+C. ~3 h

1. `scripts/demo.py`: add `kill <A|B>` (hard kill from `runtime/pids.json`: `taskkill /F /PID` on Windows, `SIGKILL` elsewhere) and `start <A|B>`.
2. Device `/stats`: expose `recovered` (outbox rows replayed on the last start), `acked`, and the gateway's `duplicates` count for this device.
3. `frontend/src/views/DevicesSync.tsx`: show "acked N · replayed N · duplicates N" on each device card.
4. Add a `b5` beat to `reset` / `play`: queue notes offline → go online → kill mid-drain → start → check that every acked write is on the server exactly once.
5. Test: extend `test_crash_recovery_replays_outbox` to assert the counters.

Cut rule: if `play b5` is not 10/10, keep the command for Q&A and leave it out of the scripted demo.

#### WP8. Label agreement (kappa). Owner C+D (second labeller). ~2 h

1. A member who did not write the labels fills `residency_2` and `criticality_2` for `h001`–`h060` in `ml/data/handwritten_notes.csv`, without looking at the first labels.
2. `python -m ml.train` → kappa goes into BENCHMARKS; update the README limitation line.

Cut rule: if it isn't done by 30 Sep, keep the limitation line as it is.

#### WP9. Docs hygiene. Owner C. ~1 h

- Update `docs/IMPLEMENTATION_PLAN.md` status table and "Next steps" (remove `git init`; record the server run).
- Update `docs/DEMO.md` for the server tab (`localhost:6333/dashboard`) and the kill beat if shipped.
- Make sure the test count in the README matches `pytest`.

### Phase 3: human tasks (not code, but they decide selection)

| # | Task | Owner | By |
|---|---|---|---|
| H1 | Email `team.geekroom@gmail.com`: confirm submission fields and whether there is an online pitch on 3 Oct | Lead | 27 Sep |
| H2 | Each member commits their own WP from their own GitHub account | All | ongoing |
| H3 | LinkedIn post from each member: GIF, repo link, one measured number; tag Geek Room, Qdrant, #codecubicle6; add the project to the Projects section | All | 30 Sep |
| H4 | Fill the HackCulture submission; check every link in a private window | Lead | 30 Sep 18:00 |
| H5 | Rehearse the 5:00 pitch five times with a timer; drill the 15 questions in `Research Work/18` | All | 1–3 Oct |
| H6 | Confirm travel to Paytm Noida for 11 Oct; at least two members must be able to present | All | 1 Oct |

### Phase 4: P2, for the 11 Oct final (post-freeze, dated branch)

Work on `final/2026-10-*` branches; disclose at the final that these were built after 30 Sep.

| # | Item | Plan | Effort | Fallback |
|---|---|---|---|---|
| F1 | **Partial-snapshot Agora refresh** | Device: `manifest = agora.snapshot_manifest()` → gateway endpoint that calls `POST /collections/{c}/shards/0/snapshot/partial/create` with the manifest and streams the file back → device `update_from_snapshot(path)`. Count bytes vs a full snapshot and show "pulled X KB instead of Y MB". Flag `MIRROR_REFRESH=partial|feed` | 1 day | Change feed (built) |
| F2 | Recency-aware ranking | Edge formula scoring (decay on `valid_from`) or MMR for diverse results; measure with the WP5 golden set before enabling | ½ day | Current RRF |
| F3 | Self-playing demo mode | `?auto` in the dashboard runs b1–b4 on a timer | ½ day | Manual beats |
| F4 | "Prove it" panel | Each headline claim with a button that re-runs its check (audit, conflict bench subset, latency sample) | ½–1 day | CLI commands |
| F5 | On-site build readiness | Rehearse ≤ 30-minute changes: new PII rule, new note type, new machine, a Hindi/Hinglish note (multilingual model swap) | ongoing | — |
| F6 | Second physical device (optional) | Only if F1–F5 are solid; laptop over a switchable hotspot | 1 day | One laptop, software link switch |

Say, don't build (production roadmap for slides): Ed25519 signing and enrolment, mTLS/OIDC, encryption at rest, multimodal notes, CMMS integration and webhooks, multilingual embeddings, retention and compaction.

---

## 3. Day-by-day schedule

| Day | A (device) | B (gateway) | C (dashboard/docs) | D (ML/bench) |
|---|---|---|---|---|
| **Sat 26 Sep** | WP1 pin pair + server bring-up | WP2 CI | WP3 README structure + credits | WP5 golden queries |
| **Sun 27 Sep** | WP4 float16 | WP1 rehearsals in server mode, stats, logs | WP6 "Why here?" | WP5 eval script + numbers |
| **Mon 28 Sep** | WP7 kill/start commands + counters | WP1 docs; review WP4 on the gateway | WP7 UI counters; WP3 hero GIF | WP8 kappa; regenerate BENCHMARKS |
| **Tue 29 Sep** | **Feature freeze.** Bug fixes | `rehearse --runs 10` (server mode) | WP9 docs hygiene | README numbers match BENCHMARKS |
| **Wed 30 Sep** | Buffer | Buffer | Final README pass; H3 posts | H4 submission by 18:00 |
| 1–10 Oct | F1 partial snapshots | F1 gateway endpoint; F4 | F3 auto mode; F4 panel | F2 ranking; F5 drills |

## 4. Definition of done for the freeze

- [ ] `pytest` green locally and in CI; badge on the README
- [ ] 10/10 rehearsals in **server** mode, logged with mode and commit
- [ ] Pinned `qdrant-client` / `qdrant/qdrant` pair; no version warning
- [ ] New bandwidth number measured with float16 transport
- [ ] Retrieval table (hybrid vs dense vs BM25) in BENCHMARKS and README
- [ ] README: GIF, diagram, Qdrant calls, Prove-it, PS3 checklist, credits, team
- [ ] Every README number traceable to `docs/BENCHMARKS.md`
- [ ] No tool attribution anywhere (`AGENT.md` §9 check)
- [ ] Commits from every member; submission filed by 18:00 on 30 Sep
