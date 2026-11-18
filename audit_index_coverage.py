
import json
import sqlite3
from collections import Counter
from pathlib import Path

db_path = Path("data/Northwind_db/nordwind.db")
index_path = Path("data/vector_index/chunks.json")

if not db_path.exists() or not index_path.exists():
    raise SystemExit("Database or vector-index chunks file not found.")

with sqlite3.connect(
    db_path.resolve().as_uri() + "?mode=ro", uri=True
) as conn:
    conn.execute("PRAGMA query_only = ON")

    print("DATABASE SOURCE COUNTS")
    for table in (
        "eight_d_reports", "rca", "capa", "ncrs",
        "inspections", "process_measurements",
    ):
        count = conn.execute(
            f'SELECT COUNT(*) FROM "{table}"'
        ).fetchone()[0]
        print(f"{table}: {count}")

with index_path.open(encoding="utf-8") as f:
    chunks = json.load(f)

if not isinstance(chunks, list):
    raise SystemExit("Unexpected chunks.json structure; stopping safely.")

print(f"\nINDEX CHUNKS: {len(chunks)}")
if chunks:
    print("CHUNK KEYS:", list(chunks[0].keys()))
    print("SAMPLE PROVENANCE:", chunks[0].get("provenance"))

counts = Counter()
samples = {}

for chunk in chunks:
    provenance = chunk.get("provenance") or {}
    source = (
        provenance.get("table")
        or chunk.get("source_type")
        or chunk.get("table")
        or "UNKNOWN"
    )
    counts[str(source)] += 1
    samples.setdefault(str(source), chunk)

print("\nINDEX CHUNK COUNTS BY SOURCE")
for source, count in sorted(counts.items()):
    print(f"{source}: {count}")

print("\nSAMPLES FOR RELEVANT SOURCES")
for source, chunk in sorted(samples.items()):
    if any(word in source.lower() for word in (
        "eight", "8d", "rca", "capa", "inspection",
        "measurement", "ncr",
    )):
        print(f"\nSOURCE: {source}")
        print("PROVENANCE:", chunk.get("provenance"))

        for key in ("content", "text", "page_content", "document"):
            value = chunk.get(key)
            if isinstance(value, str):
                print("CONTENT:", value[:900])
                break
        else:
            print("CONTENT FIELD NOT FOUND; available keys:",
                  list(chunk.keys()))

print("\nAUDIT COMPLETE — no files or database records changed.")