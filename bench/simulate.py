"""Multi-device convergence simulation for Themis.

Each run: N devices write to a few entities while offline, occasionally syncing parts of
what they know; then every version is delivered to every replica (gateway + N devices)
in a different random order, with duplicate sends. Checks:
  1. every replica ends in exactly the same state
  2. no concurrent edit is lost: every maximal version is still visible (current/contested)

    python -m bench.simulate --runs 1000 --devices 5
"""
import argparse
import random

from backend.common.themis import SUPERSEDED, apply, compare, next_vv, resolve


def history(rng: random.Random, n_devices: int, n_ops: int, n_entities: int) -> list[dict]:
    devs = [f"D{i}" for i in range(n_devices)]
    known = {d: [] for d in devs}
    counter = {d: 0 for d in devs}
    out = []
    for _ in range(n_ops):
        d = rng.choice(devs)
        if out and rng.random() < 0.3:
            known[d].extend(rng.sample(out, k=rng.randint(1, len(out))))
        ek = f"e{rng.randrange(n_entities)}"
        counter[d] += 1
        vv = next_vv([v["vv"] for v in known[d] if v["entity_key"] == ek], d, counter[d])
        v = {"op_id": f"{d}-{counter[d]}", "entity_key": ek, "vv": vv}
        known[d].append(v)
        out.append(v)
    return out


def replay(rng: random.Random, versions: list[dict]) -> dict:
    deliveries = versions + rng.sample(versions, k=rng.randint(0, len(versions)))
    rng.shuffle(deliveries)
    state: dict[str, dict] = {}
    for v in deliveries:
        same = [x for x in state.values() if x["entity_key"] == v["entity_key"]]
        plan = apply(same, v)
        if plan.result == "duplicate":
            continue
        state[v["op_id"]] = dict(v)
        for op_id, (st, by) in plan.changes.items():
            state[op_id].update(status=st, superseded_by=by)
    return {k: (x["status"], x["superseded_by"]) for k, x in sorted(state.items())}


def run(runs: int, devices: int, seed: int = 1) -> dict:
    rng = random.Random(seed)
    converged = lost = matches = 0
    contested_runs = 0
    for _ in range(runs):
        hist = history(rng, devices, rng.randint(5, 30), rng.randint(1, 4))
        replicas = [replay(rng, hist) for _ in range(devices + 1)]      # + gateway
        if all(r == replicas[0] for r in replicas):
            converged += 1
        final = replicas[0]
        for ek in {v["entity_key"] for v in hist}:
            vs = [v for v in hist if v["entity_key"] == ek]
            maximal = [v for v in vs if not any(compare(w["vv"], v["vv"]) == "after" for w in vs)]
            if any(final[v["op_id"]][0] == SUPERSEDED for v in maximal):
                lost += 1
            if len(maximal) > 1:
                contested_runs += 1
        expected = {}
        for ek in {v["entity_key"] for v in hist}:
            expected.update(resolve([v for v in hist if v["entity_key"] == ek]))
        matches += final == dict(sorted(expected.items()))
    return {"runs": runs, "devices": devices, "replicas_per_run": devices + 1, "converged": converged, "matches_batch_resolve": matches,
            "lost_concurrent_edits": lost, "entities_with_conflicts": contested_runs}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=1000)
    ap.add_argument("--devices", type=int, default=5)
    a = ap.parse_args()
    print(run(a.runs, a.devices))
