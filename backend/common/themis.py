"""Themis: version-vector conflict resolution, shared by devices and the gateway.

A version vector (vv) maps device_id -> how many of that device's writes this version has seen.

- a dominates b  (a is newer): a has seen everything b has, and more.
- concurrent: neither has seen the other; both were written independently offline.

Themis never picks a winner between concurrent versions. For one entity it computes:
- the maximal versions (dominated by nobody): 1 -> "current", 2+ -> all "contested"
- every other version -> "superseded", pointing at a maximal version that dominates it

The result depends only on the *set* of versions, never on arrival order or on duplicates.
That's why every replica converges (checked by bench/simulate.py and tests/test_themis.py).
"""
from dataclasses import dataclass, field

CURRENT, SUPERSEDED, CONTESTED = "current", "superseded", "contested"


def compare(a: dict, b: dict) -> str:
    """Return 'equal', 'after' (a newer), 'before' (a older) or 'concurrent'."""
    keys = a.keys() | b.keys()
    ge = all(a.get(k, 0) >= b.get(k, 0) for k in keys)
    le = all(a.get(k, 0) <= b.get(k, 0) for k in keys)
    if ge and le:
        return "equal"
    if ge:
        return "after"
    if le:
        return "before"
    return "concurrent"


def merge(*vvs: dict) -> dict:
    """Pointwise max: a vv that has seen everything any input has seen."""
    out: dict = {}
    for vv in vvs:
        for k, v in vv.items():
            out[k] = max(out.get(k, 0), v)
    return out


def next_vv(known: list[dict], device_id: str, counter: int) -> dict:
    """vv for a new local write: dominates everything this replica knows for the entity."""
    vv = merge(*known) if known else {}
    vv[device_id] = max(counter, vv.get(device_id, 0) + 1)
    return vv


def resolve(versions: list[dict]) -> dict[str, tuple[str, str | None]]:
    """Map op_id -> (status, superseded_by) for all versions of ONE entity.

    Each version is a dict with at least "op_id" and "vv". Duplicate op_ids count once.
    """
    uniq = {v["op_id"]: v for v in versions}
    vs = sorted(uniq.values(), key=lambda v: v["op_id"])
    maximal = [v for v in vs if not any(compare(w["vv"], v["vv"]) == "after" for w in vs)]
    top_status = CURRENT if len(maximal) == 1 else CONTESTED
    out: dict[str, tuple[str, str | None]] = {}
    for v in vs:
        if v in maximal:
            out[v["op_id"]] = (top_status, None)
        else:
            by = next(m["op_id"] for m in maximal if compare(m["vv"], v["vv"]) == "after")
            out[v["op_id"]] = (SUPERSEDED, by)
    return out


@dataclass
class Plan:
    result: str                                   # "applied" | "stale" | "duplicate"
    changes: dict = field(default_factory=dict)   # op_id -> (status, superseded_by), only what changed


def apply(existing: list[dict], new: dict) -> Plan:
    """What happens when `new` arrives at a replica that already holds `existing`.

    `existing` versions carry their current "status" (and optionally "superseded_by"),
    so the plan lists only the writes the replica actually has to make.
    """
    if any(v["op_id"] == new["op_id"] for v in existing):
        return Plan("duplicate")
    statuses = resolve(existing + [new])
    changes = {}
    for v in existing + [new]:
        target = statuses[v["op_id"]]
        if v is new or (v.get("status"), v.get("superseded_by")) != target:
            changes[v["op_id"]] = target
    result = "stale" if statuses[new["op_id"]][0] == SUPERSEDED else "applied"
    return Plan(result, changes)


def naive_merge(versions: list[dict]) -> str:
    """The reference pattern this project replaces: latest wall-clock timestamp wins.

    Used only by the benchmark and the side-by-side demo. It silently drops concurrent
    edits and trusts device clocks, which can be skewed.
    """
    return max(versions, key=lambda v: (v.get("valid_from", 0), v["op_id"]))["op_id"]
