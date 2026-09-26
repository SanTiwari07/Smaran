"""Smaran demo runner (cross-platform; replaces demo.sh).

    python scripts/demo.py start-all [--qdrant server|embedded] [--no-frontend]
    python scripts/demo.py status
    python scripts/demo.py reset base|b1|b2|b3|b4|b5  # known state in a few seconds
    python scripts/demo.py play  b1|b2|b3|b4|b5       # run a beat's actions and check them
    python scripts/demo.py rehearse [--runs 10] [--beats b1 b2 b3 b4 b5]
                                                      # reset+play beats, log to logs/rehearsal.log
    python scripts/demo.py kill A|B                   # hard-kill a device process (no clean shutdown)
    python scripts/demo.py start A|B                  # start one device again (after kill or b5)
    python scripts/demo.py stop-all

Beats (plan section 10):
  b1 offline memory   A offline -> write a note -> search it locally
  b2 privacy          note with a phone number -> Krypta; server audit stays 0
  b3 conflict         A and B offline write different CNC-07 statuses -> online -> contested
  b4 belief over time supervisor resolves -> history shows what A believed before
  b5 pull the plug     A offline writes 3 notes -> A crashes right after the gateway stored them,
                       before it recorded the acks -> restart -> resend -> 0 duplicate memories
"""
import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import httpx  # noqa: E402

from backend.common.config import settings  # noqa: E402

PY = sys.executable
PIDS = ROOT / "runtime" / "pids.json"
LOGS = ROOT / "logs"
GW = settings.gateway_url
DEV = {d: f"http://127.0.0.1:{p}" for d, p in settings.device_ports.items()}
WIN = os.name == "nt"
EK = "machine:CNC-07/status"
BEATS = ["b1", "b2", "b3", "b4", "b5"]


# ---- process management ---------------------------------------------------------------
def spawn(name: str, cmd: list[str], cwd: Path = ROOT, env: dict | None = None) -> int:
    LOGS.mkdir(exist_ok=True)
    out = open(LOGS / f"{name}.out", "a", encoding="utf8")
    flags = (subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS) if WIN else 0
    p = subprocess.Popen(cmd, cwd=cwd, stdout=out, stderr=subprocess.STDOUT, env={**os.environ, **(env or {})},
                         creationflags=flags, start_new_session=not WIN)
    return p.pid


def wait_up(url: str, timeout: float = 90) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        try:
            if httpx.get(url, timeout=2).status_code < 500:
                return True
        except httpx.HTTPError:
            pass
        time.sleep(0.5)
    return False


def qdrant_server_up() -> bool:
    try:
        return httpx.get(f"{settings.qdrant_url}/readyz", timeout=2).status_code == 200
    except httpx.HTTPError:
        return False


def start_all(args) -> None:
    if PIDS.exists():
        print("already started (runtime/pids.json exists). Run stop-all first.")
        return
    mode = args.qdrant
    if mode == "server" and not qdrant_server_up():
        print("starting Qdrant Server (docker compose)...")
        r = subprocess.run(["docker", "compose", "-f", str(ROOT / "infra" / "docker-compose.yml"), "up", "-d"],
                           capture_output=True, text=True)
        if r.returncode != 0 or not wait_up(f"{settings.qdrant_url}/readyz", 60):
            print("Qdrant Server not available (is Docker Desktop running?). "
                  "Falling back to embedded mode: python scripts/demo.py start-all --qdrant embedded")
            print(r.stderr.strip()[-400:])
            return
    pids = {"gateway": spawn("gateway", [PY, "-m", "backend.gateway", "--qdrant", mode])}
    if not wait_up(f"{GW}/health"):
        print("gateway failed to start; see logs/gateway.out")
    for d in DEV:
        pids[f"device-{d}"] = spawn(f"device-{d}", [PY, "-m", "backend.device", "--id", d])
    if not args.no_frontend:
        npm = "npm.cmd" if WIN else "npm"
        pids["frontend"] = spawn("frontend", [npm, "run", "dev", "--", "--port", "5173", "--strictPort"], cwd=ROOT / "frontend")
    PIDS.parent.mkdir(exist_ok=True)
    PIDS.write_text(json.dumps(pids, indent=2))
    for d, url in DEV.items():
        print(f"device {d}: {'up' if wait_up(url + '/health') else 'FAILED (logs/device-' + d + '.out)'}  {url}")
    print(f"gateway: {GW}  (qdrant: {mode})")
    if not args.no_frontend:
        print("dashboard: http://localhost:5173" + ("" if wait_up("http://localhost:5173", 60) else "  (still starting; logs/frontend.out)"))
    reset("base")


def stop_all(_args=None) -> None:
    if not PIDS.exists():
        print("nothing to stop")
        return
    for name, pid in json.loads(PIDS.read_text()).items():
        if WIN:
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(pid)], capture_output=True)
        else:
            try:
                os.killpg(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        print(f"stopped {name} ({pid})")
    PIDS.unlink()


def _pids() -> dict:
    if not PIDS.exists():
        raise SystemExit("no runtime/pids.json: start the stack with start-all first")
    return json.loads(PIDS.read_text())


def _hard_kill(pid: int) -> None:
    if WIN:
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(pid)], capture_output=True)
    else:
        try:
            os.killpg(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def _down(url: str, timeout: float = 15) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        try:
            httpx.get(url, timeout=1)
        except httpx.HTTPError:
            return True
        time.sleep(0.3)
    return False


def kill_device(d: str) -> None:
    pids = _pids()
    _hard_kill(pids[f"device-{d}"])
    print(f"device {d}: {'killed' if _down(DEV[d] + '/health') else 'STILL UP'}")


def start_device(d: str) -> bool:
    pids = _pids()
    old = pids.get(f"device-{d}")
    if old:
        _hard_kill(old)          # no-op if it already died
        _down(DEV[d] + "/health", 5)
    pids[f"device-{d}"] = spawn(f"device-{d}", [PY, "-m", "backend.device", "--id", d])
    PIDS.write_text(json.dumps(pids, indent=2))
    up = wait_up(DEV[d] + "/health")
    print(f"device {d}: {'up' if up else 'FAILED (logs/device-' + d + '.out)'}  {DEV[d]}")
    return up


def status(_args=None) -> None:
    for name, url in {"gateway": GW, **{f"device-{d}": u for d, u in DEV.items()}}.items():
        try:
            print(f"{name:10} {httpx.get(url + '/health', timeout=2).json()}")
        except httpx.HTTPError as e:
            print(f"{name:10} DOWN ({e.__class__.__name__})")
    print(f"qdrant-server {'up' if qdrant_server_up() else 'down'} at {settings.qdrant_url}")


# ---- beat state -----------------------------------------------------------------------
HTTP = httpx.Client(timeout=60)   # one client: a new one per call costs ~0.2 s on Windows


def post(url: str, **kw) -> dict:
    r = HTTP.post(url, **kw)
    r.raise_for_status()
    return r.json()


def get(url: str, **kw):
    r = HTTP.get(url, **kw)
    r.raise_for_status()
    return r.json()


def note(d: str, text: str, kind: str = "observation", machine: str | None = None) -> dict:
    return post(f"{DEV[d]}/notes", json={"text": text, "kind": kind, "machine": machine, "author": f"tech-{d}"})


def online(d: str, value: bool) -> None:
    post(f"{DEV[d]}/online", json={"online": value})


def sync(d: str) -> dict:
    return post(f"{DEV[d]}/sync-now")


def reset(beat: str) -> None:
    t = time.time()
    post(f"{GW}/admin/reset", params={"seed": True})
    for d in DEV:
        post(f"{DEV[d]}/admin/reset", params={"online": True})
        sync(d)
    if beat == "b1":
        online("A", False)
    elif beat == "b3":
        online("A", False)
        online("B", False)
    elif beat == "b4":
        _make_conflict()
    elif beat == "b5":
        online("A", False)
    print(f"reset {beat} in {time.time() - t:.1f}s")


def _make_conflict() -> tuple[str, str]:
    online("A", False)
    online("B", False)
    a = note("A", "CNC-07 running normally after bearing replacement, vibration normal", "status", "CNC-07")
    time.sleep(0.2)
    b = note("B", "CNC-07 still vibrating at high RPM, do not run above 8000 rpm", "status", "CNC-07")
    online("A", True)
    online("B", True)
    sync("A"); sync("B"); sync("A")
    return a["memory"]["op_id"], b["memory"]["op_id"]


# ---- beat actions + checks (used for rehearsal and the video) ----------------------------
def check(ok: bool, what: str) -> bool:
    print(f"  [{'PASS' if ok else 'FAIL'}] {what}")
    return ok


def play(beat: str) -> bool:
    ok = True
    if beat == "b1":
        w = note("A", "CNC-07 bearing replaced, vibration normal", "fix", "CNC-07")
        s = get(f"{DEV['A']}/search", params={"q": "CNC-07 bearing trouble"})
        top = s["results"][0]
        ok &= check(not get(f"{DEV['A']}/state")["online"], "device A is offline")
        ok &= check(top["payload"]["op_id"] == w["memory"]["op_id"], f"new note is the top hit ({top['shard']})")
        ok &= check(s["answered"] == "local", f"answered locally in {s['latency_ms']} ms")
    elif beat == "b2":
        w = note("A", "Call Ravi on 9876543210 about the night shift swap")
        ok &= check(w["shard"] == "krypta", f"stored in Krypta: {w['decision']['reason']}")
        sync("A")
        a = get(f"{GW}/audit")
        ok &= check(a["ok"], f"server audit: {a['private_count']} private, {a['pii_hits']} PII hits")
    elif beat == "b3":
        a = note("A", "CNC-07 running normally after bearing replacement, vibration normal", "status", "CNC-07")
        b = note("B", "CNC-07 still vibrating at high RPM, do not run above 8000 rpm", "status", "CNC-07")
        crit = note("B", "PRESS-02 smoke from the motor, pressed e-stop", "observation", "PRESS-02")
        order = [o["op_id"] for o in get(f"{DEV['B']}/outbox")]
        ok &= check(order[0] == crit["memory"]["op_id"], "safety-critical note is first in B's outbox")
        online("A", True); online("B", True)
        sync("A"); sync("B"); sync("A")
        for d in DEV:
            st = {m["op_id"]: m["status"] for m in get(f"{DEV[d]}/memories", params={"status": "contested"})}
            ok &= check(a["memory"]["op_id"] in st and b["memory"]["op_id"] in st, f"device {d} shows CNC-07 contested")
        ok &= check([g["entity_key"] for g in get(f"{GW}/contested")] == [EK], "gateway lists the conflict")
    elif beat == "b4":
        before = time.time()
        contested = get(f"{GW}/contested")[0]["versions"]
        keep = next(v for v in contested if v["device_id"] == "B")
        r = post(f"{GW}/resolve", json={"entity_key": EK, "op_id": keep["op_id"]})
        sync("A"); sync("B")
        now = {g["entity_key"]: g for g in get(f"{DEV['A']}/history")}
        then = {g["entity_key"]: g for g in get(f"{DEV['A']}/history", params={"at": before})}
        ok &= check(now[EK]["status"] == "current" and now[EK]["versions"][0]["op_id"] == r["op_id"],
                    "after resolving, A believes the supervisor's version")
        ok &= check(then[EK]["status"] == "contested", "history: before resolving, A saw a contested status")
        ok &= check(get(f"{GW}/contested") == [], "no conflicts left")
    elif beat == "b5":
        texts = ["CNC-12 coolant concentration low, topped up to 7 percent",
                 "ROBOT-ARM-5 sparks at the cable carrier, cell stopped",
                 "LATHE-03 chuck jaws replaced, runout back to 0.01 mm"]
        ops = [note("A", t, "observation")["memory"]["op_id"] for t in texts]
        queued = [o for o in ops if o in {x["op_id"] for x in get(f"{DEV['A']}/outbox")}]
        ok &= check(len(queued) == len(texts), f"{len(queued)} notes queued in A's outbox while offline")
        try:
            HTTP.post(f"{DEV['A']}/admin/crash", timeout=10)
        except httpx.HTTPError:
            pass                                   # the process died mid-request, as intended
        ok &= check(_down(DEV["A"] + "/health"), "device A crashed after the gateway stored the batch")
        gw_a = {d["device_id"]: d for d in get(f"{GW}/stats")["devices"]}.get("A", {})
        ok &= check(gw_a.get("ops") == len(queued), f"gateway stored {gw_a.get('ops')} of A's ops before the crash")
        ok &= check(start_device("A"), "device A restarted")
        st = get(f"{DEV['A']}/state")
        rec = st.get("recovery") or {}
        ok &= check(rec.get("pending") == len(queued) and st["outbox_depth"] == len(queued),
                    f"restart found {rec.get('pending')} unacknowledged ops in the outbox")
        online("A", True)
        sync("A")
        st = get(f"{DEV['A']}/state")
        gw_a = {d["device_id"]: d for d in get(f"{GW}/stats")["devices"]}["A"]
        ok &= check(st["outbox_depth"] == 0, "outbox drained after the resend")
        ok &= check(gw_a["duplicates"] == len(queued), f"gateway ignored {gw_a['duplicates']} resent duplicates")
        on_server = [m["op_id"] for m in get(f"{GW}/memories") if m["op_id"] in queued]
        ok &= check(sorted(on_server) == sorted(queued), f"each op stored exactly once ({len(on_server)} on the server)")
        points = get(f"{GW}/stats")["points"]
        ok &= check(st["counts"]["agora"] == points,
                    f"A's fleet mirror is complete after the crash ({st['counts']['agora']} of {points})")
    return ok


def _commit() -> str:
    r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT,
                           capture_output=True, text=True).stdout.strip()
    return (r.stdout.strip() or "unknown") + ("+dirty" if dirty else "")


def rehearse(runs: int, beats: list[str]) -> None:
    passed = 0
    mode = get(f"{GW}/health")["server"]          # e.g. server:http://127.0.0.1:6333/smaran
    commit = _commit()
    print(f"rehearsing {' '.join(beats)} x{runs} against {mode} at {commit}")
    with (LOGS / "rehearsal.log").open("a", encoding="utf8") as log:
        for i in range(1, runs + 1):
            results = {}
            for beat in beats:
                print(f"run {i} {beat}")
                try:
                    reset(beat)
                    results[beat] = play(beat)
                except Exception as e:  # noqa: BLE001
                    print(f"  [FAIL] {beat}: {e}")
                    results[beat] = False
            passed += all(results.values())
            log.write(json.dumps({"ts": time.time(), "run": i, "qdrant": mode, "commit": commit, **results}) + "\n")
    print(f"\n{passed}/{runs} full rehearsals passed against {mode} (logged to logs/rehearsal.log)")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("start-all")
    s.add_argument("--qdrant", choices=["server", "embedded"], default=settings.qdrant_mode)
    s.add_argument("--no-frontend", action="store_true")
    sub.add_parser("stop-all")
    sub.add_parser("status")
    r = sub.add_parser("reset")
    r.add_argument("beat", choices=["base", *BEATS])
    p = sub.add_parser("play")
    p.add_argument("beat", choices=BEATS)
    h = sub.add_parser("rehearse")
    h.add_argument("--runs", type=int, default=10)
    h.add_argument("--beats", nargs="+", choices=BEATS, default=["b1", "b2", "b3", "b4"])
    for name in ("kill", "start"):
        sub.add_parser(name).add_argument("device", choices=sorted(DEV))
    w = sub.add_parser("wipe", help="delete runtime/ state (services must be stopped)")
    a = ap.parse_args()
    if a.cmd == "start-all":
        start_all(a)
    elif a.cmd == "stop-all":
        stop_all()
    elif a.cmd == "status":
        status()
    elif a.cmd == "reset":
        reset(a.beat)
    elif a.cmd == "play":
        reset(a.beat)
        sys.exit(0 if play(a.beat) else 1)
    elif a.cmd == "rehearse":
        rehearse(a.runs, a.beats)
    elif a.cmd == "kill":
        kill_device(a.device)
    elif a.cmd == "start":
        sys.exit(0 if start_device(a.device) else 1)
    elif a.cmd == "wipe":
        for p_ in (ROOT / "runtime").iterdir():
            if p_.name != ".gitkeep":
                shutil.rmtree(p_, ignore_errors=True) if p_.is_dir() else p_.unlink()
        print("runtime/ wiped")
    _ = w


if __name__ == "__main__":
    main()
