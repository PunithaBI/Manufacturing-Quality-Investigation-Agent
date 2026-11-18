from app.db.database import SessionLocal
from app.db import models
from app.retrieval.database_ingestion import ManufacturingDatabaseIngestion

db = SessionLocal()
service = ManufacturingDatabaseIngestion(
    ingestion_service=object()
)

try:
    row = (
        db.query(models.EightDReport)
        .filter(models.EightDReport.report_number == "8D-20260001")
        .first()
    )

    print("DATABASE ROW")
    print("Report:", row.report_number)
    print("D6 raw value:", repr(row.d6_implementation))

    docs = service._load_8d_reports(db, limit=500)
    doc = next(
        d for d in docs
        if d.document_id == "8d:8D-20260001"
    )

    print("\nGENERATED DOCUMENT")
    print(doc.content)

    print("\nCHECK")
    print(
        "Full D6 sentence preserved:",
        row.d6_implementation in doc.content,
    )
finally:
    db.close()
