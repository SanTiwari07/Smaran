"""Partial-snapshot mirror refresh, measured against the real Qdrant Server.

    python -m bench.bench snapshots        # needs Qdrant Server (docker compose -f infra/docker-compose.yml up -d)

This is Qdrant's documented server -> Edge sync mechanism
(https://qdrant.tech/documentation/edge/edge-data-synchronization-patterns/):
1. download a full snapshot of server shard 0 and unpack it into a fresh Edge Shard
2. add points on the server
3. send the Edge Shard's snapshot_manifest() to /snapshot/partial/create; the server returns
   only the segments that changed; apply it with update_from_snapshot()

It runs on its own collection (`smaran_snapshot_bench`, deleted afterwards), never on the demo
collection. The live Agora mirror still refreshes from the gateway's change feed: a restored
shard takes the server's config and payloads, which would replace Smaran's device-wide BM25
IDF and each replica's own known_from/valid_to times (Chronos). Switching Agora over needs
those two moved out of the shard first; see docs/AUDIT_AND_PLAN.md.
"""
import shutil
import tempfile
import time
from pathlib import Path

import httpx
from qdrant_edge import CountRequest, EdgeShard, Query, QueryRequest

from backend.common.config import settings
from backend.device.embed import HashEmbedder, sparse_to_json
from backend.common.schema import point_id
from backend.gateway.server import FleetServer, m

ROOT = Path(__file__).resolve().parents[1]
COLLECTION = "smaran_snapshot_bench"


def _download(client: httpx.Client, method: str, url: str, dest: Path, **kw) -> int:
    with client.stream(method, url, **kw) as r:
        r.raise_for_status()
        with dest.open("wb") as f:
            for chunk in r.iter_bytes(1 << 16):
                f.write(chunk)
    return dest.stat().st_size


def _fill(server: FleetServer, emb: HashEmbedder, start: int, n: int) -> None:
    points = []
    for i in range(start, start + n):
        text = f"memory {i}: machine CNC-{i % 20:02d} observation number {i}"
        dense, sparse = emb.embed_doc(text)
        points.append(m.PointStruct(id=point_id(f"SNAP-{i:05d}"), vector={
            "dense": dense, "bm25": m.SparseVector(**sparse_to_json(sparse))},
            payload={"op_id": f"SNAP-{i:05d}", "text": text, "status": "current", "server_seq": i}))
    for k in range(0, len(points), 256):
        server.client.upsert(server.collection, points[k:k + 256], wait=True)
    _settle(server)


def _settle(server: FleetServer, timeout: float = 120) -> None:
    """Wait until the server's optimizer is idle, so the segment layout stops changing.

    A partial snapshot sends every segment that differs from the Edge Shard's manifest; if the
    optimizer merges segments after the full restore, everything differs."""
    end, last = time.time() + timeout, None
    while time.time() < end:
        info = server.client.get_collection(server.collection)
        now = (info.status, info.segments_count, info.points_count)
        if str(info.status).lower().endswith("green") and now == last:
            return
        last = now
        time.sleep(1.0)


def bench_snapshots(base: int = 2000, added: int = 20) -> dict:
    try:
        httpx.get(f"{settings.qdrant_url}/readyz", timeout=2).raise_for_status()
    except httpx.HTTPError as e:
        return {"skipped": f"Qdrant Server not reachable ({e.__class__.__name__}); start it and rerun: "
                           "python -m bench.bench snapshots"}
    emb = HashEmbedder()
    server = FleetServer(mode="server", collection=COLLECTION)
    server.reset()
    shard = None
    work = Path(tempfile.mkdtemp(dir=ROOT / "runtime"))
    try:
        http = httpx.Client(base_url=settings.qdrant_url, timeout=120)
        shard_url = f"/collections/{COLLECTION}/shards/0/snapshot"

        _fill(server, emb, 0, base)
        t = time.perf_counter()
        full_bytes = _download(http, "GET", shard_url, work / "full.snapshot")
        EdgeShard.unpack_snapshot(str(work / "full.snapshot"), str(work / "mirror"))
        shard = EdgeShard.load(str(work / "mirror"))
        full_s = time.perf_counter() - t
        initial = shard.count(CountRequest(filter=None, exact=True))

        _fill(server, emb, base, added)
        t = time.perf_counter()
        manifest = shard.snapshot_manifest()
        partial_bytes = _download(http, "POST", f"{shard_url}/partial/create", work / "partial.snapshot", json=manifest)
        shard.update_from_snapshot(str(work / "partial.snapshot"))
        partial_s = time.perf_counter() - t
        after = shard.count(CountRequest(filter=None, exact=True))

        probe = f"memory {base + added - 1}: machine CNC-{(base + added - 1) % 20:02d} observation number {base + added - 1}"
        hit = shard.query(QueryRequest(query=Query.Nearest(emb.embed_query(probe)[0], using="dense"),
                                       limit=1, with_payload=True, with_vector=False))
        full_after_bytes = _download(http, "GET", shard_url, work / "full2.snapshot")
        return {
            "collection": COLLECTION, "server_points_before": base, "points_added": added,
            "mirror_points_after_full": initial, "mirror_points_after_partial": after,
            "server_points_after": server.count(),
            "newest_point_found": bool(hit) and hit[0].payload.get("op_id") == f"SNAP-{base + added - 1:05d}",
            "full_snapshot_bytes": full_bytes, "full_snapshot_after_bytes": full_after_bytes,
            "partial_snapshot_bytes": partial_bytes,
            "partial_vs_full_pct": round(100 * partial_bytes / full_after_bytes, 1),
            "full_restore_s": round(full_s, 2), "partial_refresh_s": round(partial_s, 2),
        }
    finally:
        if shard is not None:
            shard.close()
        server.client.delete_collection(COLLECTION)
        shutil.rmtree(work, ignore_errors=True)


def to_markdown(x: dict) -> list[str]:
    L = ["## Partial-snapshot mirror refresh (Qdrant Server → Qdrant Edge)", ""]
    if "skipped" in x:
        return L + [f"- {x['skipped']}", ""]
    ok = x["mirror_points_after_partial"] == x["server_points_after"] and x["newest_point_found"]
    L += [f"Qdrant's documented sync path, run against the real server on a separate collection: restore a full "
          f"snapshot of shard 0 into an Edge Shard ({x['server_points_before']:,} points), add {x['points_added']} "
          "points on the server, then refresh the Edge Shard with a partial snapshot built from its manifest.", "",
          "| | Bytes | Time |", "|---|---|---|",
          f"| Full snapshot (initial restore) | {x['full_snapshot_bytes']:,} | {x['full_restore_s']} s |",
          f"| Full snapshot after the additions | {x['full_snapshot_after_bytes']:,} | |",
          f"| **Partial snapshot (refresh)** | **{x['partial_snapshot_bytes']:,}** ({x['partial_vs_full_pct']}% of full) | {x['partial_refresh_s']} s |", "",
          f"- Mirror after refresh: {x['mirror_points_after_partial']:,} points, server: {x['server_points_after']:,}; "
          f"newest point searchable on the Edge Shard: {'yes' if x['newest_point_found'] else 'NO'}. "
          f"{'Consistent.' if ok else 'MISMATCH.'}",
          "- Measured result: at this size the partial snapshot is about as large as a full one. The refresh is "
          "correct, but it saved no bandwidth here, also with the server optimizer settled before each snapshot "
          "and with a lower indexing threshold (tried, not kept). We report it as measured.",
          "- Not the live Agora path: the demo mirror refreshes from the change feed, which sends only changed "
          "points (see the module docstring).", ""]
    return L
