from __future__ import annotations

from app.db.database import Base, engine

# Import models so SQLAlchemy registers their tables.
from app.db.investigation_models import (  # noqa: F401
    Investigation,
    InvestigationAuditRecord,
    InvestigationTraceEvent,
)


def main() -> None:

    print(
        "Creating investigation persistence tables..."
    )

    Base.metadata.create_all(
        bind=engine,
        tables=[
            Investigation.__table__,
            InvestigationTraceEvent.__table__,
            InvestigationAuditRecord.__table__,
        ],
    )

    print(
        "Investigation persistence tables created."
    )

    print(
        "Tables:"
    )

    print(
        "  - investigations"
    )

    print(
        "  - investigation_trace_events"
    )

    print(
        "  - investigation_audit_records"
    )


if __name__ == "__main__":
    main()