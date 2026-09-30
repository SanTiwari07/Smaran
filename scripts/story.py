"""The judge-facing story, run against the live stack with pass/fail checks.

    python scripts/story.py            # one run
    python scripts/story.py --runs 3   # rehearse; appends a summary line to logs/story-rehearsal.log

Needs the stack running (python scripts/demo.py start-all [--qdrant embedded]).
Every step calls the same HTTP routes the dashboard's Control Center uses.
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import httpx  # noqa: E402

from backend.common.config import settings  # noqa: E402

GW = settings.gateway_url
PHONE = f"http://127.0.0.1:{settings.device_ports['A']}"
LAPTOP = f"http://127.0.0.1:{settings.device_ports['B']}"
C = httpx.Client(timeout=90)


def post(url, **kw):
    r = C.post(url, **kw)
    r.raise_for_status()
    return r.json()


def get(url, **kw):
    r = C.get(url, **kw)
    r.raise_for_status()
    return r.json()


def chat(dev, text):
    return post(f"{dev}/companion/chat", json={"text": text})


def online(dev, on):
    post(f"{dev}/online", json={"online": on})


def sync_all():
    for d in (PHONE, LAPTOP, PHONE):
        post(f"{d}/sync-now")


class Run:
    def __init__(self):
        self.results = []

    def check(self, name, ok, detail=""):
        self.results.append((name, bool(ok), detail))
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  ({detail})" if detail else ""))
        return ok


def once(quiet=False) -> Run:
    t = Run()
    print("reset")
    post(f"{GW}/admin/reset", params={"seed": True})
    for d in (PHONE, LAPTOP):
        post(f"{d}/admin/reset", params={"online": True})

    print("1-2. teach Smaran, then load two weeks of history")
    r = chat(PHONE, "I'm working on my final-year project. We're using PostgreSQL and Qdrant. My teammate handles the frontend and I'll handle the backend.")
    t.check("statement becomes structured memories", sum(a["state"] == "executed" for a in r["actions"]) >= 3,
            f"{len(r['actions'])} actions, planner={r['planner']}")
    s = post(f"{PHONE}/companion/seed-story")
    t.check("history replayed through the real agent", s["memories_written"] >= 12 and s["private"] == 2, str(s))
    sync_all()

    print("3. retrieve naturally (no shared keywords)")
    r = chat(PHONE, "Which DB are we going with for the capstone?")
    t.check("answer names PostgreSQL", "PostgreSQL" in r["reply"], f"{r['route']['route']} {r['latency_ms']:.0f} ms: {r['reply'][:80]}")

    print("4-6. link off; keep using Smaran")
    online(PHONE, False)
    online(LAPTOP, False)
    r = chat(PHONE, "What are the remaining tasks for my project?")
    t.check("offline: task question answered from local memory", "API integration" in r["reply"] and not r["online"],
            f"{r['route']['route']}: {r['reply'][:90]}")
    r = chat(PHONE, "When is the capstone review meeting?")
    t.check("offline: schedule question answered", "3 PM" in r["reply"], r["reply"][:90])

    print("7. agent acts offline")
    q0 = get(f"{PHONE}/state")["outbox_depth"]
    r = chat(PHONE, "Remind me tomorrow evening to finish the API integration")
    a = r["actions"][0]
    t.check("agent set a reminder (validated, executed, verified)", a["tool"] == "set_reminder" and a["state"] == "executed" and a.get("verified"),
            a["message"])
    t.check("the change is queued, not lost", get(f"{PHONE}/state")["outbox_depth"] > q0, f"queue {q0} -> {get(f'{PHONE}/state')['outbox_depth']}")
    r = chat(PHONE, "Cancel the task prepare the capstone demo slides")
    t.check("destructive action waits for confirmation", r["actions"][0]["state"] == "pending_confirmation", r["actions"][0]["message"])

    print("8-10. two devices edit the same fact while offline")
    chat(PHONE, "The capstone review meeting is at 4 PM.")
    time.sleep(1.1)
    chat(LAPTOP, "The capstone review meeting is at 5 PM.")

    print("11-12. reconnect and sync")
    queued = get(f"{PHONE}/state")["outbox_depth"] + get(f"{LAPTOP}/state")["outbox_depth"]
    online(PHONE, True)
    online(LAPTOP, True)
    sync_all()
    t.check("queues drained", get(f"{PHONE}/state")["outbox_depth"] == 0 and get(f"{LAPTOP}/state")["outbox_depth"] == 0, f"{queued} ops queued before")
    conflicts = get(f"{PHONE}/companion/conflicts")
    t.check("conflict detected and explained on both devices", len(conflicts) == 1 and len(get(f"{LAPTOP}/companion/conflicts")) == 1
            and "concurrent" in conflicts[0]["why"], f"{[v['device_label'] + ': ' + v['text'][-8:] for v in conflicts[0]['versions']] if conflicts else 'none'}")
    t.check("nothing overwritten: both versions live on the server", len(get(f"{GW}/contested")[0]["versions"]) == 2)

    print("13. resolve")
    pick = conflicts[0]["suggestion"]["op_id"]
    post(f"{GW}/resolve", json={"entity_key": conflicts[0]["entity_key"], "op_id": pick, "author": "you"})
    sync_all()
    t.check("conflict resolved on both devices", not get(f"{PHONE}/companion/conflicts") and not get(f"{LAPTOP}/companion/conflicts"))
    r = chat(LAPTOP, "When is the capstone review meeting?")
    t.check("laptop now answers with the resolved time", "5 PM" in r["reply"], r["reply"][:80])

    print("14. privacy")
    aud = get(f"{GW}/audit")
    t.check("cloud holds 0 private records and 0 PII matches", aud["ok"], f"{aud['total']} points, {aud['private_count']} private, {aud['pii_hits']} PII")
    t.check("private items stayed in Krypta on the phone", get(f"{PHONE}/companion/status")["memory"]["counts"]["krypta"] >= 2)

    print("15. observability")
    tr = get(f"{PHONE}/companion/traces")
    t.check("every request has a route, latency and top-k on record", len(tr) > 5 and all("route" in x and "latency_ms" in x for x in tr))
    au = get(f"{PHONE}/companion/audit")
    t.check("audit log holds the agent's actions", any(x["tool"] == "set_reminder" and x["verified"] == 1 for x in au))
    return t


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=1)
    args = ap.parse_args()
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    ok_runs = 0
    for i in range(args.runs):
        print(f"=== run {i + 1}/{args.runs}")
        t0 = time.time()
        try:
            res = once()
            ok = all(x[1] for x in res.results)
            failed = [x[0] for x in res.results if not x[1]]
        except Exception as e:  # noqa: BLE001
            ok, failed = False, [f"exception: {e!r}"]
        ok_runs += ok
        print(f"=== run {i + 1}: {'PASS' if ok else 'FAIL'} in {time.time() - t0:.1f}s {failed if failed else ''}")
    line = {"ts": time.strftime("%Y-%m-%d %H:%M"), "commit": commit, "runs": args.runs, "passed": ok_runs,
            "gateway": get(f"{GW}/health").get("server"), "local_model": get(f"{PHONE}/companion/status")["ai"]["local"]}
    (ROOT / "logs").mkdir(exist_ok=True)
    with open(ROOT / "logs" / "story-rehearsal.log", "a", encoding="utf8") as f:
        f.write(json.dumps(line) + "\n")
    print(f"{ok_runs}/{args.runs} runs passed")
    sys.exit(0 if ok_runs == args.runs else 1)


if __name__ == "__main__":
    main()
