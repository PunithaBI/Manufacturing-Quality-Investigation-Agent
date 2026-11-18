from __future__ import annotations

import time
import uuid
from contextlib import contextmanager
from typing import Any, Iterator

from sqlalchemy.orm import Session

from .models import TraceEvent, TraceStatus


class InvestigationTracer:

    def __init__(
        self,
        *,
        investigation_id: str,
        db: Session | None = None,
        repository=None,
    ) -> None:

        self.investigation_id = investigation_id

        self.trace_id = (
            f"TRACE-{uuid.uuid4().hex[:16].upper()}"
        )

        self.events: list[TraceEvent] = []

        self.db = db
        self.repository = repository

    def record(
        self,
        *,
        event_type: str,
        component: str,
        action: str,
        status: TraceStatus,
        duration_ms: float | None = None,
        metadata: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> TraceEvent:

        event = TraceEvent(
            trace_id=self.trace_id,
            investigation_id=self.investigation_id,
            event_type=event_type,
            component=component,
            action=action,
            status=status,
            duration_ms=duration_ms,
            metadata=metadata or {},
            error=error,
        )

        self.events.append(event)

        if self.db is not None and self.repository is not None:
            self.repository.save_trace_event(
                self.db,
                event,
            )

        return event

    @contextmanager
    def span(
        self,
        *,
        event_type: str,
        component: str,
        action: str,
        metadata: dict[str, Any] | None = None,
    ) -> Iterator[None]:

        started = time.perf_counter()

        self.record(
            event_type=event_type,
            component=component,
            action=action,
            status=TraceStatus.STARTED,
            metadata=metadata,
        )

        try:
            yield

        except Exception as exc:

            duration_ms = (
                time.perf_counter() - started
            ) * 1000

            self.record(
                event_type=event_type,
                component=component,
                action=action,
                status=TraceStatus.FAILED,
                duration_ms=round(
                    duration_ms,
                    2,
                ),
                metadata=metadata,
                error=str(exc),
            )

            raise

        else:

            duration_ms = (
                time.perf_counter() - started
            ) * 1000

            self.record(
                event_type=event_type,
                component=component,
                action=action,
                status=TraceStatus.SUCCESS,
                duration_ms=round(
                    duration_ms,
                    2,
                ),
                metadata=metadata,
            )

    def export(self) -> dict[str, Any]:

        return {
            "trace_id": self.trace_id,
            "investigation_id": self.investigation_id,
            "event_count": len(self.events),
            "events": [
                event.model_dump()
                for event in self.events
            ],
        }