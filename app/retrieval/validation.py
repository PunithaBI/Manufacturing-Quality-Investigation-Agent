from __future__ import annotations

from .models import HybridEvidence


def validate_evidence(
    evidence: list[HybridEvidence],
) -> list[HybridEvidence]:

    validated: list[HybridEvidence] = []

    for item in evidence:

        if not item.evidence_id:
            continue

        if not item.source_type:
            continue

        if not item.source_id:
            continue

        if not item.provenance:
            continue

        table = item.provenance.get("table")

        record_id = item.provenance.get("record_id")

        if not table:
            continue

        if not isinstance(record_id, int):
            continue

        if record_id < 1:
            continue

        validated.append(item)

    return validated