from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.models import InvestigationRequest
from app.db.database import get_db
from app.security.input_guard import validate_investigation_input
from app.workflow.investigation_workflow import (
    ManufacturingInvestigationWorkflow,
)
from app.workflow.states import InvestigationState

router = APIRouter(
    prefix="/investigations",
    tags=["investigations"],
)

workflow = ManufacturingInvestigationWorkflow()
class HITLDecisionRequest(BaseModel):
    comment: str | None = None

@router.post(
    "",
    response_model=InvestigationState,
)
def create_investigation(
    request: InvestigationRequest,
    db: Session = Depends(get_db),
) -> InvestigationState:

    valid, errors = validate_investigation_input(
        ncr_number=request.ncr_number,
        investigation_id=request.investigation_id,
        max_results=request.max_results,
    )

    if not valid:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "SECURITY_VALIDATION_FAILED",
                "details": errors,
            },
        )

    try:

        return workflow.start(
            db=db,
            request=request,
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Investigation execution failed: {exc}",
        ) from exc


@router.get(
    "/{investigation_id}",
    response_model=InvestigationState,
)
def get_investigation(
    investigation_id: str,
    db: Session = Depends(get_db),
) -> InvestigationState:

    state = workflow.load(
        db,
        investigation_id,
    )

    if state is None:

        raise HTTPException(
            status_code=404,
            detail=(
                f"Investigation "
                f"'{investigation_id}' not found."
            ),
        )

    return state


@router.post(
    "/{investigation_id}/hitl",
    response_model=InvestigationState,
)
def submit_hitl_decision(
    investigation_id: str,
    decision: str,
    request: HITLDecisionRequest,
    db: Session = Depends(get_db),
) -> InvestigationState:

    state = workflow.load(
        db,
        investigation_id,
    )

    if state is None:

        raise HTTPException(
            status_code=404,
            detail=(
                f"Investigation "
                f"'{investigation_id}' not found."
            ),
        )

    try:

        return workflow.submit_human_decision(
            db=db,
            state=state,
            decision=decision,
            comment=request.comment,
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

@router.post(
    "/{investigation_id}/resume",
    response_model=InvestigationState,
)
def resume_investigation(
    investigation_id: str,
    requested_by: str = "human_reviewer",
    db: Session = Depends(get_db),
) -> InvestigationState:

    try:

        return workflow.resume_after_return(
            db=db,
            investigation_id=investigation_id,
            requested_by=requested_by,
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

@router.get(
    "/{investigation_id}/trace",
)
def get_investigation_trace(
    investigation_id: str,
    db: Session = Depends(get_db),
):

    state = workflow.load(
        db,
        investigation_id,
    )

    if state is None:

        raise HTTPException(
            status_code=404,
            detail=(
                f"Investigation "
                f"'{investigation_id}' not found."
            ),
        )

    records = workflow.repository.get_trace(
        db,
        investigation_id,
    )

    if not records:

        raise HTTPException(
            status_code=404,
            detail=(
                f"Trace for investigation "
                f"'{investigation_id}' not found."
            ),
        )

    return {
        "investigation_id": investigation_id,
        "trace_id": records[0].trace_id,
        "event_count": len(records),
        "events": [
            {
                "id": record.id,
                "trace_id": record.trace_id,
                "investigation_id": record.investigation_id,
                "event_type": record.event_type,
                "component": record.component,
                "action": record.action,
                "status": record.status,
                "duration_ms": record.duration_ms,
                "metadata": workflow._load_json(
                    record.metadata_json,
                    {},
                ),
                "error": record.error,
                "timestamp": record.timestamp.isoformat(),
            }
            for record in records
        ],
    }


@router.get(
    "/{investigation_id}/audit",
)
def get_investigation_audit(
    investigation_id: str,
    db: Session = Depends(get_db),
):

    state = workflow.load(
        db,
        investigation_id,
    )

    if state is None:

        raise HTTPException(
            status_code=404,
            detail=(
                f"Investigation "
                f"'{investigation_id}' not found."
            ),
        )

    records = workflow.repository.get_audit(
        db,
        investigation_id,
    )

    if not records:

        raise HTTPException(
            status_code=404,
            detail=(
                f"Audit records for investigation "
                f"'{investigation_id}' not found."
            ),
        )

    return {
        "investigation_id": investigation_id,
        "record_count": len(records),
        "records": [
            {
                "id": record.id,
                "investigation_id": record.investigation_id,
                "actor": record.actor,
                "action": record.action,
                "resource": record.resource,
                "success": record.success,
                "reason": record.reason,
                "metadata": workflow._load_json(
                    record.metadata_json,
                    {},
                ),
                "timestamp": record.timestamp.isoformat(),
            }
            for record in records
        ],
    }