"""Memory lifecycle: Temporary -> Active -> Stale -> Archived.

Smaran does not keep everything at the same weight forever. A memory's state is a pure function
of its type, its status and its age, so nothing is swept or deleted in the background, the same
memory always gets the same state at the same time, and the reason is always available:

    temporary   transient chat (an event or a note) in its first days: kept, not yet trusted as lasting knowledge
    active      currently relevant
    stale       past its freshness window: still retrievable, but ranked lower and flagged
    archived    hidden from recall (never deleted): superseded, closed long ago, or expired

Windows are in days since the memory was written (or, for a scheduled item, since its time passed):

    kind                              temporary  stale    archived   persistence
    decision                          -          never    on superseded    persistent until superseded
    preference                        -          never    on superseded    persistent until contradicted
    fact                              -          180 d    365 d            high
    schedule fact                     -          due+1 d  due+14 d         until the time passes
    task, open                        -          never    -                until closed
    task, done or cancelled           -          3 d      14 d             decays quickly
    event / note (transient chat)     3 d        14 d     30 d             decays
"""
from dataclasses import dataclass

DAY = 86400

# kind -> (temporary_days, stale_days, archive_days, persistence label); None = does not apply
WINDOWS = {
    "event": (3, 14, 30, "decays"),
    "note": (3, 14, 30, "decays"),
    "fact": (None, 180, 365, "high"),
    "personal": (None, 180, 365, "high"),
}
CLOSED_TASK = (None, 3, 14, "decays quickly")
SCHEDULE_AFTER = (None, 1, 14, "until the time passes")
PERSISTENT = {"decision": "persistent until superseded", "preference": "persistent until contradicted"}

STATES = ("temporary", "active", "stale", "archived")


@dataclass
class Lifecycle:
    state: str
    reason: str
    persistence: str

    def as_dict(self) -> dict:
        return {"state": self.state, "reason": self.reason, "persistence": self.persistence}


def _age_state(age_days: float, win: tuple, what: str) -> tuple[str, str]:
    temp, stale, arch, _ = win
    if arch is not None and age_days >= arch:
        return "archived", f"{what} is {age_days:.0f} days old (archived after {arch})"
    if stale is not None and age_days >= stale:
        return "stale", f"{what} is {age_days:.0f} days old (stale after {stale})"
    if temp is not None and age_days < temp:
        return "temporary", f"{what} is {age_days:.1f} days old (temporary for the first {temp})"
    return "active", f"{what} is {age_days:.0f} days old"


def lifecycle(p: dict, now: float) -> Lifecycle:
    """State of one memory payload at time `now`."""
    kind = p.get("kind") or "note"
    if p.get("status") == "superseded":
        by = p.get("superseded_by")
        return Lifecycle("archived", "replaced by a newer version" + (f" ({by})" if by else "") + "; kept as history",
                         "history")
    age = max((now - (p.get("valid_from") or now)) / DAY, 0.0)
    if kind == "task":
        if p.get("task_status", "open") == "open":
            return Lifecycle("active", "task is still open", "until closed")
        st, why = _age_state(age, CLOSED_TASK, f"task closed as {p.get('task_status')}")
        return Lifecycle(st, why, CLOSED_TASK[3])
    if kind in PERSISTENT:
        return Lifecycle("active", f"{kind}s are {PERSISTENT[kind]}", PERSISTENT[kind])
    tags = p.get("tags") or []
    if "schedule" in tags and p.get("due"):
        since = (now - p["due"]) / DAY
        if since < 0:
            return Lifecycle("active", "scheduled time is still ahead", SCHEDULE_AFTER[3])
        st, why = _age_state(since, SCHEDULE_AFTER, "scheduled time passed; it")
        return Lifecycle(st, why, SCHEDULE_AFTER[3])
    win = WINDOWS.get(kind)
    if win is None:
        return Lifecycle("active", "no expiry rule for this kind", "high")
    st, why = _age_state(age, win, "memory")
    return Lifecycle(st, why, win[3])


def summarize(payloads: list[dict], now: float) -> dict:
    """Counts per state and the archived/stale examples, for the dashboard and the demo."""
    counts = {s: 0 for s in STATES}
    examples: dict[str, list[dict]] = {"stale": [], "archived": []}
    for p in sorted(payloads, key=lambda q: q.get("status") == "superseded"):     # aged-out memories before version history
        lc = lifecycle(p, now)
        counts[lc.state] += 1
        if lc.state in examples and len(examples[lc.state]) < 5:
            examples[lc.state].append({"op_id": p["op_id"], "text": p["text"].split(" Original:")[0][:110],
                                       "kind": p.get("kind"), "reason": lc.reason})
    return {"counts": counts, "total": sum(counts.values()), "examples": examples,
            "note": "Archived memories are hidden from recall but never deleted."}
