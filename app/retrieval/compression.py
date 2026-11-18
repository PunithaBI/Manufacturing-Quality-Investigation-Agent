from __future__ import annotations

from .models import (
    CompressedEvidence,
    HybridEvidence,
    InvestigationContext,
)


def compress_context(
    query: str,
    evidence: list[HybridEvidence],
    max_items: int = 10,
) -> InvestigationContext:

    selected = evidence[:max_items]

    compressed: list[CompressedEvidence] = []

    for item in selected:

        summary = item.content or item.title or ""

        key_facts = []

        if item.title:
            key_facts.append(item.title)

        if item.source_type:
            key_facts.append(
                f"Source type: {item.source_type}"
            )

        compressed.append(
            CompressedEvidence(
                evidence_id=item.evidence_id,
                source_type=item.source_type,
                source_id=item.source_id,
                summary=summary,
                key_facts=key_facts,
                retrieval_methods=item.retrieval_methods,
                provenance=item.provenance,
            )
)

    original_count = len(evidence)

    compression_ratio = (
        len(compressed) / original_count
        if original_count
        else 1.0
    )

    return InvestigationContext(
        query=query,
        evidence=compressed,
        evidence_count=len(compressed),
        compression_ratio=compression_ratio,
    )