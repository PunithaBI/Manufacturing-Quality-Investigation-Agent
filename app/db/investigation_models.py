from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Investigation(Base):
    __tablename__ = "investigations"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    investigation_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    ncr_number: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    state: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="CREATED",
    )

    hitl_required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    human_decision: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )

    human_comment: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    data_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="{}",
    )

    errors_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
    )

    history_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class InvestigationTraceEvent(Base):
    __tablename__ = "investigation_trace_events"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    trace_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    investigation_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    component: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    action: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    duration_ms: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    metadata_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="{}",
    )

    error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )


class InvestigationAuditRecord(Base):
    __tablename__ = "investigation_audit_records"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    investigation_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    actor: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    action: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    resource: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
    )

    success: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )

    reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    metadata_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="{}",
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )