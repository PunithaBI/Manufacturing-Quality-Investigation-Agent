from __future__ import annotations

from app.db.database import SessionLocal

from .database_ingestion import (
    ManufacturingDatabaseIngestion,
)


def main() -> None:

    db = SessionLocal()

    try:

        service = ManufacturingDatabaseIngestion()

        result = service.ingest_all(
            db
        )

        print()
        print(
            "DATABASE VECTOR INDEX BUILD COMPLETE"
        )
        print(
            f"Documents: {result['documents']}"
        )
        print(
            f"Chunks:    {result['chunks']}"
        )

    finally:

        db.close()


if __name__ == "__main__":
    main()