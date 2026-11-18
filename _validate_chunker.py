from app.retrieval.documents import ManufacturingDocument
from app.retrieval.manufacturing_chunking import chunk_manufacturing_document

cases = [
    (
        "inline_actions",
        "Corrective action: Replace damaged component\n"
        "Preventive action: Inspect every batch",
        ["Replace damaged component", "Inspect every batch"],
    ),
    (
        "rca_evidence",
        "Root cause: Fixture wear caused misalignment\n"
        "Analysis: Maintenance schedule adherence",
        ["Fixture wear caused misalignment", "Maintenance schedule adherence"],
    ),
    (
        "standalone_heading",
        "Investigation\nRoot cause:\nFixture wear caused misalignment",
        ["Fixture wear caused misalignment"],
    ),
]

for case_id, content, expected in cases:
    doc = ManufacturingDocument(
        document_id=case_id,
        source_type="test",
        title=case_id,
        content=content,
        provenance={},
    )
    chunks = chunk_manufacturing_document(doc)
    combined = "\n".join(chunk.content for chunk in chunks)
    missing = [phrase for phrase in expected if phrase not in combined]
    print(f"{case_id}: {'PASS' if not missing else 'FAIL'}")
    if missing:
        print("  Missing:", missing)
    print("  Chunks:", len(chunks))
