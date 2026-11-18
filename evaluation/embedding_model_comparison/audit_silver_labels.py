
import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path.cwd()

LABELS_PATH = (
    ROOT / "evaluation" / "embedding_model_comparison"
    / "silver_label_evaluation_candidate" / "silver_labels.json"
)
CHUNKS_PATH = ROOT / "data" / "vector_index_candidate" / "chunks.json"
OUTPUT_DIR = ROOT / "evaluation" / "embedding_model_comparison" / "audit"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_records(data):
    """Support list-based and dictionary-based corpus files."""
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        if isinstance(data.get("chunks"), list):
            return data["chunks"]

        # Some corpus formats use a dictionary keyed by chunk ID.
        values = list(data.values())
        if values and all(isinstance(v, dict) for v in values):
            return values

    raise ValueError(
        "Unrecognized chunks.json structure. "
        "Inspect its top-level keys before proceeding."
    )


def get_chunk_id(record):
    if record.get("chunk_id") is not None:
        return str(record["chunk_id"])

    return str(record.get("id", ""))


def get_reason(case, chunk_id):
    # Read a per-chunk reason if the current JSON contains one.
    for field in (
        "chunk_reasons",
        "label_reasons",
        "reasons",
        "chunk_label_reasons",
    ):
        mapping = case.get(field, {})
        if isinstance(mapping, dict) and chunk_id in mapping:
            value = mapping[chunk_id]
            if isinstance(value, (dict, list)):
                return json.dumps(value, ensure_ascii=False)
            return str(value)

    return ""


def main():
    labels = load_json(LABELS_PATH)
    corpus = load_json(CHUNKS_PATH)
    records = get_records(corpus)

    print("=== READ-ONLY CANDIDATE LABEL AUDIT ===")
    print("Candidate chunk count:", len(records))
    print("Corpus path:", CHUNKS_PATH.relative_to(ROOT))
    print("Labels path:", LABELS_PATH.relative_to(ROOT))
    print("Production index accessed: NO")
    print("Model downloads: NONE")

    if records:
        print("Chunk fields:", list(records[0].keys()))

    print("Label case IDs:", list(labels.get("cases", {}).keys()))

    chunk_lookup = {}
    for record in records:
        cid = get_chunk_id(record)
        if cid:
            chunk_lookup[cid] = record

    all_rows = []
    anomaly_rows = []
    unmatched = []

    for case_id, case in labels.get("cases", {}).items():
        grades = case.get("chunk_grades", {})

        print(f"\n{case_id}: {len(grades)} labeled chunks")

        source_counts = Counter()
        grade_counts = Counter()

        for cid, grade in grades.items():
            source_type = cid.split(":", 1)[0]
            source_counts[source_type] += 1
            grade_counts[str(grade)] += 1

            record = chunk_lookup.get(cid)

            # Try a fallback if the stored ID differs in format.
            if record is None:
                record = next(
                    (
                        r for r in records
                        if str(r.get("document_id", "")) == cid
                    ),
                    None,
                )

            if record is None:
                unmatched.append((case_id, cid, grade))
                content = ""
                metadata = {}
                provenance = {}
                source_id = ""
                actual_source_type = source_type
            else:
                content = str(record.get("content", ""))
                metadata = record.get("metadata", {})
                provenance = record.get("provenance", {})
                source_id = str(record.get("source_id", ""))
                actual_source_type = str(
                    record.get("source_type", source_type)
                )

            reason = get_reason(case, cid)

            row = {
                "case_id": case_id,
                "query": case.get("query", ""),
                "chunk_id": cid,
                "grade": grade,
                "reason_code": reason,
                "source_type": actual_source_type,
                "source_id": source_id,
                "content": content,
                "metadata_json": json.dumps(
                    metadata, ensure_ascii=False, default=str
                ),
                "provenance_json": json.dumps(
                    provenance, ensure_ascii=False, default=str
                ),
                "review_status": "NOT_REVIEWED",
                "human_grade": "",
                "review_notes": "",
            }
            all_rows.append(row)

            # Target the two anomalies identified so far.
            if (
                case_id == "EMB-001"
                and source_type == "process_measurement"
                and grade >= 2
            ) or (
                case_id == "EMB-002"
                and source_type == "process_measurement"
                and grade == 3
            ):
                anomaly_rows.append(row)

        print("  Grades:", dict(sorted(grade_counts.items())))
        print("  Sources:", dict(sorted(source_counts.items())))

    fields = [
        "case_id", "query", "chunk_id", "grade", "reason_code",
        "source_type", "source_id", "content", "metadata_json",
        "provenance_json", "review_status", "human_grade",
        "review_notes",
    ]

    all_path = OUTPUT_DIR / "label_audit_all.csv"
    anomaly_path = OUTPUT_DIR / "label_audit_anomalies.csv"

    for path, rows in (
        (all_path, all_rows),
        (anomaly_path, anomaly_rows),
    ):
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    print("\n=== AUDIT OUTPUTS ===")
    print("All labels:", all_path.relative_to(ROOT))
    print("Targeted anomalies:", anomaly_path.relative_to(ROOT))
    print("Total label rows:", len(all_rows))
    print("Targeted anomaly rows:", len(anomaly_rows))
    print("Unmatched label IDs:", len(unmatched))

    if unmatched:
        print("\nFirst unmatched IDs:")
        for item in unmatched[:10]:
            print(" ", item)

    if all_rows and not any(r["content"] for r in all_rows):
        print(
            "\nWARNING: No chunk content matched. "
            "Do not interpret the CSV until the ID mapping is fixed."
        )

    if any(not r["reason_code"] for r in all_rows):
        print(
            "\nNOTE: Some per-chunk reason codes were not found "
            "in the current JSON. We will determine whether they "
            "were never stored or use a different field name."
        )

    print("\nNo labels or vector indexes were modified.")


if __name__ == "__main__":
    main()
