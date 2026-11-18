from __future__ import annotations

from sqlalchemy.orm import Session

from app.retrieval.models import RetrievalRequest
from app.retrieval.pipeline import (
    retrieve_investigation_context,
)

from .models import (
    AgentStatus,
    EvidencePackage,
    InvestigationRequest,
)


class EvidenceRetrievalAgent:
    """
    Retrieves investigation evidence using the existing
    hybrid retrieval pipeline.

    Retrieval channels are hidden behind the pipeline:

        Structured
        Graph
        Keyword
        Vector
    """

    def run(
        self,
        db: Session,
        request: InvestigationRequest,
    ) -> EvidencePackage:

        ncr_query = request.ncr_number.strip()

        additional_request = (
            request.additional_evidence_request or ""
        ).strip()

        if additional_request:
            query = (
                f"NCR: {ncr_query}\n"
                f"Additional evidence requested by reviewer: "
                f"{additional_request}"
            )
        else:
            query = ncr_query

        if not query:

            return EvidencePackage(
                status=AgentStatus.FAILED,
                query=query,
                errors=[
                    "NCR number is required."
                ],
            )

        try:

            context = retrieve_investigation_context(
                db,
                RetrievalRequest(
                    query=query,
                    investigation_id=(
                        request.investigation_id
                        or query
                    ),
                    max_results=request.max_results,
                ),
            )

        except Exception as exc:

            return EvidencePackage(
                status=AgentStatus.FAILED,
                query=query,
                errors=[
                    f"Evidence retrieval failed: {exc}"
                ],
            )

        # Convert the Pydantic CompressedEvidence models
        # into dictionaries for the EvidencePackage contract.
        evidence = [
            item.model_dump()
            for item in context.evidence
        ]

        retrieval_methods = sorted(
        {
            method
            for item in context.evidence
            for method in item.retrieval_methods
        }
)

        evidence_gaps: list[str] = []

        if not evidence:

            evidence_gaps.append(
                "No supporting evidence was retrieved."
            )

        if context.evidence_count < 3:

            evidence_gaps.append(
                "Limited supporting evidence was retrieved."
            )

        status = AgentStatus.SUCCESS

        if evidence_gaps:

            status = AgentStatus.PARTIAL

        return EvidencePackage(
            status=status,
            query=query,
            evidence=evidence,
            evidence_count=len(evidence),
            retrieval_methods=retrieval_methods,
            evidence_gaps=evidence_gaps,
        )

    @staticmethod
    def _methods(item) -> list[str]:
        """
        Extract retrieval methods from a CompressedEvidence model.

        CompressedEvidence is a Pydantic model, not a dictionary.
        """

        return item.retrieval_methods