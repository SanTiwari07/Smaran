# On-site build playbook

The Code Cubicle 5.0 final included an 8-hour on-site build, and the 6.0 final runs 09:00–18:00. Judges may ask for a change live. These are the likely requests, each with the exact files to touch, the test to add, and how to show it. Rehearse each one at least once before 11 Oct; target 30 minutes or less, tests green.

Always finish with:

```bash
.venv/Scripts/python -m pytest
.venv/Scripts/python scripts/demo.py rehearse --runs 3
```

## 1. "Add a new kind of personal data" (for example a vehicle number or an employee ID)

1. `backend/common/pii.py`: add one entry to `RULES`, e.g. `"vehicle_in": re.compile(r"\b[A-Z]{2}[\s-]?\d{1,2}[\s-]?[A-Z]{1,3}[\s-]?\d{4}\b")`.
2. `backend/tests/test_pii.py`: one positive and one negative example.
3. Nothing else: the router (device) and the gateway (defence in depth) both call `find_pii`.
4. Show it: write a note with the new identifier on device A. It lands in **Krypta** with *"PII rule matched: vehicle_in"*, and the server audit stays at 0.

## 2. "Add a new machine"

1. `backend/common/config.py`: add it to `MACHINES` (the dashboard reads the list from `/machines`).
2. `seed/manuals/fleet.json`: add a `status` line and one or two `manual` lines for it.
3. `demo.py reset base` reseeds the gateway; both devices pull the new manuals into Agora.
4. Show it: search the machine's name on a device, offline.

## 3. "Add a new note type" (for example `inspection`)

1. `backend/common/schema.py`: add it to `Kind`.
2. `frontend/src/api/types.ts` (`Kind`) and `frontend/src/views/MemorySearch.tsx` (`KINDS`): add it to the picker.
3. Decide whether it describes a single changing fact. If yes, `entity_key_for` in `schema.py` should return a key for it (like `status`), so Themis tracks conflicts on it.
4. Test: extend `test_e2e.py` with one note of the new type that syncs.

## 4. "Make it handle Hindi / Hinglish notes"

1. `.env`: `DENSE_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384-d, so `DENSE_DIM` stays 384; FastEmbed supports it). Needs internet once: `python scripts/setup_models.py`.
2. Retrain the classifier on the new embeddings: `python -m ml.train` (the saved model is tied to the embedding model).
3. `demo.py stop-all`, `demo.py wipe`, `demo.py start-all`: the old shards hold vectors from the other model.
4. BM25 stays English-stemmed (`Bm25Config(language="english")` in `backend/device/embed.py`); Hinglish written in Latin script still matches on machine IDs and part numbers.
5. Re-run `python -m bench.bench retrieval` and report the new numbers, whatever they are.

## 5. "Change what counts as safety-critical"

1. `backend/device/classifier.py`: edit the `SAFETY` keyword pattern.
2. Test: extend `test_critical_first` in `test_e2e.py`.
3. Show it: two offline notes, the new safety one jumps to the top of the outbox.

## 6. "Add a third device"

1. `.env`: `DEVICE_C_PORT=8003` and add `"C"` to `device_ports` in `backend/common/config.py`.
2. `frontend/src/api/client.ts`: add `C` to `DEVICES`.
3. `demo.py start-all` starts every device in `device_ports`.
4. Themis needs no change: version vectors take any number of devices (the convergence benchmark runs 5).

## 7. "Show us the data on the server"

Open http://localhost:6333/dashboard → collection `smaran`. Filter `status` = `contested` during beat 3. The **Prove it** card on the dashboard re-runs the privacy audit, the latency check, the conflict and convergence benchmarks, and the idempotent resend.

## What to say if a request doesn't fit

Scope it out loud: what the change is, which files it touches, which test proves it. A clear plan for a larger request is better than a rushed change that breaks the demo.
