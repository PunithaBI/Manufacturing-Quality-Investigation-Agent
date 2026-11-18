from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class InvestigationRequest(BaseModel):
    ncr_number: str
    investigation_id: str | None = None
    requested_by: str = "system"
    max_results: int = 20
    additional_evidence_request: str | None = None


class TraceabilityResult(BaseModel):
    status: AgentStatus

    ncr_number: str

    product: dict[str, Any] | None = None
    component: dict[str, Any] | None = None
    serial_unit: dict[str, Any] | None = None
    manufacturing_order: dict[str, Any] | None = None
    lot: dict[str, Any] | None = None

    relationships: list[dict[str, Any]] = Field(
        default_factory=list
    )

    evidence: list[dict[str, Any]] = Field(
        default_factory=list
    )

    evidence_gaps: list[str] = Field(
        default_factory=list
    )

    errors: list[str] = Field(
        default_factory=list
    )


class EvidencePackage(BaseModel):
    status: AgentStatus

    query: str

    evidence: list[dict[str, Any]] = Field(
        default_factory=list
    )

    evidence_count: int = 0

    retrieval_methods: list[str] = Field(
        default_factory=list
    )

    evidence_gaps: list[str] = Field(
        default_factory=list
    )

    errors: list[str] = Field(
        default_factory=list
    )


class RCAAnalysis(BaseModel):
    status: AgentStatus

    problem_statement: str

    potential_causes: list[dict[str, Any]] = Field(
        default_factory=list
    )

    supporting_evidence: list[str] = Field(
        default_factory=list
    )

    contradictory_evidence: list[str] = Field(
        default_factory=list
    )

    evidence_gaps: list[str] = Field(
        default_factory=list
    )

    recommended_next_steps: list[str] = Field(
        default_factory=list
    )

    conclusion: str | None = None


class ReviewResult(BaseModel):
    status: AgentStatus

    approved_for_hitl: bool

    checks: dict[str, bool] = Field(
        default_factory=dict
    )

    issues: list[str] = Field(
        default_factory=list
    )

    warnings: list[str] = Field(
        default_factory=list
    )

    reviewer_summary: str = ""


    
class InvestigationResult(BaseModel):
    status: AgentStatus

    investigation_id: str
    ncr_number: str

    traceability: TraceabilityResult | None = None

    evidence_package: EvidencePackage | None = None

    rca_analysis: RCAAnalysis | None = None

    review: ReviewResult | None = None

    hitl_required: bool = True

    errors: list[str] = Field(
        default_factory=list
    )

    workflow: list[str] = Field(
        default_factory=list
    )