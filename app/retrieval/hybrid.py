from __future__ import annotations

from collections import defaultdict

from .models import (
    HybridEvidence,
    HybridRetrievalResult,
    RetrievalEvidence,
)


METHOD_WEIGHTS = {
    "structured": 1.00,
    "graph": 0.90,
    "keyword": 0.70,
    "vector": 0.80,
}


def combine_evidence(
    evidence: list[RetrievalEvidence],
    *,
    max_results: int = 20,
) -> HybridRetrievalResult:

    grouped: dict[str, list[RetrievalEvidence]] = defaultdict(list)

    for item in evidence:
        grouped[item.evidence_id].append(item)

    combined: list[HybridEvidence] = []

    for evidence_id, items in grouped.items():

        methods = sorted(
            {
                item.retrieval_method
                for item in items
            }
        )

        scores = {}

        for item in items:
            base_score = (
                item.score
                if item.score is not None
                else 1.0
            )

            weight = METHOD_WEIGHTS.get(
                item.retrieval_method,
                0.5,
            )

            scores[item.retrieval_method] = (
                base_score * weight
            )

        combined_score = sum(scores.values())

        primary = items[0]

        combined.append(
            HybridEvidence(
                evidence_id=evidence_id,
                source_type=primary.source_type,
                source_id=primary.source_id,
                retrieval_methods=methods,
                title=primary.title,
                content=primary.content,
                scores=scores,
                combined_score=combined_score,
                metadata=primary.metadata,
                provenance=primary.provenance,
            )
        )

    combined.sort(
        key=lambda item: (
            item.combined_score or 0.0
        ),
        reverse=True,
    )

    combined = combined[:max_results]

    return HybridRetrievalResult(
        success=True,
        evidence=combined,
        metadata={
            "input_evidence_count": len(evidence),
            "unique_evidence_count": len(combined),
            "retrieval_methods": sorted(
                {
                    item.retrieval_method
                    for item in evidence
                }
            ),
        },
    )