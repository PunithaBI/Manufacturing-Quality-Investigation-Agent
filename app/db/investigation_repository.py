from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.observability.audit import AuditRecord
from app.observability.models import TraceEvent

from .investigation_models import (
    Investigation,
    InvestigationAuditRecord,
    InvestigationTraceEvent,
)


class InvestigationRepository:
    """
    Persistence layer for investigation state,
    tracing and audit records.
    """

    # ---------------------------------------------------------------
    # Investigation
    # ---------------------------------------------------------------

    def create(
        self,
        db: Session,
        *,
        investigation_id: str,
        ncr_number: str,
        state: str,
        hitl_required: bool,
        data: dict,
        errors: list[str],
        history: list[str],
    ) -> Investigation:

        record = Investigation(
            investigation_id=investigation_id,
            ncr_number=ncr_number,
            state=state,
            hitl_required=hitl_required,
            data_json=json.dumps(
                data,
                default=str,
            ),
            errors_json=json.dumps(
                errors,
                default=str,
            ),
            history_json=json.dumps(
                history,
                default=str,
            ),
        )

        db.add(record)
        db.commit()
        db.refresh(record)

        return record

    def get(
        self,
        db: Session,
        investigation_id: str,
    ) -> Investigation | None:

        statement = select(Investigation).where(
            Investigation.investigation_id == investigation_id
        )

        return db.scalar(statement)

    def update(
        self,
        db: Session,
        *,
        investigation_id: str,
        state: str,
        hitl_required: bool,
        human_decision: str | None,
        human_comment: str | None,
        data: dict,
        errors: list[str],
        history: list[str],
    ) -> Investigation:

        record = self.get(
            db,
            investigation_id,
        )

        if record is None:
            raise ValueError(
                f"Investigation '{investigation_id}' does not exist."
            )

        record.state = state
        record.hitl_required = hitl_required
        record.human_decision = human_decision
        record.human_comment = human_comment

        record.data_json = json.dumps(
            data,
            default=str,
        )

        record.errors_json = json.dumps(
            errors,
            default=str,
        )

        record.history_json = json.dumps(
            history,
            default=str,
        )

        record.updated_at = datetime.now(
            timezone.utc
        )

        db.commit()
        db.refresh(record)

        return record

    # ---------------------------------------------------------------
    # Trace
    # ---------------------------------------------------------------

    def save_trace_event(
        self,
        db: Session,
        event: TraceEvent,
    ) -> InvestigationTraceEvent:

        record = InvestigationTraceEvent(
            trace_id=event.trace_id,
            investigation_id=event.investigation_id,
            event_type=event.event_type,
            component=event.component,
            action=event.action,
            status=event.status.value,
            duration_ms=event.duration_ms,
            metadata_json=json.dumps(
                event.metadata,
                default=str,
            ),
            error=event.error,
            timestamp=datetime.fromisoformat(
                event.timestamp
            ),
        )

        db.add(record)
        db.commit()
        db.refresh(record)

        return record

    def get_trace(
        self,
        db: Session,
        investigation_id: str,
    ) -> list[InvestigationTraceEvent]:

        statement = (
            select(InvestigationTraceEvent)
            .where(
                InvestigationTraceEvent.investigation_id
                == investigation_id
            )
            .order_by(
                InvestigationTraceEvent.id
            )
        )

        return list(db.scalars(statement).all())

    # ---------------------------------------------------------------
    # Audit
    # ---------------------------------------------------------------

    def save_audit(
        self,
        db: Session,
        record: AuditRecord,
    ) -> InvestigationAuditRecord:

        database_record = InvestigationAuditRecord(
            investigation_id=record.investigation_id,
            actor=record.actor,
            action=record.action,
            resource=record.resource,
            success=record.success,
            reason=record.reason,
            metadata_json=json.dumps(
                record.metadata,
                default=str,
            ),
            timestamp=datetime.fromisoformat(
                record.timestamp
            ),
        )

        db.add(database_record)
        db.commit()
        db.refresh(database_record)

        return database_record

    def get_audit(
        self,
        db: Session,
        investigation_id: str,
    ) -> list[InvestigationAuditRecord]:

        statement = (
            select(InvestigationAuditRecord)
            .where(
                InvestigationAuditRecord.investigation_id
                == investigation_id
            )
            .order_by(
                InvestigationAuditRecord.id
            )
        )

        return list(db.scalars(statement).all())