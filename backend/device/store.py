"""The device's three Qdrant Edge shards.

- Krypta (private): personal/sensitive memories. No code path syncs it.
- Hermes (mutable): local writes waiting to sync (every write here is also in the outbox).
- Agora  (mirror):  fleet knowledge pulled from the server.

Point ids are uuid5(op_id), so every write is idempotent.

BM25 with a device-wide IDF: shards store plain BM25 term weights (no per-shard IDF modifier)
and the Store keeps one document-frequency table across all three shards. Queries are
weighted with that global IDF, so a BM25 score means the same in every shard. With a
per-shard IDF, a fresh note in a nearly empty Hermes shard scored low on every keyword.
"""
import math
import shutil
import threading
from collections import Counter
from pathlib import Path

from qdrant_edge import (CountRequest, Distance, EdgeConfig, EdgeShard, EdgeSparseVectorParams,
                         EdgeVectorParams, FieldCondition, Filter, Fusion, MatchValue, PayloadSchemaType,
                         Point, Prefetch, Query, QueryRequest, ScrollRequest, SparseVector, UpdateOperation)

from ..common.schema import SHARDS, point_id

KEYWORD_FIELDS = ("status", "entity_key", "machine", "kind", "op_id")

NOT_SUPERSEDED = Filter(must_not=[FieldCondition(key="status", match=MatchValue(value="superseded"))])


def match(key: str, value) -> Filter:
    return Filter(must=[FieldCondition(key=key, match=MatchValue(value=value))])


class Store:
    def __init__(self, root: Path, dim: int):
        self.root = Path(root)
        self.dim = dim
        self.lock = threading.RLock()
        self.shards: dict[str, EdgeShard] = {}
        self.dirty = False
        self.df: Counter = Counter()      # term -> number of docs containing it (all shards)
        self.n_docs = 0
        self.open()

    # ---- lifecycle -------------------------------------------------------------------
    def _config(self) -> EdgeConfig:
        return EdgeConfig(
            vectors={"dense": EdgeVectorParams(size=self.dim, distance=Distance.Cosine)},
            sparse_vectors={"bm25": EdgeSparseVectorParams()},   # IDF applied at query time
        )

    def _open_shard(self, path: Path) -> EdgeShard:
        path.mkdir(parents=True, exist_ok=True)
        if any(path.iterdir()):
            return EdgeShard.load(str(path))  # create() refuses a non-empty directory
        shard = EdgeShard.create(str(path), self._config())
        for f in KEYWORD_FIELDS:
            shard.update(UpdateOperation.create_field_index(f, PayloadSchemaType.Keyword))
        shard.update(UpdateOperation.create_field_index("server_seq", PayloadSchemaType.Integer))
        return shard

    def open(self) -> None:
        with self.lock:
            for name in SHARDS:
                self.shards[name] = self._open_shard(self.root / name)
            self._rebuild_df()

    # ---- device-wide IDF -------------------------------------------------------------
    def _rebuild_df(self) -> None:
        self.df, self.n_docs = Counter(), 0
        for name in self.shards:
            for r in self.scroll(name, vectors=["bm25"]):
                self._count(r.vector.get("bm25"), +1)

    def _count(self, sv, sign: int) -> None:
        if sv is None:
            return
        self.n_docs += sign
        for i in sv.indices:
            self.df[i] += sign
            if self.df[i] <= 0:
                del self.df[i]

    def _existing_bm25(self, shard: str, op_id: str):
        recs = self.shards[shard].retrieve(point_ids=[point_id(op_id)], with_payload=False, with_vector=["bm25"])
        return recs[0].vector.get("bm25") if recs else None

    def idf_query(self, sq: SparseVector) -> SparseVector:
        """Weight a BM25 query by device-wide IDF (same formula as Qdrant's IDF modifier)."""
        n = max(self.n_docs, 1)
        w = [math.log(1 + (n - self.df.get(i, 0) + 0.5) / (self.df.get(i, 0) + 0.5)) for i in sq.indices]
        return SparseVector(indices=list(sq.indices), values=w)

    def close(self) -> None:
        with self.lock:
            for s in self.shards.values():
                s.close()
            self.shards = {}

    def wipe(self) -> None:
        """Delete and recreate the shard directories (slow on Windows once shards were used)."""
        with self.lock:
            self.close()
            for name in SHARDS:
                shutil.rmtree(self.root / name, ignore_errors=True)
            self.open()

    def clear(self) -> None:
        """Delete every point but keep the shards open. Used by demo resets: fast, no file I/O."""
        with self.lock:
            self.df, self.n_docs = Counter(), 0
            for name, shard in self.shards.items():
                ids = [r.id for r in self.scroll(name)]
                for i in range(0, len(ids), 500):
                    shard.update(UpdateOperation.delete_points(ids[i:i + 500]))
                shard.optimize()
            self.dirty = False

    def optimize(self) -> None:
        with self.lock:
            for s in self.shards.values():
                s.optimize()
            self.dirty = False

    # ---- writes ----------------------------------------------------------------------
    def upsert(self, shard: str, op_id: str, dense: list[float], sparse: SparseVector, payload: dict) -> None:
        with self.lock:
            self._count(self._existing_bm25(shard, op_id), -1)
            self.shards[shard].update(UpdateOperation.upsert_points(
                [Point(id=point_id(op_id), vector={"dense": dense, "bm25": sparse}, payload=payload)]))
            self._count(sparse, +1)
            self.dirty = True

    def set_payload(self, shard: str, op_id: str, payload: dict) -> None:
        with self.lock:
            self.shards[shard].update(UpdateOperation.set_payload(point_ids=[point_id(op_id)], payload=payload))

    def delete(self, shard: str, op_id: str) -> None:
        with self.lock:
            self._count(self._existing_bm25(shard, op_id), -1)
            self.shards[shard].update(UpdateOperation.delete_points([point_id(op_id)]))
            self.dirty = True

    # ---- reads -----------------------------------------------------------------------
    def get(self, shard: str, op_id: str, with_vector: bool = False):
        with self.lock:
            recs = self.shards[shard].retrieve(point_ids=[point_id(op_id)], with_payload=True,
                                               with_vector=["dense", "bm25"] if with_vector else False)
        return recs[0] if recs else None

    def scroll(self, shard: str, flt: Filter | None = None, vectors: list[str] | None = None) -> list:
        out, offset = [], None
        with self.lock:
            while True:
                recs, offset = self.shards[shard].scroll(ScrollRequest(
                    limit=256, offset=offset, filter=flt, with_payload=True, with_vector=vectors or False))
                out.extend(recs)
                if offset is None:
                    return out

    def by_entity(self, entity_key: str, shards=("hermes", "agora")) -> list[tuple[str, dict]]:
        """All versions of one entity on this device, as (shard, payload). Agora wins on duplicates."""
        seen: dict[str, tuple[str, dict]] = {}
        for name in shards:
            for r in self.scroll(name, match("entity_key", entity_key)):
                if r.payload["op_id"] not in seen or name == "agora":
                    seen[r.payload["op_id"]] = (name, r.payload)
        return list(seen.values())

    def count(self, shard: str, flt: Filter | None = None) -> int:
        with self.lock:
            return self.shards[shard].count(CountRequest(filter=flt, exact=True))

    def hybrid(self, shard: str, dense: list[float], sparse: SparseVector, k: int = 20,
               flt: Filter | None = NOT_SUPERSEDED) -> list:
        """Dense + BM25 fused with RRF natively inside ONE Edge shard (not used across shards).

        `sparse` should come from idf_query().
        """
        def pf(q):
            return Prefetch(query=q, limit=k, filter=flt, prefetches=[], params=None, score_threshold=None)
        with self.lock:
            return self.shards[shard].query(QueryRequest(
                prefetches=[pf(Query.Nearest(dense, using="dense")), pf(Query.Nearest(sparse, using="bm25"))],
                query=Fusion.Rrf(k=60), limit=k, offset=0, filter=None, score_threshold=None,
                params=None, with_payload=True, with_vector=["dense"]))

    def vector_search(self, shard: str, vector, using: str, k: int = 20, flt: Filter | None = NOT_SUPERSEDED) -> list:
        """One ranked list (dense or bm25) from one shard, with the dense vector for cosine display.

        For bm25, pass the output of idf_query() so scores are comparable across shards.
        """
        with self.lock:
            return self.shards[shard].query(QueryRequest(
                query=Query.Nearest(vector, using=using), limit=k, filter=flt,
                with_payload=True, with_vector=["dense"]))

    def nearest(self, shard: str, dense: list[float], k: int = 1, flt: Filter | None = NOT_SUPERSEDED,
                score_threshold: float | None = None) -> list:
        with self.lock:
            return self.shards[shard].query(QueryRequest(
                query=Query.Nearest(dense, using="dense"), limit=k, filter=flt,
                score_threshold=score_threshold, with_payload=True, with_vector=False))
