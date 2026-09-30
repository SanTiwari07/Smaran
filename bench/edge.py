"""Edge benchmark for the personal companion: what does it cost to run on ONE laptop, offline?

    python -m bench.edge [--sizes 100 1000 3000] [--skip-slm]

Everything is measured on this machine with the real embedder (bge-small ONNX) and, if the
local model runtime is running, the real local SLM. No network is used except the loopback call
to the local model server. Results: bench/results/edge.json and docs/EDGE_BENCHMARKS.md.

Sync here is device -> gateway through the gateway's real HTTP routes, in-process (no sockets),
so it measures our code, not a LAN.
"""
import argparse
import ctypes
import json
import os
import platform
import shutil
import statistics
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from backend.common.config import settings  # noqa: E402
from backend.common.log import Log  # noqa: E402
from backend.common.schema import NoteIn  # noqa: E402
from backend.companion.benchmark import dir_size_mb  # noqa: E402
from backend.companion.llm import ModelRouter  # noqa: E402
from backend.companion.service import Companion  # noqa: E402
from backend.companion.story import load_story  # noqa: E402
from backend.device.classifier import PersonalClassifier  # noqa: E402
from backend.device.core import Device  # noqa: E402
from backend.device.embed import get_embedder  # noqa: E402
from backend.device.hermes import Hermes  # noqa: E402
from backend.gateway.app import create_app  # noqa: E402
from backend.gateway.core import Gateway  # noqa: E402
from backend.gateway.server import FleetServer  # noqa: E402

TOPICS = ["binary trees", "TCP congestion", "normalization", "process scheduling", "gradient descent", "REST design",
          "hash tables", "SQL joins", "cache coherence", "graph search", "regularization", "virtual memory"]
QUERIES = ["which database did we decide on", "what tasks are left for the project", "when is the review meeting",
           "who handles the frontend", "when should I study", "what was covered in the last lecture",
           "what did the mentor say about deadlines", "did we need a vector extension"]


def rss_mb() -> float:
    if platform.system() == "Windows":
        class PMC(ctypes.Structure):
            _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong), ("PeakWorkingSetSize", ctypes.c_size_t),
                        ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t),
                        ("PeakPagefileUsage", ctypes.c_size_t)]
        c = PMC()
        c.cb = ctypes.sizeof(PMC)
        k32, ps = ctypes.WinDLL("kernel32"), ctypes.WinDLL("psapi")
        k32.GetCurrentProcess.restype = ctypes.c_void_p
        ps.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(PMC), ctypes.c_ulong]
        ps.GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(c), c.cb)
        return round(c.WorkingSetSize / 1e6, 0)
    import resource
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 0)


def pct(xs, p):
    xs = sorted(xs)
    return round(xs[min(len(xs) - 1, int(p / 100 * len(xs)))], 2)


def ms(fn, n):
    out = []
    for i in range(n):
        t0 = time.perf_counter()
        fn(i)
        out.append((time.perf_counter() - t0) * 1000)
    return {"p50": pct(out, 50), "p95": pct(out, 95), "n": n}


def startup(dev, emb, tmp, tag):
    """Close the device and reopen it from disk with the link off; time it to the first answer."""
    root = dev.root
    dev.close()
    t0 = time.perf_counter()
    d2 = Device("A", root, emb, PersonalClassifier(), http=None, log=Log("re" + tag, tmp / "logs"))
    d2.set_online(False)
    c2 = Companion(d2, None, ModelRouter(online=lambda: False, use_local=False))
    t_open = (time.perf_counter() - t0) * 1000
    c2.chat("Which DB are we going with for the capstone?")
    out = {"open_ms": round(t_open), "to_first_answer_ms": round((time.perf_counter() - t0) * 1000),
           "memories": sum(d2.state()["counts"].values()), "network": "none (http client is None)"}
    d2.close()
    return out


def fill(c, n_total):
    have = sum(c.dev.state()["counts"].values())
    for i in range(have, n_total):
        c.dev.add_note(NoteIn(text=f"Lecture note {i}: {TOPICS[i % len(TOPICS)]} and example {i} from week {i % 14}, "
                                   f"discussed with group {i % 9}", kind="event", subject=f"course-{i % 6}"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", type=int, nargs="+", default=[100, 1000, 3000])
    ap.add_argument("--skip-slm", action="store_true")
    args = ap.parse_args()
    tmp = Path(tempfile.mkdtemp(prefix="smaran-edge-"))
    r: dict = {"machine": {"os": platform.platform(), "python": platform.python_version(), "cpu_threads": os.cpu_count()},
               "measured_at": time.strftime("%Y-%m-%d %H:%M"), "embedder": "bge-small-en-v1.5 (ONNX, CPU)"}
    try:
        rss0 = rss_mb()
        t0 = time.perf_counter()
        emb = get_embedder("fastembed")
        emb.dense(["warm up"])
        r["embedder_load_ms"] = round((time.perf_counter() - t0) * 1000)
        r["rss_after_embedder_mb"] = rss_mb()
        r["embed_query_ms"] = ms(lambda i: emb.embed_query(QUERIES[i % len(QUERIES)]), 100)
        r["embed_doc_ms"] = ms(lambda i: emb.embed_doc(f"Lecture note {i}: {TOPICS[i % len(TOPICS)]} example"), 100)

        gw = Gateway(FleetServer(mode="embedded", path=":memory:"), tmp / "gw.db", lambda: emb, log=Log("gw", tmp / "logs"))
        gw.seed(settings.path("seed/campus"))
        client = TestClient(create_app(gw))
        root = tmp / "phone"
        dev = Device("A", root, emb, PersonalClassifier(), http=client, log=Log("phone", tmp / "logs"))
        local = ModelRouter(online=lambda: dev.online)
        slm_up = (not args.skip_slm) and local.local.available()
        comp = Companion(dev, Hermes(dev), local)
        comp.router.use_local = False           # retrieval and agent numbers must not include model time
        load_story(comp)

        r["retrieval_by_size"] = {}
        for n in args.sizes:
            fill(comp, n)
            total = sum(dev.state()["counts"].values())
            dev.store.optimize()
            res = ms(lambda i: comp.recall(QUERIES[i % len(QUERIES)], 5, allow_cloud=False), 60)
            r["retrieval_by_size"][str(total)] = {**res, "disk_mb": dir_size_mb(root)}
            print(f"  retrieval @ {total} memories: p50 {res['p50']} ms, p95 {res['p95']} ms")
            if n == args.sizes[0]:
                r["offline_startup_small"] = startup(dev, emb, tmp, "s")
                dev = Device("A", root, emb, PersonalClassifier(), http=client, log=Log("phone-b", tmp / "logs"))
                comp = Companion(dev, Hermes(dev), local)
                comp.router.use_local = False

        r["agent_ms"] = {
            "create_task_with_verify": ms(lambda i: comp.run_action("create_task", {"title": f"benchmark task {i}"}, f"b{i}", "b"), 30),
            "list_tasks": ms(lambda i: comp.run_action("list_tasks", {}, f"l{i}", "b"), 30),
            "chat_remember_end_to_end": ms(lambda i: comp.chat(f"We decided to use tool number {i} for the benchmark project."), 20),
            "chat_ask_rules_end_to_end": ms(lambda i: comp.chat(QUERIES[i % len(QUERIES)]), 20),
        }

        dev.set_online(False)
        for i in range(100):
            comp.chat(f"I need to finish benchmark item {i}")
        queued = dev.db.depth()
        dev.set_online(True)
        t0 = time.perf_counter()
        push = comp.hermes.push()
        r["sync"] = {"queued_ops": queued, "push_ms": round((time.perf_counter() - t0) * 1000), "sent": push.get("sent"),
                     "note": "in-process HTTP routes to an embedded gateway; excludes real network latency"}
        t0 = time.perf_counter()
        pull = comp.hermes.pull()
        r["sync"].update(pull_ms=round((time.perf_counter() - t0) * 1000), pulled=pull.get("pulled"))
        dev.db.conn.execute("UPDATE outbox SET state='pending'")
        t0 = time.perf_counter()
        replay = comp.hermes.push()
        r["sync"].update(replay_ms=round((time.perf_counter() - t0) * 1000), replay_results=replay.get("results"))

        r["disk_mb_final"] = dir_size_mb(root)
        r["memories_final"] = sum(dev.state()["counts"].values())

        r["offline_startup"] = startup(dev, emb, tmp, "l")

        if slm_up:
            dev3 = Device("A", root, emb, PersonalClassifier(), http=None, log=Log("phone3", tmp / "logs"))
            dev3.set_online(False)
            router = ModelRouter(online=lambda: False)
            comp3 = Companion(dev3, None, router)
            t0 = time.perf_counter()
            cold = router.local.warm()
            answers = []
            for i, q in enumerate(QUERIES[:6]):
                t0 = time.perf_counter()
                out = comp3.chat(q)
                answers.append({"q": q, "route": out["route"]["route"], "ms": round((time.perf_counter() - t0) * 1000)})
            slm = [a["ms"] for a in answers if a["route"] == "local-slm"]
            r["local_slm"] = {"model": router.local.model, "runtime": "Ollama (llama.cpp)", "load_ms": cold,
                              "answered_by_slm": f"{len(slm)}/{len(answers)}",
                              "e2e_question_ms": {"p50": pct(slm, 50), "p95": pct(slm, 95), "n": len(slm)} if slm else None,
                              "fell_back_to_rules": [a["q"] for a in answers if a["route"] != "local-slm"]}
            dev3.close()
        else:
            r["local_slm"] = "not measured (local model runtime not running or --skip-slm)"
        r["rss_end_mb"] = rss_mb()
        r["rss_start_mb"] = rss0

        out = ROOT / "bench" / "results"
        out.mkdir(exist_ok=True)
        (out / "edge.json").write_text(json.dumps(r, indent=1), encoding="utf8")
        write_md(r)
        print(json.dumps(r, indent=1))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def write_md(r: dict) -> None:
    L = ["# Edge benchmark (personal companion)", "",
         f"Measured {r['measured_at']} on: {r['machine']['os']}, Python {r['machine']['python']}, {r['machine']['cpu_threads']} CPU threads. "
         "Command: `python -m bench.edge`. Every number below was measured by that command; nothing is estimated.", "",
         "| Measure | Result |", "|---|---|",
         f"| Embedder load (bge-small ONNX, CPU) | {r['embedder_load_ms']} ms |",
         f"| Query embedding p50 / p95 | {r['embed_query_ms']['p50']} / {r['embed_query_ms']['p95']} ms ({r['embed_query_ms']['n']} runs) |",
         f"| Document embedding p50 / p95 | {r['embed_doc_ms']['p50']} / {r['embed_doc_ms']['p95']} ms |"]
    for n, v in r["retrieval_by_size"].items():
        L.append(f"| Retrieval (embed + hybrid search + rerank) @ {n} memories, p50 / p95 | {v['p50']} / {v['p95']} ms ({v['n']} queries, {v['disk_mb']} MB on disk) |")
    for k, v in r["agent_ms"].items():
        L.append(f"| Agent: {k.replace('_', ' ')} p50 / p95 | {v['p50']} / {v['p95']} ms ({v['n']} runs) |")
    s = r["sync"]
    L += [f"| Sync push of {s['queued_ops']} queued ops | {s['push_ms']} ms (sent {s['sent']}) |",
          f"| Sync pull after push | {s['pull_ms']} ms ({s['pulled']} points) |",
          f"| Replay of the same {s['queued_ops']} ops (idempotency) | {s['replay_ms']} ms, results {s['replay_results']} |",
          f"| Offline restart (link off): open device + companion / to first answered question | {r['offline_startup_small']['open_ms']} / {r['offline_startup_small']['to_first_answer_ms']} ms with {r['offline_startup_small']['memories']} memories |",
          f"| Offline restart, larger memory | {r['offline_startup']['open_ms']} / {r['offline_startup']['to_first_answer_ms']} ms with {r['offline_startup']['memories']} memories |",
          f"| Process memory (working set) | {r['rss_start_mb']:.0f} MB at start, {r['rss_after_embedder_mb']:.0f} MB with the embedder, {r['rss_end_mb']:.0f} MB at the end |",
          f"| On-disk size at {r['memories_final']} memories | {r['disk_mb_final']} MB |"]
    if isinstance(r["local_slm"], dict):
        m = r["local_slm"]
        e = m["e2e_question_ms"]
        L.append(f"| Local SLM `{m['model']}` ({m['runtime']}): load / first token | {m['load_ms']} ms |")
        if e:
            L.append(f"| Question answered on device (retrieve + generate) p50 / p95 | {e['p50']} / {e['p95']} ms ({e['n']} questions; SLM answered {m['answered_by_slm']}) |")
        if m["fell_back_to_rules"]:
            L.append(f"| Questions where the SLM answer was rejected or failed and rules answered | {len(m['fell_back_to_rules'])} |")
    L += ["", "Notes:", "- Retrieval and agent rows run with the SLM disabled so they show the cost of memory and tools alone.",
          "- Sync rows use the gateway's real HTTP routes in-process, not a network; add your LAN or mobile latency on top.",
          "- Memory notes are synthetic lecture sentences (`Lecture note N: ...`) plus the 15-utterance story."]
    (ROOT / "docs" / "EDGE_BENCHMARKS.md").write_text("\n".join(L) + "\n", encoding="utf8")


if __name__ == "__main__":
    main()
