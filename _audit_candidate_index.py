import json
from collections import Counter
from pathlib import Path
import numpy as np

index_dir = Path("data/vector_index_candidate")
chunks_path = index_dir / "chunks.json"
vectors_path = index_dir / "vectors.npy"

print("=== CANDIDATE VECTOR INDEX AUDIT ===")

with chunks_path.open("r", encoding="utf-8-sig") as f:
    chunks = json.load(f)

vectors = np.load(vectors_path, mmap_mode="r", allow_pickle=False)

print("Chunk records:", len(chunks))
print("Vector shape:", vectors.shape)
print("Vector dtype:", vectors.dtype)

if not isinstance(chunks, list):
    raise TypeError("Expected chunks.json to contain a JSON list.")

if not chunks:
    raise ValueError("No chunk records found.")

print("\nRecord fields:", sorted(chunks[0].keys()))
print("First record sample:")
print(json.dumps(chunks[0], ensure_ascii=False, indent=2)[:1800])

ids = [c.get("chunk_id") for c in chunks]
valid_ids = [x for x in ids if isinstance(x, str) and x.strip()]
print("\nUnique chunk IDs:", len(set(valid_ids)))
print("Missing/invalid chunk IDs:", len(chunks) - len(valid_ids))
print("Duplicate chunk IDs:", len(valid_ids) - len(set(valid_ids)))

print("\nSource counts from chunk ID prefixes:")
prefix_counts = Counter(
    x.split(":", 1)[0] for x in valid_ids
)
for name, count in sorted(prefix_counts.items()):
    print(f"  {name}: {count}")

text_keys = ("text", "content", "chunk_text", "page_content")
text_key = next(
    (key for key in text_keys if any(key in c for c in chunks)),
    None
)

if text_key:
    empty_text = sum(
        not isinstance(c.get(text_key), str) or not c[text_key].strip()
        for c in chunks
    )
    print(f"\nText field checked: {text_key}")
    print("Empty/missing text records:", empty_text)

    for term in (
        "corrective action",
        "preventive action",
        "root cause",
        "implementation",
    ):
        matches = sum(
            term in c.get(text_key, "").lower()
            for c in chunks
            if isinstance(c.get(text_key), str)
        )
        print(f"Records containing '{term}': {matches}")
else:
    print("\nText field not identified automatically; inspect the sample above.")

print("\nVector rows match chunk count:", vectors.ndim == 2 and vectors.shape[0] == len(chunks))
print("Vector dimensions:", vectors.shape[1] if vectors.ndim == 2 else "INVALID")
print("All vector values finite:", bool(np.isfinite(vectors).all()))
print("\n=== AUDIT FINISHED ===")
