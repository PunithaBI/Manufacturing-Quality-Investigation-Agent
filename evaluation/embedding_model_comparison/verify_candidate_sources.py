
import csv
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "evaluation/embedding_model_comparison/silver_label_evaluation_candidate/silver_evaluation_report.json"
CHUNKS = ROOT / "data/vector_index_candidate/chunks.json"
DB = ROOT / "data/Northwind_db/nordwind.db"
OUT = ROOT / "evaluation/embedding_model_comparison/silver_label_evaluation_candidate/source_verification.csv"

def json_text(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)

report = json.loads(REPORT.read_text(encoding="utf-8"))
chunks_list = json.loads(CHUNKS.read_text(encoding="utf-8"))
chunks = {x["chunk_id"]: x for x in chunks_list}

# Open the source database read-only.
conn = sqlite3.connect(DB.resolve().as_uri() + "?mode=ro", uri=True)
conn.row_factory = sqlite3.Row

# Known source table primary keys and human-readable source identifiers.
SOURCE_TABLES = {
    "ncr": ("ncrs", "ncr_number"),
    "8d": ("eight_d_reports", "report_number"),
    "rca": ("rca", None),
    "capa": ("capa", "capa_number"),
    "inspection": ("inspections", None),
    "process_measurement": ("process_measurements", None),
    "manufacturing_order": ("manufacturing_orders", "mo_number"),
    "operation": ("operations", None),
}

# Foreign-key-like relationships to check against actual rows.
RELATIONS = {
    "ncrs": {
        "serial_unit_id": "serial_units",
        "lot_id": "lots",
        "mo_id": "manufacturing_orders",
        "inspection_id": "inspections",
    },
    "eight_d_reports": {"ncr_id": "ncrs"},
    "rca": {"eight_d_id": "eight_d_reports"},
    "capa": {"eight_d_id": "eight_d_reports"},
    "inspections": {
        "serial_unit_id": "serial_units",
        "mo_id": "manufacturing_orders",
    },
    "process_measurements": {
        "operation_id": "operations",
        "serial_unit_id": "serial_units",
    },
    "manufacturing_orders": {"product_id": "products"},
    "operations": {"mo_id": "manufacturing_orders"},
}

def table_columns(table):
    return {
        row["name"]
        for row in conn.execute(f'PRAGMA table_info("{table}")')
    }

def fetch_source(table, record_id):
    columns = table_columns(table)
    if "id" not in columns:
        return None
    return conn.execute(
        f'SELECT * FROM "{table}" WHERE id = ?',
        (record_id,),
    ).fetchone()

def relationship_audit(table, row):
    checks = []
    for column, target_table in RELATIONS.get(table, {}).items():
        if column not in row.keys():
            continue
        value = row[column]
        if value is None:
            checks.append(f"{column}=NULL (not linked)")
            continue
        target_columns = table_columns(target_table)
        if "id" not in target_columns:
            checks.append(f"{column}={value}: target schema unclear")
            continue
        found = conn.execute(
            f'SELECT 1 FROM "{target_table}" WHERE id = ? LIMIT 1',
            (value,),
        ).fetchone()
        checks.append(
            f"{column}={value}: " + ("PASS" if found else "BROKEN LINK")
        )
    return "; ".join(checks)

fields = [
    "benchmark_id", "query", "method", "rank", "score",
    "silver_grade", "chunk_id", "source_type", "source_id",
    "provenance_table", "provenance_record_id",
    "chunk_exists", "source_row_exists", "source_id_matches",
    "relationship_checks", "indexed_content", "source_record_json",
    "content_review", "reviewer_notes",
]

output_rows = []
for method in report.get("methods", []):
    for case in method.get("case_results", []):
        for result in case.get("top_10", []):
            chunk_id = result.get("chunk_id", "")
            chunk = chunks.get(chunk_id)
            source_type = result.get("source_type", "")
            mapping = SOURCE_TABLES.get(source_type)
            source_row = None
            table = ""
            record_id = None
            id_matches = "NOT CHECKED"
            relation_checks = ""

            if chunk and mapping:
                table = chunk.get("provenance", {}).get("table", mapping[0])
                record_id = chunk.get("provenance", {}).get("record_id")
                if table in {item[0] for item in SOURCE_TABLES.values()}:
                    source_row = fetch_source(table, record_id)
                    if source_row:
                        identifier_column = mapping[1]
                        if identifier_column and identifier_column in source_row.keys():
                            id_matches = (
                                "PASS"
                                if str(source_row[identifier_column]) ==
                                   str(result.get("source_id"))
                                else "MISMATCH"
                            )
                        else:
                            id_matches = "PK-ONLY; CHECK SOURCE ID"
                        relation_checks = relationship_audit(table, source_row)

            output_rows.append({
                "benchmark_id": case.get("case_id", ""),
                "query": case.get("query", ""),
                "method": method.get("method", ""),
                "rank": result.get("rank", ""),
                "score": result.get("score", ""),
                "silver_grade": result.get("silver_grade", ""),
                "chunk_id": chunk_id,
                "source_type": source_type,
                "source_id": result.get("source_id", ""),
                "provenance_table": table,
                "provenance_record_id": record_id if record_id is not None else "",
                "chunk_exists": "YES" if chunk else "NO",
                "source_row_exists": "YES" if source_row else "NO",
                "source_id_matches": id_matches,
                "relationship_checks": relation_checks,
                "indexed_content": chunk.get("content", "") if chunk else "",
                "source_record_json": json_text(dict(source_row)) if source_row else "",
                "content_review": "PENDING MANUAL REVIEW",
                "reviewer_notes": "",
            })

conn.close()

OUT.parent.mkdir(parents=True, exist_ok=True)
with OUT.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(output_rows)

print("Audit complete")
print("Saved results checked:", len(output_rows))
print("Unique chunks:", len({r["chunk_id"] for r in output_rows}))
print("Output:", OUT)
print("Review source_row_exists, source_id_matches and relationship_checks first.")
print("A PASS on provenance does not prove that the retrieved evidence is relevant.")
