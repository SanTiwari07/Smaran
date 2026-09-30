"""Shared data shapes (docs/IMPLEMENTATION_PLAN.md section 3).

Memory payloads travel as plain dicts (Qdrant payloads); these models validate API input
and document the payload fields in one place.
"""
import uuid
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

# "status/observation/fix/manual" are the fleet-maintenance kinds (still supported and tested);
# "personal" forces Krypta. The rest are the personal-companion kinds (backend/companion/).
Kind = Literal["status", "observation", "fix", "personal", "manual",
               "decision", "task", "fact", "preference", "event", "note"]
MemoryType = Literal["episodic", "semantic", "procedural"]
Residency = Literal["private", "sync", "drop"]
Status = Literal["current", "superseded", "contested"]

# Shard names on the device. Krypta never syncs; Hermes holds unsynced local writes;
# Agora mirrors fleet knowledge from the server.
KRYPTA, HERMES, AGORA = "krypta", "hermes", "agora"
SHARDS = (KRYPTA, HERMES, AGORA)

# Payload fields (see plan 3.1):
#   op_id, entity_key, machine, kind, text, device_id, author, vv, seq,
#   valid_from (author's wall clock), known_from (when *this* replica learned it),
#   valid_to (when this replica learned it was superseded), superseded_by, status,
#   residency, criticality (0 routine, 1 important, 2 safety-critical), decision, server_seq

_NS = uuid.UUID("5a4d7a2e-0c1b-4f3e-9a51-736d6172616e")  # fixed namespace for Smaran


def point_id(op_id: str) -> str:
    """Deterministic point id, so retries and replays are idempotent everywhere."""
    return str(uuid.uuid5(_NS, op_id))


# Kinds that can name ONE changing fact (a task's state, a meeting time, "the database we use").
SLOT_KINDS = ("task", "fact", "decision", "preference")


def entity_key_for(machine: Optional[str], kind: str, slot: Optional[str] = None) -> Optional[str]:
    """Only notes that describe a single changing fact get an entity key (and so versions and
    conflicts); everything else is append-only.

    - fleet: a machine's status  -> "machine:CNC-07/status"
    - companion: a slot in a subject (project, course...) -> "capstone/decision:database"
    """
    if slot and kind in SLOT_KINDS:
        return f"{machine or 'general'}/{slot}"
    if machine and kind == "status":
        return f"machine:{machine}/status"
    return None


class NoteIn(BaseModel):
    """`machine` is the memory's scope: a machine in the fleet domain, a project/course in the
    personal domain (`subject` is the friendlier alias for the same field)."""
    text: str = Field(min_length=1, max_length=2000)
    kind: Kind = "observation"
    machine: Optional[str] = None
    subject: Optional[str] = None
    author: str = ""
    # ---- companion memory fields (all optional; the fleet domain never sets them) ----
    memory_type: Optional[MemoryType] = None
    slot: Optional[str] = None            # names the single changing fact -> entity key
    importance: Optional[float] = Field(default=None, ge=0, le=1)
    confidence: Optional[float] = Field(default=None, ge=0, le=1)
    entities: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    source: Optional[str] = None          # conversation | agent | import | seed
    fields: dict = Field(default_factory=dict)   # kind-specific: task status, due date...
    ts: Optional[float] = None            # backdate (seed data and tests only)

    @model_validator(mode="after")
    def _scope(self):
        if self.subject and not self.machine:
            self.machine = self.subject
        return self


class OnlineIn(BaseModel):
    online: bool


class SparseJson(BaseModel):
    indices: list[int]
    values: list[float]


class VectorsJson(BaseModel):
    """Either `dense` (JSON floats) or `dense_f16` (base64 float16), see common/vectors.py."""
    dense: Optional[list[float]] = None
    dense_f16: Optional[str] = None
    bm25: SparseJson

    @model_validator(mode="after")
    def _one_dense(self):
        if (self.dense is None) == (self.dense_f16 is None):
            raise ValueError("give exactly one of dense or dense_f16")
        return self


class SyncOp(BaseModel):
    op_id: str
    vectors: VectorsJson
    payload: dict


class SyncBatch(BaseModel):
    device_id: str
    ops: list[SyncOp]


class SearchIn(BaseModel):
    dense: list[float]
    bm25: SparseJson
    limit: int = 10


class ResolveIn(BaseModel):
    entity_key: str
    op_id: Optional[str] = None     # keep this version's text
    text: Optional[str] = None      # or write a new text
    author: str = "supervisor"
