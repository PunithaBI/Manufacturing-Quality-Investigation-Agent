from app.db.database import SessionLocal
from app.retrieval.database_ingestion import ManufacturingDatabaseIngestion
from app.retrieval.manufacturing_chunking import chunk_manufacturing_document
from app.retrieval.documents import ManufacturingDocument

class DummyIngestionService:
    def ingest(self, documents):
        return 0

sample = ManufacturingDocument(
    document_id="chunk-test-001",
    source_type="capa",
    title="CAPA chunking test",
    content=(
        "Corrective action: Replace damaged component\n"
        "Preventive action: Inspect every batch"
    ),
    provenance={},
)

chunks = chunk_manufacturing_document(sample)
combined = "\n".join(chunk.content for chunk in chunks)

print("Chunk count:", len(chunks))
print("Corrective evidence preserved:", "Replace damaged component" in combined)
print("Preventive evidence preserved:", "Inspect every batch" in combined)

db = SessionLocal()
service = ManufacturingDatabaseIngestion(
    ingestion_service=DummyIngestionService()
)
try:
    for name, loader, limit in [
        ("8D", service._load_8d_reports, 500),
        ("RCA", service._load_rcas, 500),
        ("CAPA", service._load_capas, 500),
        ("Process measurements", service._load_process_measurements, 2000),
    ]:
        docs = loader(db, limit=limit)
        print(f"\n{name}: {len(docs)} documents")
        if docs:
            print("Sample ID:", docs[0].document_id)
            print("Sample content:", docs[0].content[:400])
        else:
            print("WARNING: No documents generated")
finally:
    db.close()
