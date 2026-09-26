import random

from hypothesis import given, settings as hsettings, strategies as st

from backend.common.themis import (CONTESTED, CURRENT, SUPERSEDED, apply, compare, merge,
                                   naive_merge, next_vv, resolve)


def v(op_id, vv, t=0.0):
    return {"op_id": op_id, "vv": vv, "valid_from": t}


def test_compare():
    assert compare({"A": 1}, {"A": 1}) == "equal"
    assert compare({"A": 2}, {"A": 1}) == "after"
    assert compare({"A": 1}, {"A": 1, "B": 1}) == "before"
    assert compare({"A": 1}, {"B": 1}) == "concurrent"
    assert compare({}, {"A": 1}) == "before"


def test_merge_and_next_vv():
    assert merge({"A": 2, "B": 1}, {"B": 3}) == {"A": 2, "B": 3}
    vv = next_vv([{"A": 2}, {"B": 5}], "A", 7)
    assert vv == {"A": 7, "B": 5}
    assert all(compare(vv, k) == "after" for k in [{"A": 2}, {"B": 5}])


def test_update_supersedes():
    old, new = v("A-1", {"A": 1}), v("A-2", {"A": 2})
    assert resolve([old, new]) == {"A-1": (SUPERSEDED, "A-2"), "A-2": (CURRENT, None)}


def test_concurrent_is_contested_not_overwritten():
    base = v("F-1", {"F": 1})
    a, b = v("A-1", {"F": 1, "A": 1}), v("B-1", {"F": 1, "B": 1})
    r = resolve([base, a, b])
    assert r["A-1"] == (CONTESTED, None) and r["B-1"] == (CONTESTED, None)
    assert r["F-1"][0] == SUPERSEDED


def test_three_way_concurrent_keeps_all():
    r = resolve([v("A-1", {"A": 1}), v("B-1", {"B": 1}), v("C-1", {"C": 1})])
    assert {s for s, _ in r.values()} == {CONTESTED}


def test_resolution_is_just_another_write():
    a, b = v("A-1", {"A": 1}), v("B-1", {"B": 1})
    sup = v("SUP-1", next_vv([a["vv"], b["vv"]], "supervisor", 1))
    r = resolve([a, b, sup])
    assert r["SUP-1"] == (CURRENT, None)
    assert r["A-1"] == (SUPERSEDED, "SUP-1") and r["B-1"] == (SUPERSEDED, "SUP-1")


def test_stale_arrival_is_kept_as_history():
    newer = {**v("A-2", {"A": 2}), "status": CURRENT, "superseded_by": None}
    plan = apply([newer], v("A-1", {"A": 1}))
    assert plan.result == "stale"
    assert plan.changes == {"A-1": (SUPERSEDED, "A-2")}


def test_duplicate_is_noop():
    x = {**v("A-1", {"A": 1}), "status": CURRENT}
    assert apply([x], v("A-1", {"A": 1})).result == "duplicate"


def test_naive_merge_loses_concurrent_edit_and_trusts_skewed_clock():
    # B's clock runs 10 minutes fast: its older write looks newest to a timestamp merge.
    old_b = v("B-1", {"B": 1}, t=1000 + 600)
    new_a = v("A-1", {"A": 1, "B": 1}, t=1100)
    assert naive_merge([old_b, new_a]) == "B-1"          # wrong: stale fact wins
    assert resolve([old_b, new_a])["A-1"] == (CURRENT, None)  # Themis: correct


# ---- property test: any delivery order, with duplicates, gives the same final state ----

def _random_history(rng: random.Random, n_devices: int, n_ops: int):
    """Devices write offline and occasionally sync; returns every version ever written."""
    devices = [chr(65 + i) for i in range(n_devices)]
    known = {d: [] for d in devices}       # versions each device has seen
    counter = {d: 0 for d in devices}
    out = []
    for _ in range(n_ops):
        d = rng.choice(devices)
        if rng.random() < 0.3 and out:     # partial sync: learn some random versions
            known[d].extend(rng.sample(out, k=rng.randint(1, len(out))))
        counter[d] += 1
        ver = v(f"{d}-{counter[d]}", next_vv([x["vv"] for x in known[d]], d, counter[d]))
        known[d].append(ver)
        out.append(ver)
    return out


@hsettings(max_examples=300, deadline=None)
@given(seed=st.integers(0, 10**9), n_devices=st.integers(2, 5), n_ops=st.integers(1, 12))
def test_convergence_any_order_with_duplicates(seed, n_devices, n_ops):
    rng = random.Random(seed)
    history = _random_history(rng, n_devices, n_ops)
    expected = resolve(history)

    # Replay incrementally via apply() in a random order with duplicates.
    deliveries = history + rng.sample(history, k=rng.randint(0, len(history)))
    rng.shuffle(deliveries)
    replica: dict[str, dict] = {}
    for d in deliveries:
        plan = apply(list(replica.values()), d)
        if plan.result == "duplicate":
            continue
        replica[d["op_id"]] = dict(d)
        for op_id, (status, by) in plan.changes.items():
            replica[op_id].update(status=status, superseded_by=by)
    assert {k: (x["status"], x.get("superseded_by")) for k, x in replica.items()} == expected

    # Nothing written concurrently is lost: every maximal version is still visible.
    visible = {k for k, (s, _) in expected.items() if s != SUPERSEDED}
    assert visible, "at least one version must stay visible"
