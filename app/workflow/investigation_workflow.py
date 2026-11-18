from __future__ import annotations

from sqlalchemy.orm import Session

from app.agents.models import (
    AgentStatus,
    InvestigationRequest,
)
from app.agents.orchestrator import InvestigationOrchestrator
from app.db.investigation_repository import InvestigationRepository
from app.observability.audit import AuditLogger
from app.observability.models import TraceStatus
from app.observability.tracer import InvestigationTracer

from .states import (
    InvestigationState,
    WorkflowState,
)


class ManufacturingInvestigationWorkflow:
    """
    Coordinates the complete manufacturing quality investigation workflow.

    Workflow:

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

        self.orchestrator = InvestigationOrchestrator()

        self.repository = InvestigationRepository()

    # ------------------------------------------------------------------
    # Start investigation
    # ------------------------------------------------------------------

    def start(
        self,
        db: Session,
        request: InvestigationRequest,
    ) -> InvestigationState:

        investigation_id = (
            request.investigation_id
            or self._generate_investigation_id(
                request.ncr_number
            )
        )

        existing = self.repository.get(
            db,
            investigation_id,
        )

        if existing is not None:
            raise ValueError(
                f"Investigation '{investigation_id}' already exists."
            )

        state = InvestigationState(
            investigation_id=investigation_id,
            ncr_number=request.ncr_number,
            state=WorkflowState.CREATED,
            hitl_required=True,
        )

        state.history.append(
            WorkflowState.CREATED.value
        )

        self.repository.create(
            db,
            investigation_id=state.investigation_id,
            ncr_number=state.ncr_number,
            state=state.state.value,
            hitl_required=state.hitl_required,
            data=state.data,
            errors=state.errors,
            history=state.history,
        )

        tracer = InvestigationTracer(
            investigation_id=investigation_id,
            db=db,
            repository=self.repository,
        )

        audit = AuditLogger(
            db=db,
            repository=self.repository,
        )

        audit.record(
            investigation_id=investigation_id,
            actor=request.requested_by,
            action="INVESTIGATION_STARTED",
            resource=request.ncr_number,
            success=True,
            metadata={
                "max_results": request.max_results,
            },
        )

        tracer.record(
            event_type="workflow",
            component="investigation_workflow",
            action="investigation_started",
            status=TraceStatus.STARTED,
            metadata={
                "ncr_number": request.ncr_number,
                "requested_by": request.requested_by,
            },
        )

        try:

            with tracer.span(
                event_type="agent",
                component="orchestrator",
                action="investigation_execution",
                metadata={
                    "ncr_number": request.ncr_number,
                },
            ):

                result = self.orchestrator.run(
                    db=db,
                    request=request,
                )

        except Exception as exc:

            state.state = WorkflowState.FAILED

            state.errors.append(
                f"Workflow execution failed: {exc}"
            )

            state.history.append(
                WorkflowState.FAILED.value
            )

            tracer.record(
                event_type="workflow",
                component="investigation_workflow",
                action="workflow_failed",
                status=TraceStatus.FAILED,
                error=str(exc),
            )

            audit.record(
                investigation_id=investigation_id,
                actor=request.requested_by,
                action="INVESTIGATION_FAILED",
                resource=request.ncr_number,
                success=False,
                reason=str(exc),
            )

            self._persist_state(
                db,
                state,
            )

            return state

        self._apply_result(
            state=state,
            result=result,
        )

        if state.state == WorkflowState.HUMAN_REVIEW:

            tracer.record(
                event_type="workflow",
                component="investigation_workflow",
                action="workflow_ready_for_hitl",
                status=TraceStatus.SUCCESS,
                metadata={
                    "state": state.state.value,
                    "hitl_required": state.hitl_required,
                },
            )

            audit.record(
                investigation_id=investigation_id,
                actor="system",
                action="INVESTIGATION_READY_FOR_HITL",
                resource=request.ncr_number,
                success=True,
            )

        elif state.state == WorkflowState.BLOCKED:

            tracer.record(
                event_type="workflow",
                component="investigation_workflow",
                action="workflow_blocked",
                status=TraceStatus.BLOCKED,
                metadata={
                    "state": state.state.value,
                    "errors": state.errors,
                },
            )

            audit.record(
                investigation_id=investigation_id,
                actor="system",
                action="INVESTIGATION_BLOCKED",
                resource=request.ncr_number,
                success=False,
                reason="Investigation blocked before HITL.",
            )

        elif state.state == WorkflowState.FAILED:

            tracer.record(
                event_type="workflow",
                component="investigation_workflow",
                action="workflow_failed",
                status=TraceStatus.FAILED,
                metadata={
                    "state": state.state.value,
                },
            )

            audit.record(
                investigation_id=investigation_id,
                actor="system",
                action="INVESTIGATION_FAILED",
                resource=request.ncr_number,
                success=False,
                reason="Workflow failed.",
            )

        self._persist_state(
            db,
            state,
        )

        return state

    # ------------------------------------------------------------------
    # Load investigation
    # ------------------------------------------------------------------

    def load(
        self,
        db: Session,
        investigation_id: str,
    ) -> InvestigationState | None:

        record = self.repository.get(
            db,
            investigation_id,
        )

        if record is None:
            return None

        return InvestigationState(
            investigation_id=record.investigation_id,
            ncr_number=record.ncr_number,
            state=WorkflowState(record.state),
            data=self._load_json(
                record.data_json,
                {},
            ),
            errors=self._load_json(
                record.errors_json,
                [],
            ),
            history=self._load_json(
                record.history_json,
                [],
            ),
            hitl_required=record.hitl_required,
            human_decision=record.human_decision,
            human_comment=record.human_comment,
        )

    # ------------------------------------------------------------------
    # Human decision
    # ------------------------------------------------------------------

    def submit_human_decision(
        self,
        db: Session,
        state: InvestigationState,
        decision: str,
        comment: str | None = None,
    ) -> InvestigationState:

        decision = decision.strip().upper()

        allowed_decisions = {
            "APPROVE",
            "REJECT",
            "RETURN",
        }

        if decision not in allowed_decisions:
            raise ValueError(
                "Invalid HITL decision. "
                "Allowed values: APPROVE, REJECT, RETURN."
            )

        if state.state != WorkflowState.HUMAN_REVIEW:
            raise ValueError(
                "Human decision can only be submitted "
                "when the investigation is in HUMAN_REVIEW state."
            )

        tracer = InvestigationTracer(
            investigation_id=state.investigation_id,
            db=db,
            repository=self.repository,
        )

        audit = AuditLogger(
            db=db,
            repository=self.repository,
        )

        # --------------------------------------------------------------
        # APPROVE
        # --------------------------------------------------------------

        if decision == "APPROVE":

            state.human_decision = "APPROVE"
            state.human_comment = comment

            state.state = WorkflowState.COMPLETED

            state.history.append(
                WorkflowState.COMPLETED.value
            )

            tracer.record(
                event_type="hitl",
                component="human_review",
                action="human_decision",
                status=TraceStatus.SUCCESS,
                metadata={
                    "decision": "APPROVE",
                    "comment_provided": bool(comment),
                },
            )

            tracer.record(
                event_type="workflow",
                component="investigation_workflow",
                action="investigation_completed",
                status=TraceStatus.SUCCESS,
            )

            audit.record(
                investigation_id=state.investigation_id,
                actor="human_reviewer",
                action="HITL_APPROVED",
                resource=state.ncr_number,
                success=True,
                metadata={
                    "comment_provided": bool(comment),
                },
            )

        # --------------------------------------------------------------
        # REJECT
        # --------------------------------------------------------------

        elif decision == "REJECT":

            state.human_decision = "REJECT"
            state.human_comment = comment

            state.state = WorkflowState.BLOCKED

            state.history.append(
                WorkflowState.BLOCKED.value
            )

            tracer.record(
                event_type="hitl",
                component="human_review",
                action="human_decision",
                status=TraceStatus.BLOCKED,
                metadata={
                    "decision": "REJECT",
                    "comment_provided": bool(comment),
                },
            )

            tracer.record(
                event_type="workflow",
                component="investigation_workflow",
                action="investigation_blocked",
                status=TraceStatus.BLOCKED,
            )

            audit.record(
                investigation_id=state.investigation_id,
                actor="human_reviewer",
                action="HITL_REJECTED",
                resource=state.ncr_number,
                success=False,
                reason=comment
                or "Human reviewer rejected investigation.",
            )

        # --------------------------------------------------------------
        # RETURN
        # --------------------------------------------------------------

        else:

            state.human_decision = "RETURN"
            state.human_comment = comment
            state.data["pending_evidence_request"] = {
                "decision": "RETURN",
                "comment": comment,
            }

            state.state = WorkflowState.NEEDS_MORE_EVIDENCE

            state.history.append(
                WorkflowState.NEEDS_MORE_EVIDENCE.value
            )

            tracer.record(
                event_type="hitl",
                component="human_review",
                action="human_decision",
                status=TraceStatus.SUCCESS,
                metadata={
                    "decision": "RETURN",
                    "comment_provided": bool(comment),
                },
            )

            audit.record(
                investigation_id=state.investigation_id,
                actor="human_reviewer",
                action="HITL_RETURNED",
                resource=state.ncr_number,
                success=True,
                reason=comment
                or "Investigation returned for further evidence.",
            )

        # --------------------------------------------------------------
        # Persist HITL decision
        # --------------------------------------------------------------

        self._persist_state(
            db,
            state,
        )

        return state

    # ------------------------------------------------------------------
    # Resume investigation after HUMAN_REVIEW RETURN
    # ------------------------------------------------------------------

    def resume_after_return(
        self,
        db: Session,
        investigation_id: str,
        requested_by: str = "human_reviewer",
    ) -> InvestigationState:

        state = self.load(
            db=db,
            investigation_id=investigation_id,
        )

        if state is None:
            raise ValueError(
                f"Investigation '{investigation_id}' not found."
            )

        # --------------------------------------------------------------
        # Guard: only RETURN may restart an investigation
        # --------------------------------------------------------------

        if state.human_decision != "RETURN":
            raise ValueError(
                "Additional investigation can only be started "
                "after a HUMAN_REVIEW RETURN decision."
            )

        tracer = InvestigationTracer(
            investigation_id=state.investigation_id,
            db=db,
            repository=self.repository,
        )

        audit = AuditLogger(
            db=db,
            repository=self.repository,
        )

        # --------------------------------------------------------------
        # Record that additional investigation has started
        # --------------------------------------------------------------

        tracer.record(
            event_type="workflow",
            component="investigation_workflow",
            action="additional_investigation_started",
            status=TraceStatus.STARTED,
            metadata={
                "requested_by": requested_by,
                "previous_decision": "RETURN",
                "previous_comment": state.human_comment,
            },
        )

        audit.record(
            investigation_id=state.investigation_id,
            actor=requested_by,
            action="ADDITIONAL_INVESTIGATION_STARTED",
            resource=state.ncr_number,
            success=True,
            metadata={
                "previous_decision": "RETURN",
                "previous_comment": state.human_comment,
            },
        )

        # --------------------------------------------------------------
        # Re-run the existing orchestrator
        # --------------------------------------------------------------

        request = InvestigationRequest(
            investigation_id=state.investigation_id,
            ncr_number=state.ncr_number,
            requested_by=requested_by,
             additional_evidence_request=(
                state.data.get("pending_evidence_request", {}).get("comment")
                if isinstance(state.data.get("pending_evidence_request"), dict)
                else None
            ),
        )

        try:

            result = self.orchestrator.run(
                db=db,
                request=request,
            )

        except Exception as exc:

            state.state = WorkflowState.FAILED
            state.hitl_required = False

            state.errors.append(
                f"Additional investigation failed: {exc}"
            )

            state.history.append(
                WorkflowState.FAILED.value
            )

            tracer.record(
                event_type="workflow",
                component="investigation_workflow",
                action="additional_investigation_failed",
                status=TraceStatus.FAILED,
                error=str(exc),
            )

            audit.record(
                investigation_id=state.investigation_id,
                actor=requested_by,
                action="ADDITIONAL_INVESTIGATION_FAILED",
                resource=state.ncr_number,
                success=False,
                reason=str(exc),
            )

            self._persist_state(
                db,
                state,
            )

            return state

        # --------------------------------------------------------------
        # Preserve the previous reviewer request, then clear the
        # active HITL decision for the new investigation cycle.
        # --------------------------------------------------------------

        previous_comment = state.human_comment

        state.data["previous_human_review"] = {
            "decision": "RETURN",
            "comment": previous_comment,
        }

        state.human_decision = None
        state.human_comment = None

        # --------------------------------------------------------------
        # Apply fresh orchestration result
        # --------------------------------------------------------------

        self._apply_result(
            state=state,
            result=result,
        )

        # --------------------------------------------------------------
        # Record new HITL state
        # --------------------------------------------------------------

        if state.state == WorkflowState.HUMAN_REVIEW:

            tracer.record(
                event_type="workflow",
                component="investigation_workflow",
                action="additional_investigation_ready_for_hitl",
                status=TraceStatus.SUCCESS,
                metadata={
                    "state": state.state.value,
                    "hitl_required": state.hitl_required,
                },
            )

            audit.record(
                investigation_id=state.investigation_id,
                actor="system",
                action="ADDITIONAL_INVESTIGATION_READY_FOR_HITL",
                resource=state.ncr_number,
                success=True,
            )

        elif state.state == WorkflowState.BLOCKED:

            tracer.record(
                event_type="workflow",
                component="investigation_workflow",
                action="additional_investigation_blocked",
                status=TraceStatus.BLOCKED,
                metadata={
                    "state": state.state.value,
                    "errors": state.errors,
                },
            )

        elif state.state == WorkflowState.FAILED:

            tracer.record(
                event_type="workflow",
                component="investigation_workflow",
                action="additional_investigation_failed",
                status=TraceStatus.FAILED,
                metadata={
                    "state": state.state.value,
                },
            )

        self._persist_state(
            db,
            state,
        )

        return state

    # ------------------------------------------------------------------
    # Apply orchestrator result
    # ------------------------------------------------------------------

    def _apply_result(
        self,
        *,
        state: InvestigationState,
        result,
    ) -> None:

        state.data["investigation_result"] = (
            result.model_dump()
        )

        if result.traceability is not None:

            state.data["traceability"] = (
                result.traceability.model_dump()
            )

            state.state = WorkflowState.TRACEABILITY

            state.history.append(
                WorkflowState.TRACEABILITY.value
            )

        if result.evidence_package is not None:

            state.data["evidence_package"] = (
                result.evidence_package.model_dump()
            )

            state.state = WorkflowState.EVIDENCE_RETRIEVAL

            state.history.append(
                WorkflowState.EVIDENCE_RETRIEVAL.value
            )

        if result.rca_analysis is not None:

            state.data["rca_analysis"] = (
                result.rca_analysis.model_dump()
            )

            state.state = WorkflowState.RCA_ANALYSIS

            state.history.append(
                WorkflowState.RCA_ANALYSIS.value
            )

        if result.review is not None:

            state.data["review"] = (
                result.review.model_dump()
            )

            state.state = WorkflowState.REVIEW

            state.history.append(
                WorkflowState.REVIEW.value
            )

        if result.errors:
            state.errors.extend(
                result.errors
            )

        if result.status == AgentStatus.SUCCESS:

            state.state = WorkflowState.HUMAN_REVIEW
            state.hitl_required = True

            state.history.append(
                WorkflowState.HUMAN_REVIEW.value
            )

        elif result.status == AgentStatus.BLOCKED:

            state.state = WorkflowState.BLOCKED
            state.hitl_required = False

            state.history.append(
                WorkflowState.BLOCKED.value
            )

        elif result.status == AgentStatus.FAILED:

            state.state = WorkflowState.FAILED
            state.hitl_required = False

            state.history.append(
                WorkflowState.FAILED.value
            )

        else:

            state.state = WorkflowState.BLOCKED
            state.hitl_required = False

            state.history.append(
                WorkflowState.BLOCKED.value
            )

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _persist_state(
        self,
        db: Session,
        state: InvestigationState,
    ) -> None:

        self.repository.update(
            db,
            investigation_id=state.investigation_id,
            state=state.state.value,
            hitl_required=state.hitl_required,
            human_decision=state.human_decision,
            human_comment=state.human_comment,
            data=state.data,
            errors=state.errors,
            history=state.history,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load_json(
        value: str,
        default,
    ):
        import json

        try:
            return json.loads(value)
        except Exception:
            return default

    @staticmethod
    def _generate_investigation_id(
        ncr_number: str,
    ) -> str:

        cleaned = (
            ncr_number
            .strip()
            .replace(" ", "-")
        )

        return f"INV-{cleaned}"

