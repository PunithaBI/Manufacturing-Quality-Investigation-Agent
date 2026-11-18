from app.db.database import SessionLocal
from app.retrieval.database_ingestion import ManufacturingDatabaseIngestion

TEMP_INDEX = "data/vector_index_candidate"

db = SessionLocal()
try:
    service = ManufacturingDatabaseIngestion(
        index_directory=TEMP_INDEX
    )
    result = service.ingest_all(db)

    print("\nCANDIDATE INDEX BUILD COMPLETE")
    print("Index directory:", TEMP_INDEX)
    print("Documents:", result["documents"])
    print("Chunks:", result["chunks"])
finally:
    db.close()
