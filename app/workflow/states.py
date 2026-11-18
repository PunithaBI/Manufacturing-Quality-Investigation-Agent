from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class WorkflowState(str, Enum):
    CREATED = "CREATED"
    TRACEABILITY = "TRACEABILITY"
    EVIDENCE_RETRIEVAL = "EVIDENCE_RETRIEVAL"
    RCA_ANALYSIS = "RCA_ANALYSIS"
    REVIEW = "REVIEW"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    NEEDS_MORE_EVIDENCE = "NEEDS_MORE_EVIDENCE"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"

class InvestigationState(BaseModel):
    investigation_id: str
    ncr_number: str

    state: WorkflowState = (
        WorkflowState.CREATED
    )

    data: dict[str, Any] = Field(
        default_factory=dict
    )

    errors: list[str] = Field(
        default_factory=list
    )

    history: list[str] = Field(
        default_factory=list
    )

    hitl_required: bool = True

    human_decision: str | None = None

    human_comment: str | None = None