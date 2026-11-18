from typing import Generic, TypeVar

from pydantic import BaseModel, Field

from .errors import ToolErrorCode


T = TypeVar("T")


class ToolError(BaseModel):
    code: ToolErrorCode
    message: str


class Provenance(BaseModel):
    table: str
    record_id: int
    query_scope: str


class Evidence(BaseModel):
    evidence_id: str
    source_type: str
    source_id: str
    provenance: Provenance


class ToolMetadata(BaseModel):
    tool: str
    version: str = "1.0"
    result_count: int = 0


class ToolResult(BaseModel, Generic[T]):
    success: bool
    data: T | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    errors: list[ToolError] = Field(default_factory=list)
    metadata: ToolMetadata