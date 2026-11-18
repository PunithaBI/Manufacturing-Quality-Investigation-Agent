from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.db.models import (
    BOM,
    CAPA,
    Component,
    Document,
    EightDReport,
    Inspection,
    Lot,
    ManufacturingOrder,
    NCR,
    Operation,
    ProcessMeasurement,
    Product,
    RCA,
    SerialUnit,
)


SOURCE_DB = Path("/seed/nordwind.db")

SOURCE_ENGINE = create_engine(
    f"sqlite:///{SOURCE_DB}",
    connect_args={"check_same_thread": False},
)

TARGET_ENGINE = create_engine(
    settings.database_url,
    pool_pre_ping=True,
)


TABLES = [
    Product,
    Component,
    BOM,
    Lot,
    ManufacturingOrder,
    SerialUnit,
    Operation,
    ProcessMeasurement,
    Inspection,
    NCR,
    EightDReport,
    RCA,
    CAPA,
    Document,
]


def migrate_table(
    source: Session,
    target: Session,
    model,
) -> int:

    rows = source.execute(
        select(model)
    ).scalars().all()

    if not rows:
        return 0

    column_names = [
        column.name
        for column in model.__table__.columns
    ]

    records = []

    for row in rows:
        records.append(
            {
                column_name: getattr(
                    row,
                    column_name,
                )
                for column_name in column_names
            }
        )

    target.execute(
        model.__table__.insert(),
        records,
    )

    return len(records)


def verify_target_empty(target: Session) -> None:

    for model in TABLES:

        count = target.execute(
            select(model)
        ).scalars().all()

        if count:
            raise RuntimeError(
                f"Target table '{model.__tablename__}' "
                "is not empty. Migration aborted."
            )


def reset_sequences(target: Session) -> None:

    for model in TABLES:

        table_name = model.__tablename__

        target.execute(
            text(
                f"""
                SELECT setval(
                    pg_get_serial_sequence(
                        '{table_name}',
                        'id'
                    ),
                    COALESCE(MAX(id), 1),
                    MAX(id) IS NOT NULL
                )
                FROM {table_name}
                """
            )
        )


def main() -> None:

    print("========================================")
    print("MQI MANUFACTURING DATA MIGRATION")
    print("========================================")

    print(f"Source: {SOURCE_DB}")

    print(
        "Target:",
        TARGET_ENGINE.url.render_as_string(
            hide_password=True
        ),
    )

    print()

    if not SOURCE_DB.exists():
        raise FileNotFoundError(
            f"Source database not found: {SOURCE_DB}"
        )

    with Session(SOURCE_ENGINE) as source:

        with Session(TARGET_ENGINE) as target:

            print("Checking target database...")

            verify_target_empty(target)

            print("Target is empty.")
            print()

            total = 0

            for model in TABLES:

                count = migrate_table(
                    source,
                    target,
                    model,
                )

                total += count

                print(
                    f"{model.__tablename__:25s}"
                    f"{count:>6d}"
                )

            reset_sequences(target)

            target.commit()

            print()
            print(f"TOTAL ROWS MIGRATED: {total}")

    print()
    print("MANUFACTURING DATA MIGRATION COMPLETE")


if __name__ == "__main__":
    main()