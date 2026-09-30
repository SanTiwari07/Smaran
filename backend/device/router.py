"""Argus: decides where each new memory lives. Order matters; earlier layers win.

1. PII rules (or kind=personal)  -> private, confidence 1.0. No model can override this.
2. Classifier proposal           -> private | sync | drop, plus criticality
   - criticality: safety-critical if the model OR safety keywords say so (see classifier.py)
   - status updates are never dropped (they're how machines change state)
   - an unsure "sync" (< 0.5) stays private: when in doubt, don't let it leave
3. Dedup against Agora           -> drop if it nearly repeats fleet knowledge (cosine >= 0.95)
"""
from dataclasses import asdict, dataclass

from ..common.config import settings
from ..common.pii import find_pii
from ..common.schema import AGORA, NoteIn
from .classifier import ResidencyClassifier, combine_criticality, safety_floor


@dataclass
class Decision:
    residency: str
    criticality: int
    confidence: float
    by: str
    reason: str

    def as_dict(self) -> dict:
        return asdict(self)


class Router:
    def __init__(self, classifier: ResidencyClassifier, store, dedup_at: float = settings.dedup_at):
        self.clf, self.store, self.dedup_at = classifier, store, dedup_at

    def decide(self, note: NoteIn, dense: list[float]) -> Decision:
        crit_floor = safety_floor(note.text)
        hits = find_pii(note.text)
        if hits or note.kind == "personal":
            why = f"PII rule matched: {', '.join(hits)}" if hits else "note marked personal"
            return Decision("private", crit_floor, 1.0, "pii_rule", why)

        p = self.clf.predict(note.text, dense)
        crit = combine_criticality(p.criticality, note.text)
        residency, by = p.residency, "classifier"
        reason = f"{self.clf.name} proposed {p.residency} ({p.confidence:.2f})"
        if crit_floor:
            reason += "; safety keyword -> safety-critical"
        if note.kind == "status" and residency == "drop":
            residency, by, reason = "sync", "rule", reason + "; status updates are never dropped"
        if residency == "sync" and p.confidence < 0.5 and note.kind not in ("status", "fix", "task", "decision", "fact", "preference"):
            residency, by, reason = "private", "rule", reason + "; unsure, kept local by default"

        if residency == "sync" and note.kind != "status":
            dup = self.store.nearest(AGORA, dense, k=1, score_threshold=self.dedup_at)
            if dup:
                return Decision("drop", crit, float(dup[0].score), "dedup",
                                f"near-duplicate of fleet memory {dup[0].payload.get('op_id')} "
                                f"(cosine {dup[0].score:.2f})")
        return Decision(residency, crit, round(p.confidence, 3), by, reason)
