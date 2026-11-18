from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TraceStatus(str, Enum):
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class TraceEvent(BaseModel):
    timestamp: str = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        ).isoformat()
    )

    trace_id: str
    investigation_id: str

    event_type: str
    component: str
    action: str

    status: TraceStatus

    duration_ms: float | None = None

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )

    error: str | None = None