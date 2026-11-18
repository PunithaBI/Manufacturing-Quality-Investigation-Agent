from __future__ import annotations

from sqlalchemy.orm import Session

from .evidence_agent import EvidenceRetrievalAgent
from .models import (
    AgentStatus,
    InvestigationRequest,
    InvestigationResult,
)
from .rca_agent import RCAAnalystAgent
from .reviewer import InvestigationReviewer
from .traceability_agent import ProductTraceabilityAgent


class InvestigationOrchestrator:
    """
    Coordinates the manufacturing investigation agents.

    Workflow:

        Orchestrator
             ↓
        Product/Traceability Agent
             ↓
        Evidence Retrieval Agent
             ↓
        RCA Analyst
             ↓
        Reviewer
             ↓
        HITL
    """

    def __init__(self) -> None:

        self.traceability_agent = (
            ProductTraceabilityAgent()
        )

        self.evidence_agent = (
            EvidenceRetrievalAgent()
        )

        self.rca_agent = (
            RCAAnalystAgent()
        )

        self.reviewer = (
            InvestigationReviewer()
        )

    def run(
        self,
        db: Session,
        request: InvestigationRequest,
    ) -> InvestigationResult:

        investigation_id = (
            request.investigation_id
            or f"INV-{request.ncr_number}"
        )

        workflow: list[str] = []

        errors: list[str] = []

        # ========================================================
        # 1. Product / Traceability Agent
        # ========================================================

        workflow.append(
            "ProductTraceabilityAgent"
        )

        traceability = (
            self.traceability_agent.run(
                db,
                request,
            )
        )

        if traceability.status == AgentStatus.FAILED:

            return InvestigationResult(
                status=AgentStatus.FAILED,
                investigation_id=investigation_id,
                ncr_number=request.ncr_number,
                traceability=traceability,
                hitl_required=True,
                errors=traceability.errors,
                workflow=workflow,
            )

        # ========================================================
        # 2. Evidence Retrieval Agent
        # ========================================================

        workflow.append(
            "EvidenceRetrievalAgent"
        )

        evidence = (
            self.evidence_agent.run(
                db,
                request,
            )
        )

        if evidence.status == AgentStatus.FAILED:

            errors.extend(
                evidence.errors
            )

            return InvestigationResult(
                status=AgentStatus.FAILED,
                investigation_id=investigation_id,
                ncr_number=request.ncr_number,
                traceability=traceability,
                evidence_package=evidence,
                hitl_required=True,
                errors=errors,
                workflow=workflow,
            )

        # ========================================================
        # 3. RCA Analyst
        # ========================================================

        workflow.append(
            "RCAAnalystAgent"
        )

        rca = self.rca_agent.run(
            traceability=traceability,
            evidence=evidence,
        )

        # ========================================================
        # 4. Reviewer
        # ========================================================

        workflow.append(
            "InvestigationReviewer"
        )

        review = self.reviewer.run(
            traceability=traceability,
            evidence=evidence,
            rca=rca,
        )

        # ========================================================
        # 5. HITL
        # ========================================================

        workflow.append(
            "HITL"
        )

        if review.approved_for_hitl:

            final_status = AgentStatus.SUCCESS

        else:

            final_status = AgentStatus.BLOCKED

        return InvestigationResult(
            status=final_status,
            investigation_id=investigation_id,
            ncr_number=request.ncr_number,
            traceability=traceability,
            evidence_package=evidence,
            rca_analysis=rca,
            review=review,
            hitl_required=True,
            errors=errors,
            workflow=workflow,
        )