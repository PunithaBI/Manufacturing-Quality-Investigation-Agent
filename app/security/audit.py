from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class SecurityAuditEvent(BaseModel):
    timestamp: str = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        ).isoformat()
    )

    investigation_id: str | None = None
    actor: str = "system"
    action: str
    resource: str | None = None

    success: bool
    reason: str | None = None

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )