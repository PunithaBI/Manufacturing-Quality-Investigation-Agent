from pathlib import Path
import json
import numpy as np

from app.retrieval.vector_store import LocalVectorStore

candidate = Path("data/vector_index_candidate")
store = LocalVectorStore(candidate)

print("=== CANDIDATE STORE LOAD TEST ===")
print("Loaded chunk count:", store.count)
print("Loaded vector shape:",
      None if store.vectors is None else store.vectors.shape)

if store.count != 1226:
    raise SystemExit("FAIL: Expected 1226 chunks after loading.")

if store.vectors is None or store.vectors.shape[0] != store.count:
    raise SystemExit("FAIL: Loaded vectors and chunks do not align.")

print("\n=== TARGET EVIDENCE CHECK ===")
terms = [
    "corrective action implemented on production line",
    "updated work instructions and inspection checklist",
    "root cause",
]

for term in terms:
    matches = [
        chunk for chunk in store.chunks
        if term in chunk.content.lower()
    ]
    print(f"\n{term!r}: {len(matches)} matching chunks")
    for chunk in matches[:2]:
        print("  source_type:", chunk.source_type)
        print("  source_id:", chunk.source_id)
        print("  title:", chunk.title)
        print("  content:", chunk.content[:350].replace("\n", " | "))

print("\n=== TEST COMPLETE ===")
