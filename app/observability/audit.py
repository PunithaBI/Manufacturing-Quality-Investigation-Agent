from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class AuditRecord(BaseModel):
    timestamp: str = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        ).isoformat()
    )

    investigation_id: str

    actor: str
    action: str

    resource: str | None = None

    success: bool

    reason: str | None = None

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )


class AuditLogger:

    def __init__(
        self,
        *,
        db=None,
        repository=None,
    ) -> None:

        self.records: list[AuditRecord] = []

        self.db = db
        self.repository = repository

    def record(
        self,
        *,
        investigation_id: str,
        actor: str,
        action: str,
        resource: str | None = None,
        success: bool,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditRecord:

        record = AuditRecord(
            investigation_id=investigation_id,
            actor=actor,
            action=action,
            resource=resource,
            success=success,
            reason=reason,
            metadata=metadata or {},
        )

        self.records.append(record)

        if self.db is not None and self.repository is not None:
            self.repository.save_audit(
                self.db,
                record,
            )

        return record

    def export(self) -> list[dict[str, Any]]:
        return [
            record.model_dump()
            for record in self.records
        ]