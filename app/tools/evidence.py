from __future__ import annotations

import hashlib

from .common import Evidence, Provenance
from .errors import ToolErrorCode


def create_evidence_id(
    source_type: str,
    source_id: str,
) -> str:
    """
    Create a deterministic evidence identifier.

    The same source record will always produce the same
    evidence ID, which makes evidence references stable
    across repeated tool calls.
    """

    if not source_type or not source_id:
        raise ValueError(
            f"{ToolErrorCode.PROVENANCE_UNAVAILABLE.value}: "
            "source_type and source_id are required"
        )

    raw_value = f"{source_type}:{source_id}"

    digest = hashlib.sha256(
        raw_value.encode("utf-8")
    ).hexdigest()[:16]

    return f"EV-{digest.upper()}"


def build_evidence(
    *,
    source_type: str,
    source_id: str,
    table: str,
    record_id: int,
    query_scope: str,
) -> Evidence:
    """
    Build a traceable evidence object for a database record.

    The evidence object identifies:
    - what type of source produced the evidence
    - which business identifier was used
    - which database table contains the record
    - which database record was returned
    - what query scope produced it
    """

    if not source_type:
        raise ValueError(
            f"{ToolErrorCode.PROVENANCE_UNAVAILABLE.value}: "
            "source_type is required"
        )

    if not source_id:
        raise ValueError(
            f"{ToolErrorCode.PROVENANCE_UNAVAILABLE.value}: "
            "source_id is required"
        )

    if not table:
        raise ValueError(
            f"{ToolErrorCode.PROVENANCE_UNAVAILABLE.value}: "
            "table is required"
        )

    if not isinstance(record_id, int) or isinstance(record_id, bool):
        raise ValueError(
            f"{ToolErrorCode.PROVENANCE_UNAVAILABLE.value}: "
            "record_id must be an integer"
        )

    if record_id < 1:
        raise ValueError(
            f"{ToolErrorCode.PROVENANCE_UNAVAILABLE.value}: "
            "record_id must be greater than zero"
        )

    if not query_scope:
        raise ValueError(
            f"{ToolErrorCode.PROVENANCE_UNAVAILABLE.value}: "
            "query_scope is required"
        )

    evidence_id = create_evidence_id(
        source_type=source_type,
        source_id=source_id,
    )

    provenance = Provenance(
        table=table,
        record_id=record_id,
        query_scope=query_scope,
    )

    return Evidence(
        evidence_id=evidence_id,
        source_type=source_type,
        source_id=source_id,
        provenance=provenance,
    )


def build_evidence_for_record(
    *,
    source_type: str,
    source_id: str,
    table: str,
    record_id: int,
    query_scope: str,
) -> Evidence:
    """
    Explicit alias used by database tools when creating
    evidence for a returned database record.
    """

    return build_evidence(
        source_type=source_type,
        source_id=source_id,
        table=table,
        record_id=record_id,
        query_scope=query_scope,
    )


def ensure_evidence(
    evidence: list[Evidence],
) -> list[Evidence]:
    """
    Fail closed if a successful tool result has no evidence.

    Tools that return database-derived investigation data
    should not silently return unsupported results.
    """

    if not evidence:
        raise ValueError(
            f"{ToolErrorCode.EVIDENCE_NOT_AVAILABLE.value}: "
            "No evidence was attached to the tool result"
        )

    return evidence