from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RetrievalEvidence(BaseModel):
    evidence_id: str

    source_type: str
    source_id: str

    retrieval_method: str

    title: str | None = None
    content: str | None = None

    score: float | None = None

    metadata: dict[str, Any] = Field(default_factory=dict)

    provenance: dict[str, Any] = Field(default_factory=dict)


class RetrievalRequest(BaseModel):
    query: str

    investigation_id: str | None = None

    max_results: int = 20


class RetrievalResult(BaseModel):
    success: bool

    evidence: list[RetrievalEvidence] = Field(
        default_factory=list
    )

    errors: list[str] = Field(
        default_factory=list
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )


class HybridEvidence(BaseModel):
    evidence_id: str

    source_type: str
    source_id: str

    retrieval_methods: list[str] = Field(
        default_factory=list
    )

    title: str | None = None

    content: str | None = None

    scores: dict[str, float] = Field(
        default_factory=dict
    )

    combined_score: float | None = None

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )

    provenance: dict[str, Any] = Field(
        default_factory=dict
    )


class HybridRetrievalResult(BaseModel):
    success: bool

    evidence: list[HybridEvidence] = Field(
        default_factory=list
    )

    errors: list[str] = Field(
        default_factory=list
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )


class CompressedEvidence(BaseModel):
    evidence_id: str
    source_type: str
    source_id: str
    summary: str
    key_facts: list[str] = Field(default_factory=list)
    retrieval_methods: list[str] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict
    )


class InvestigationContext(BaseModel):
    query: str

    evidence: list[CompressedEvidence] = Field(
        default_factory=list
    )

    evidence_count: int = 0

    compression_ratio: float | None = None