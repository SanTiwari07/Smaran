"""Thin wrapper over qdrant-client for the fleet collection.

QDRANT_MODE=server   -> real Qdrant Server at QDRANT_URL (Docker; the PS3 setup)
QDRANT_MODE=embedded -> qdrant-client local mode on disk (same API, no Docker; dev/tests)
"""
from qdrant_client import QdrantClient, models as m

from ..common.config import settings
from ..common.schema import point_id

ALL = m.Filter()


def eq(key: str, value) -> m.FieldCondition:
    return m.FieldCondition(key=key, match=m.MatchValue(value=value))


class FleetServer:
    def __init__(self, mode: str = settings.qdrant_mode, url: str = settings.qdrant_url,
                 path: str | None = None, collection: str = settings.qdrant_collection, dim: int = settings.dense_dim):
        self.mode, self.collection, self.dim = mode, collection, dim
        if mode == "server":
            self.client = QdrantClient(url=url, timeout=10)
        elif path == ":memory:":
            self.client = QdrantClient(location=":memory:")
        else:
            p = path or str(settings.path(settings.runtime_dir) / "qdrant-embedded")
            self.client = QdrantClient(path=p)
        self.ensure()

    def describe(self) -> str:
        return f"{self.mode}:{settings.qdrant_url if self.mode == 'server' else 'local'}/{self.collection}"

    def ensure(self) -> None:
        if self.client.collection_exists(self.collection):
            return
        self.client.create_collection(
            self.collection,
            vectors_config={"dense": m.VectorParams(size=self.dim, distance=m.Distance.COSINE)},
            sparse_vectors_config={"bm25": m.SparseVectorParams(modifier=m.Modifier.IDF)},
        )
        if self.mode == "server":   # payload indexes (local mode ignores them)
            for f in ("entity_key", "status", "device_id", "residency"):
                self.client.create_payload_index(self.collection, f, m.PayloadSchemaType.KEYWORD)
            self.client.create_payload_index(self.collection, "server_seq", m.PayloadSchemaType.INTEGER)

    def reset(self) -> None:
        """Delete every point, keep the collection.

        Not delete_collection + create: in qdrant-client's on-disk local mode on Windows the
        recreated collection comes back with the old points.
        """
        self.ensure()
        self.client.delete(self.collection, points_selector=m.FilterSelector(filter=m.Filter()), wait=True)

    def upsert(self, op_id: str, vectors: dict, payload: dict) -> None:
        sp = vectors["bm25"]
        self.client.upsert(self.collection, [m.PointStruct(
            id=point_id(op_id), payload=payload,
            vector={"dense": vectors["dense"], "bm25": m.SparseVector(indices=sp["indices"], values=sp["values"])})])

    def set_payload(self, op_id: str, payload: dict) -> None:
        self.client.set_payload(self.collection, payload=payload, points=[point_id(op_id)])

    def scroll(self, flt: m.Filter | None = None, with_vectors: bool = False) -> list:
        out, offset = [], None
        while True:
            recs, offset = self.client.scroll(self.collection, scroll_filter=flt, limit=256, offset=offset,
                                              with_payload=True, with_vectors=with_vectors)
            out.extend(recs)
            if offset is None:
                return out

    def versions(self, entity_key: str) -> list[dict]:
        return [r.payload for r in self.scroll(m.Filter(must=[eq("entity_key", entity_key)]))]

    def changes(self, since: int, limit: int) -> list:
        recs = self.scroll(m.Filter(must=[m.FieldCondition(key="server_seq", range=m.Range(gt=since))]),
                           with_vectors=True)
        recs.sort(key=lambda r: r.payload["server_seq"])
        return recs[:limit]

    def hybrid(self, dense: list[float], sparse: dict, limit: int) -> list:
        flt = m.Filter(must_not=[eq("status", "superseded")])
        sv = m.SparseVector(indices=sparse["indices"], values=sparse["values"])
        return self.client.query_points(
            self.collection,
            prefetch=[m.Prefetch(query=dense, using="dense", limit=limit * 2, filter=flt),
                      m.Prefetch(query=sv, using="bm25", limit=limit * 2, filter=flt)],
            query=m.FusionQuery(fusion=m.Fusion.RRF), limit=limit, with_payload=True, with_vectors=["dense"],
        ).points

    def count(self, flt: m.Filter | None = None) -> int:
        return self.client.count(self.collection, count_filter=flt, exact=True).count


def vectors_json(vector: dict) -> dict:
    sp = vector["bm25"]
    return {"dense": list(vector["dense"]), "bm25": {"indices": list(sp.indices), "values": list(sp.values)}}
