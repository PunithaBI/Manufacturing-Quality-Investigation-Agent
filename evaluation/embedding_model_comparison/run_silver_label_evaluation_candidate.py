from __future__ import annotations

"""
Candidate-only, no-download embedding evaluation.

Reads:
  data/vector_index_candidate/chunks.json
  data/Northwind_db/nordwind.db (read-only)
  existing candidate model vectors/manifests under
    data/embedding_experiments/single_query_comparison_8d_candidate/

Writes only to:
  evaluation/embedding_model_comparison/silver_label_evaluation_candidate/

This creates heuristic/relationship-derived SILVER labels, not human-validated
ground truth. It never reads data/vector_index and never downloads models.
"""

import json
import math
import re
import sqlite3
import time
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parents[2]
CORPUS_FILE = ROOT / "data" / "vector_index_candidate" / "chunks.json"
DB_FILE = ROOT / "data" / "Northwind_db" / "nordwind.db"
EXPERIMENT_ROOT = (
    ROOT / "data" / "embedding_experiments" / "single_query_comparison_8d_candidate"
)
OUT_DIR = ROOT / "evaluation" / "embedding_model_comparison" / "silver_label_evaluation_candidate"
TOP_KS = (5, 10)

CASES = [
    {
        "case_id": "EMB-001",
        "query": "Find historical manufacturing evidence related to dimensional non-conformance found during final inspection.",
        "kind": "dimensional_final_inspection",
    },
    {
        "case_id": "EMB-002",
        "query": "Find manufacturing evidence related to process measurements outside specification.",
        "kind": "process_out_of_spec",
    },
    {
        "case_id": "EMB-003",
        "query": "Find previous quality investigations involving root cause and corrective action for manufacturing problems.",
        "kind": "root_cause_capa",
    },
    {
        "case_id": "EMB-004",
        "query": "Find inspection evidence associated with dimensional quality problems.",
        "kind": "dimensional_inspection",
    },
    {
        "case_id": "EMB-005",
        "query": "Find historical NCR evidence that is similar to a dimensional non-conformance found during final inspection.",
        "kind": "historical_dimensional_ncr",
    },
]

# Deliberately excludes e5-base-v2.
MODELS = {
    "all-MiniLM-L6-v2": {
        "model_name": "sentence-transformers/all-MiniLM-L6-v2",
        "query_prefix": "",
    },
    "all-mpnet-base-v2": {
        "model_name": "sentence-transformers/all-mpnet-base-v2",
        "query_prefix": "",
    },
    "bge-small-en-v1.5": {
        "model_name": "BAAI/bge-small-en-v1.5",
        "query_prefix": "Represent this sentence for searching relevant passages: ",
    },
    "bge-base-en-v1.5": {
        "model_name": "BAAI/bge-base-en-v1.5",
        "query_prefix": "Represent this sentence for searching relevant passages: ",
    },
}

DIMENSION_TERMS = (
    "dimensional", "dimension", "diameter", "length", "width", "thickness",
    "tolerance", "size deviation", "out of tolerance",
)
FINAL_INSPECTION_TERMS = ("final inspection", "inspection", "inspector", "measured")
OUT_SPEC_TERMS = (
    "outside specification",
    "outside spec",
    "out of specification",
    "out of spec",
    "out of limit",
    "above limit",
    "below limit",
    "out of tolerance",
    "exceeded upper spec limit",
    "exceeded lower spec limit",
    "exceeded specification limit",
    "above upper spec limit",
    "below lower spec limit",
    "failed specification",
)
ROOT_CAUSE_TERMS = (
    "root cause", "cause", "contributing factor", "why-why", "5 why", "fishbone",
)
CAPA_TERMS = (
    "corrective action", "preventive action", "capa", "effectiveness check",
)
INSPECTION_SOURCE_TERMS = ("inspection", "inspect", "measurement", "processmeasurement")
NCR_SOURCE_TERMS = ("ncr", "nonconformance", "non-conformance")
EIGHT_D_SOURCE_TERMS = ("eight_d", "8d", "eightd")
RCA_SOURCE_TERMS = ("rca", "rootcause")
CAPA_SOURCE_TERMS = ("capa",)


def norm(value: Any) -> str:
    return str(value or "").strip().lower().replace("_", " ").replace("-", " ")


def contains_any(text: str, terms: tuple[str, ...]) -> bool:
    text = norm(text)
    return any(norm(term) in text for term in terms)


def load_chunks() -> list[dict[str, Any]]:
    if not CORPUS_FILE.exists():
        raise FileNotFoundError(f"Candidate corpus not found: {CORPUS_FILE}")
    chunks = json.loads(CORPUS_FILE.read_text(encoding="utf-8-sig"))
    if not isinstance(chunks, list) or not chunks:
        raise ValueError("Candidate chunks.json must contain a non-empty list.")
    required = ("chunk_id", "source_id", "source_type", "content")
    for i, chunk in enumerate(chunks):
        missing = [key for key in required if not chunk.get(key)]
        if missing:
            raise ValueError(f"Candidate chunk {i} missing fields: {missing}")
    ids = [c["chunk_id"] for c in chunks]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate chunk_id values found in candidate corpus.")
    return chunks


def chunk_text(chunk: dict[str, Any]) -> str:
    metadata = chunk.get("metadata") or {}
    return "\n".join(
        str(v) for v in (
            chunk.get("source_type", ""),
            chunk.get("source_id", ""),
            chunk.get("title", ""),
            metadata.get("section", ""),
            chunk.get("content", ""),
        ) if v is not None
    )


def readonly_db_connection() -> sqlite3.Connection | None:
    if not DB_FILE.exists():
        print(f"WARNING: database not found at {DB_FILE}; labels will use text/source rules only.")
        return None
    uri = DB_FILE.resolve().as_uri() + "?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as exc:
        print(f"WARNING: could not open database read-only ({type(exc).__name__}: {exc}); using text/source rules only.")
        return None


def table_rows(conn: sqlite3.Connection, table: str) -> list[dict[str, Any]]:
    try:
        # Table names come only from sqlite_master and are quoted defensively.
        escaped = table.replace('"', '""')
        return [dict(row) for row in conn.execute(f'SELECT * FROM "{escaped}"').fetchall()]
    except sqlite3.Error:
        return []


def build_record_links(
    conn: sqlite3.Connection | None,
) -> dict[tuple[str, str], set[str]]:
    """
    Map (provenance table, record_id) to related NCR numbers.

    Verified paths:
      NCR -> 8D -> RCA/CAPA
      NCR -> inspection
      NCR -> process measurement through shared serial unit

    A shared serial unit is contextual evidence, not proof of causation.
    """
    links: dict[tuple[str, str], set[str]] = {}
    if conn is None:
        return links

    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    rows_by_table = {t: table_rows(conn, t) for t in tables}

    ncr_rows = rows_by_table.get("ncrs", [])
    ncr_number_by_pk: dict[str, str] = {}
    ncrs_by_serial: dict[str, set[str]] = {}
    ncrs_by_inspection: dict[str, set[str]] = {}

    for row in ncr_rows:
        pk = str(row.get("id", ""))
        number = str(row.get("ncr_number", "") or "")
        if not pk or not number:
            continue

        ncr_number_by_pk[pk] = number
        links.setdefault(("ncrs", pk), set()).add(number)

        serial_id = row.get("serial_unit_id")
        if serial_id is not None:
            ncrs_by_serial.setdefault(str(serial_id), set()).add(number)

        inspection_id = row.get("inspection_id")
        if inspection_id is not None:
            ncrs_by_inspection.setdefault(
                str(inspection_id), set()
            ).add(number)

    # Direct inspection -> NCR relationships.
    for inspection_id, numbers in ncrs_by_inspection.items():
        links.setdefault(("inspections", inspection_id), set()).update(numbers)

    # NCR -> 8D relationships.
    ncrs_by_8d: dict[str, set[str]] = {}
    for row in rows_by_table.get("eight_d_reports", []):
        eight_d_id = str(row.get("id", ""))
        ncr_id = str(row.get("ncr_id", "") or "")
        number = ncr_number_by_pk.get(ncr_id)

        if eight_d_id and number:
            ncrs_by_8d.setdefault(eight_d_id, set()).add(number)
            links.setdefault(
                ("eight_d_reports", eight_d_id), set()
            ).add(number)

    # RCA/CAPA -> 8D -> NCR relationships.
    for table in ("rca", "capa"):
        for row in rows_by_table.get(table, []):
            record_id = row.get("id")
            eight_d_id = row.get("eight_d_id")
            if record_id is None or eight_d_id is None:
                continue

            related = ncrs_by_8d.get(str(eight_d_id), set())
            if related:
                links.setdefault(
                    (table, str(record_id)), set()
                ).update(related)

    # Other explicit foreign-key relationships, where present.
    for table, rows in rows_by_table.items():
        for row in rows:
            record_id = row.get("id")
            if record_id is None:
                continue

            key = (table.lower(), str(record_id))
            related = links.setdefault(key, set())

            raw_ncr_id = row.get("ncr_id")
            if raw_ncr_id is not None:
                number = ncr_number_by_pk.get(str(raw_ncr_id))
                if number:
                    related.add(number)

            raw_eight_d_id = row.get("eight_d_id")
            if raw_eight_d_id is not None:
                related.update(ncrs_by_8d.get(str(raw_eight_d_id), set()))

            raw_number = row.get("ncr_number")
            if raw_number:
                number = str(raw_number)
                if number in ncr_number_by_pk.values():
                    related.add(number)

            if not related:
                links.pop(key, None)

    # Measurements share a serial unit with an NCR. This is a contextual
    # relationship only; the grading rules below do not treat it as proof
    # that the measurement caused the NCR.
    for row in rows_by_table.get("process_measurements", []):
        record_id = row.get("id")
        serial_id = row.get("serial_unit_id")
        if record_id is None or serial_id is None:
            continue

        related = ncrs_by_serial.get(str(serial_id), set())
        if related:
            links.setdefault(
                ("process_measurements", str(record_id)), set()
            ).update(related)

    return links


def related_ncrs_for_chunk(
    chunk: dict[str, Any],
    links: dict[tuple[str, str], set[str]],
) -> set[str]:
    provenance = chunk.get("provenance") or {}
    table = str(provenance.get("table", "")).lower()
    record_id = str(provenance.get("record_id", ""))

    result = set(links.get((table, record_id), set()))

    source_id = str(chunk.get("source_id", ""))
    if source_id.upper().startswith("NCR-"):
        result.add(source_id)

    return result


def _provenance_table(chunk: dict[str, Any]) -> str:
    return str(
        (chunk.get("provenance") or {}).get("table", "")
    ).lower()


def _is_process_measurement(chunk: dict[str, Any]) -> bool:
    return (
        _provenance_table(chunk) == "process_measurements"
        or norm(chunk.get("source_type", "")) == "process measurement"
    )


def _measurement_out_of_spec(text: str) -> bool | None:
    """
    Return True/False for structured measurement status, or None if unknown.

    Prefer an explicit In Spec field. Otherwise compare actual value with
    available numeric limits. Does not infer a breach from generic wording.
    """
    in_spec_match = re.search(
        r"^\s*In\s+Spec\s*:\s*(true|false|1|0|yes|no)\s*$",
        text,
        re.IGNORECASE | re.MULTILINE,
    )

    if in_spec_match:
        value = in_spec_match.group(1).lower()
        return value in ("false", "0", "no")

    def read_number(field: str) -> float | None:
        match = re.search(
            rf"^\s*{field}\s*:\s*(-?\d+(?:\.\d+)?)\s*$",
            text,
            re.IGNORECASE | re.MULTILINE,
        )
        return float(match.group(1)) if match else None

    actual = read_number("Actual Value")
    lower = read_number("Lsl")
    upper = read_number("Usl")

    if actual is None or (lower is None and upper is None):
        return None

    if lower is not None and actual < lower:
        return True
    if upper is not None and actual > upper:
        return True

    return False

def _measurement_is_dimensional(text: str) -> bool:
    """Check the measurement's parameter name, not just its NCR link."""
    match = re.search(
        r"^\s*Parameter Name\s*:\s*(.*?)\s*$",
        text,
        re.IGNORECASE | re.MULTILINE,
    )
    if not match:
        return False

    parameter = norm(match.group(1))

    dimensional_terms = (
        "diameter", "bore", "length", "width", "thickness",
        "depth", "radius", "circumference", "flatness",
        "roundness", "cylindricity", "concentricity",
        "runout", "straightness", "perpendicularity",
        "parallelism", "position", "profile", "taper",
        "dimension", "size",
    )

    return any(
        re.search(rf"\b{re.escape(term)}\b", parameter)
        for term in dimensional_terms
    )


def _explicit_out_of_spec(text: str) -> bool:
    return contains_any(text, OUT_SPEC_TERMS)


def _has_substantive_field(text: str, field_names: tuple[str, ...]) -> bool:
    """
    Detect a real field value rather than 'Pending RCA', 'See linked CAPA',
    or other placeholder text.
    """
    placeholders = (
        "pending",
        "see linked",
        "not determined",
        "unknown",
        "not available",
        "n/a",
        "none",
        "tbd",
        "to be determined",
    )

    for field in field_names:
        match = re.search(
            rf"^\s*{re.escape(field)}\s*:\s*(.*?)\s*$",
            text,
            re.IGNORECASE | re.MULTILINE,
        )
        if not match:
            continue

        value = match.group(1).strip()
        value_norm = norm(value)

        if not value or any(
            value_norm == p or value_norm.startswith(p + " ")
            for p in placeholders
        ):
            continue

        return True

    return False


def grade_chunk(
    chunk: dict[str, Any],
    case_kind: str,
    related_ncrs: set[str],
    matching_ncrs: set[str],
) -> tuple[int, str]:
    text = chunk_text(chunk)
    family = source_family(chunk)
    table = _provenance_table(chunk)

    dimension = contains_any(text, DIMENSION_TERMS)
    final_inspection = contains_any(text, FINAL_INSPECTION_TERMS)
    linked_match = bool(related_ncrs & matching_ncrs)

    is_measurement = _is_process_measurement(chunk)
    measurement_status = (
        _measurement_out_of_spec(text) if is_measurement else None
    )
    explicit_breach = _explicit_out_of_spec(text)

    inspection_failed = (
        table == "inspections"
        and contains_any(text, ("result: fail", "result: failed"))
    )
    inspection_final = (
        table == "inspections"
        and contains_any(text, ("inspection type: final",))
    )

    has_root_cause = _has_substantive_field(
        text,
        ("Root cause", "Root cause description"),
    )
    has_corrective_action = _has_substantive_field(
        text,
        ("Corrective action",),
    )
    has_preventive_action = _has_substantive_field(
        text,
        ("Preventive action",),
    )
    has_substantive_rca_or_capa = (
        has_root_cause
        or has_corrective_action
        or has_preventive_action
    )

    if case_kind == "dimensional_final_inspection":
        if family == "ncr" and dimension and final_inspection:
            description_match = re.search(
                r"^\s*NCR description\s*:\s*(.*?)\s*$",
                text,
                re.IGNORECASE | re.MULTILINE,
            )
            description = (
                norm(description_match.group(1)).rstrip(". ")
                if description_match
                else ""
            )

            generic_description = (
                "dimensional non-conformance found on final inspection"
            )

            if description == generic_description:
                return 2, "generic_dimensional_final_inspection_ncr"

            return 3, "specific_dimensional_final_inspection_ncr"

        if table == "inspections" and linked_match and inspection_final:
            if inspection_failed:
                return 3, "directly_linked_failed_final_inspection"
            return 2, "directly_linked_final_inspection"

        if (
            table == "process_measurements"
            and is_measurement
            and _measurement_is_dimensional(text)
            and measurement_status is True
            and linked_match
        ):
            return 2, "linked_out_of_spec_dimensional_measurement"

        if (
            table == "inspections"
            and linked_match
            and inspection_failed
            and dimension
        ):
            return 3, "linked_failed_dimensional_inspection"

        if family == "eight_d" and linked_match and dimension:
            return 2, "linked_8d_dimensional_problem"

        if family in ("rca", "capa") and linked_match and dimension:
            return 2, "linked_rca_capa_dimensional_context"

        if family == "ncr" and dimension:
            return 2, "historical_dimensional_ncr_without_final_inspection"

    elif case_kind == "historical_dimensional_ncr":
        # This query asks for similar historical NCRs, so NCR records are
        # primary. Other record types provide context, not equivalent matches.
        if family == "ncr" and dimension and final_inspection:
            return 3, "similar_historical_dimensional_final_inspection_ncr"

        if family == "ncr" and dimension:
            return 2, "historical_dimensional_ncr"

        if family == "eight_d" and linked_match and dimension:
            return 1, "linked_8d_for_similar_historical_ncr"

        if family in ("rca", "capa") and linked_match:
            return 1, "linked_investigation_context_for_historical_ncr"

   
    elif case_kind == "dimensional_inspection":
        if table == "inspections" and linked_match and inspection_failed:
            return 3, "failed_inspection_directly_linked_to_dimensional_ncr"

        if table == "inspections" and linked_match and inspection_final:
            return 2, "final_inspection_linked_to_dimensional_ncr"

        if (
            table == "process_measurements"
            and is_measurement
            and _measurement_is_dimensional(text)
            and linked_match
        ):
            if measurement_status is True:
                return 2, "linked_out_of_spec_dimensional_measurement"

            return 1, "contextual_linked_dimensional_measurement"

        if family == "ncr" and dimension and final_inspection:
            return 2, "ncr_describes_dimensional_inspection_problem"

        if family == "eight_d" and linked_match and dimension:
            return 2, "linked_8d_dimensional_problem"

        if family in ("rca", "capa") and linked_match and dimension:
            return 1, "linked_rca_capa_dimensional_context"

    elif case_kind == "process_out_of_spec":
        if is_measurement:
            if measurement_status is True:
                return 3, "structured_measurement_confirmed_out_of_spec"

            if measurement_status is False:
                # Explicitly in-spec measurements are not positive evidence
                # for a query asking for out-of-spec measurements.
                return 0, "structured_measurement_confirmed_in_spec"

            if explicit_breach:
                return 3, "measurement_text_explicitly_reports_spec_breach"

            return 0, "measurement_breach_not_established"

        if explicit_breach and family in ("ncr", "eight_d", "rca", "capa"):
            return 2, "quality_record_explicitly_reports_spec_breach"

        if linked_match and explicit_breach:
            return 1, "linked_record_with_explicit_spec_breach"

    elif case_kind == "root_cause_capa":
        if family == "rca" and has_root_cause:
            return 3, "substantive_root_cause_finding"

        if family == "capa" and (
            has_corrective_action or has_preventive_action
        ):
            return 3, "substantive_corrective_or_preventive_action"

        if family == "eight_d" and has_substantive_rca_or_capa:
            return 2, "8d_contains_substantive_investigation_or_action"

        if family == "eight_d" and linked_match:
            return 1, "8d_linked_to_investigation_case"

        if family == "ncr" and linked_match:
            return 1, "ncr_linked_to_investigation"

    return 0, "not_identified_by_silver_rules"


def build_silver_labels(
    chunks: list[dict[str, Any]],
    links: dict[tuple[str, str], set[str]],
) -> tuple[dict[str, dict[str, int]], dict[str, Any]]:
    ncr_text_by_number: dict[str, str] = {}

    for chunk in chunks:
        if source_family(chunk) == "ncr":
            number = str(chunk.get("source_id", ""))
            ncr_text_by_number[number] = (
                ncr_text_by_number.get(number, "") + "\n" + chunk_text(chunk)
            )

    matching_ncrs_by_case: dict[str, set[str]] = {}
    case_grades: dict[str, dict[str, int]] = {}
    case_reasons: dict[str, dict[str, int]] = {}

    for case in CASES:
        kind = case["kind"]
        matches: set[str] = set()

        if kind in (
            "dimensional_final_inspection",
            "historical_dimensional_ncr",
        ):
            for number, text in ncr_text_by_number.items():
                if (
                    contains_any(text, DIMENSION_TERMS)
                    and contains_any(text, ("final inspection",))
                ):
                    matches.add(number)

        elif kind == "dimensional_inspection":
            for number, text in ncr_text_by_number.items():
                if contains_any(text, DIMENSION_TERMS):
                    matches.add(number)

        elif kind == "root_cause_capa":
            # Identify NCRs connected to RCA/CAPA records through verified
            # foreign-key relationships. This is for contextual linking;
            # substantive RCA/CAPA records can independently match the query.
            for chunk in chunks:
                if source_family(chunk) in ("rca", "capa"):
                    matches.update(related_ncrs_for_chunk(chunk, links))

        elif kind == "process_out_of_spec":
            for chunk in chunks:
                text = chunk_text(chunk)
                structured_breach = (
                    _is_process_measurement(chunk)
                    and _measurement_out_of_spec(text) is True
                )
                if structured_breach or _explicit_out_of_spec(text):
                    matches.update(related_ncrs_for_chunk(chunk, links))

        grades: dict[str, int] = {}
        reasons: Counter[str] = Counter()

        for chunk in chunks:
            related = related_ncrs_for_chunk(chunk, links)
            grade, reason = grade_chunk(chunk, kind, related, matches)

            if grade > 0:
                grades[chunk["chunk_id"]] = grade
                reasons[reason] += 1

        matching_ncrs_by_case[case["case_id"]] = matches
        case_grades[case["case_id"]] = grades
        case_reasons[case["case_id"]] = dict(reasons)

    labels = case_grades

    summary = {
        "label_type": "automatic_silver_labels",
        "human_review_performed": False,
        "rules": {
            "grade_3": (
                "Direct query evidence; verified failed inspection; "
                "confirmed out-of-spec measurement; or substantive RCA/CAPA"
            ),
            "grade_2": (
                "Strong supporting evidence with query-relevant content "
                "or a verified relationship"
            ),
            "grade_1": (
                "Contextual evidence with a relevant relationship"
            ),
            "grade_0": (
                "Not identified as relevant by these rules; "
                "not proof of irrelevance"
            ),
        },
        "case_summary": [
            {
                "case_id": case["case_id"],
                "query": case["query"],
                "silver_relevant_chunk_count_grade_1_plus": sum(
                    1 for grade in labels[case["case_id"]].values()
                    if grade >= 1
                ),
                "silver_relevant_chunk_count_grade_2_plus": sum(
                    1 for grade in labels[case["case_id"]].values()
                    if grade >= 2
                ),
                "silver_relevant_chunk_count_grade_3": sum(
                    1 for grade in labels[case["case_id"]].values()
                    if grade >= 3
                ),
                "matching_ncr_count": len(
                    matching_ncrs_by_case[case["case_id"]]
                ),
                "label_reason_counts": case_reasons[case["case_id"]],
                "matching_ncr_examples": sorted(
                    matching_ncrs_by_case[case["case_id"]]
                )[:20],
            }
            for case in CASES
        ],
    }

    return labels, summary



def source_family(chunk: dict[str, Any]) -> str:
    st = norm(chunk.get("source_type", ""))
    table = norm((chunk.get("provenance") or {}).get("table", ""))
    value = f"{st} {table}"
    if contains_any(value, NCR_SOURCE_TERMS):
        return "ncr"
    if contains_any(value, EIGHT_D_SOURCE_TERMS):
        return "eight_d"
    if contains_any(value, RCA_SOURCE_TERMS):
        return "rca"
    if contains_any(value, CAPA_SOURCE_TERMS):
        return "capa"
    if contains_any(value, INSPECTION_SOURCE_TERMS):
        return "inspection_or_measurement"
    return "other"






def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def tfidf_rank(chunks: list[dict[str, Any]], query: str, top_k: int) -> list[dict[str, Any]]:
    docs = [tokenize(chunk_text(chunk)) for chunk in chunks]
    df: Counter[str] = Counter()
    for tokens in docs:
        df.update(set(tokens))
    n = len(docs)
    idf = {token: math.log((n + 1) / (freq + 1)) + 1.0 for token, freq in df.items()}

    def vector(tokens: list[str]) -> dict[str, float]:
        counts = Counter(tokens)
        return {
            token: (1.0 + math.log(count)) * idf[token]
            for token, count in counts.items() if token in idf
        }

    doc_vectors = [vector(tokens) for tokens in docs]
    norms = [math.sqrt(sum(v * v for v in vec.values())) for vec in doc_vectors]
    qvec = vector(tokenize(query))
    qnorm = math.sqrt(sum(v * v for v in qvec.values()))
    scores = []
    for vec, dnorm in zip(doc_vectors, norms):
        dot = sum(weight * vec.get(token, 0.0) for token, weight in qvec.items())
        scores.append(dot / (qnorm * dnorm) if qnorm and dnorm else 0.0)
    order = sorted(range(n), key=lambda i: (-scores[i], i))[:top_k]
    return [{"chunk_id": chunks[i]["chunk_id"], "score": float(scores[i])} for i in order]


def precision_at_k(ranked_ids: list[str], relevant: set[str], k: int) -> float:
    return sum(1 for item in ranked_ids[:k] if item in relevant) / k if k else 0.0


def recall_at_k(ranked_ids: list[str], relevant: set[str], k: int) -> float:
    return sum(1 for item in ranked_ids[:k] if item in relevant) / len(relevant) if relevant else 0.0


def mrr(ranked_ids: list[str], relevant: set[str]) -> float:
    for rank, item in enumerate(ranked_ids, 1):
        if item in relevant:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(ranked_ids: list[str], grades: dict[str, int], k: int) -> float:
    def dcg(ids: list[str]) -> float:
        return sum(((2 ** grades.get(cid, 0)) - 1) / math.log2(rank + 1) for rank, cid in enumerate(ids[:k], 1))
    actual = dcg(ranked_ids)
    ideal_grades = sorted(grades.values(), reverse=True)[:k]
    ideal = sum(((2 ** grade) - 1) / math.log2(rank + 1) for rank, grade in enumerate(ideal_grades, 1))
    return actual / ideal if ideal else 0.0


def load_candidate_vectors(model_key: str, corpus: list[dict[str, Any]]) -> np.ndarray:
    model_dir = EXPERIMENT_ROOT / model_key
    vector_file = model_dir / "vectors.npy"
    manifest_file = model_dir / "index_manifest.json"
    if not vector_file.exists() or not manifest_file.exists():
        raise FileNotFoundError(
            f"Existing candidate vectors/manifest missing for {model_key}; refusing to rebuild/download. "
            f"Expected {vector_file} and {manifest_file}"
        )
    manifest = json.loads(manifest_file.read_text(encoding="utf-8-sig"))
    manifest_ids = [item.get("chunk_id") for item in manifest.get("items", [])]
    corpus_ids = [chunk["chunk_id"] for chunk in corpus]
    if manifest_ids != corpus_ids:
        raise ValueError(f"{model_key}: candidate index manifest chunk order does not match candidate corpus.")
    vectors = np.load(vector_file, mmap_mode="r")
    if vectors.ndim != 2 or vectors.shape[0] != len(corpus):
        raise ValueError(f"{model_key}: vector shape {vectors.shape} does not match {len(corpus)} candidate chunks.")
    return np.asarray(vectors, dtype=np.float32)


def run_model(
    model_key: str,
    config: dict[str, str],
    chunks: list[dict[str, Any]],
    cases: list[dict[str, str]],
    labels: dict[str, dict[str, int]],
) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        vectors = load_candidate_vectors(model_key, chunks)
        # local_files_only=True guarantees no model download is attempted.
        model = SentenceTransformer(config["model_name"], local_files_only=True)
        case_results = []
        for case in cases:
            q = config["query_prefix"] + case["query"]
            qvec = np.asarray(
                model.encode(q, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False),
                dtype=np.float32,
            ).reshape(-1)
            if qvec.shape[0] != vectors.shape[1]:
                raise ValueError(
                    f"Query vector dimension {qvec.shape[0]} != candidate index dimension {vectors.shape[1]}"
                )
            scores = np.asarray(vectors @ qvec)
            order = np.argsort(-scores, kind="stable")[:10]
            ranked_chunks = [chunks[int(i)] for i in order]
            ranked_ids = [chunk["chunk_id"] for chunk in ranked_chunks]
            grade_map = labels[case["case_id"]]
            relevant = {cid for cid, grade in grade_map.items() if grade >= 2}
            metrics = {
                "precision_at_5": round(precision_at_k(ranked_ids, relevant, 5), 4),
                "precision_at_10": round(precision_at_k(ranked_ids, relevant, 10), 4),
                "recall_at_5": round(recall_at_k(ranked_ids, relevant, 5), 4),
                "recall_at_10": round(recall_at_k(ranked_ids, relevant, 10), 4),
                "mrr": round(mrr(ranked_ids, relevant), 4),
                "ndcg_at_10_graded": round(ndcg_at_k(ranked_ids, grade_map, 10), 4),
                "silver_relevant_chunks_grade_2_plus": len(relevant),
            }
            case_results.append({
                "case_id": case["case_id"],
                "query": case["query"],
                "metrics": metrics,
                "top_10": [
                    {
                        "rank": rank,
                        "chunk_id": chunk["chunk_id"],
                        "source_id": chunk["source_id"],
                        "source_type": chunk["source_type"],
                        "title": chunk.get("title"),
                        "content": chunk.get("content", ""),
                        "silver_grade": grade_map.get(chunk["chunk_id"], 0),
                        "silver_label_reason": "rule_based_label" if grade_map.get(chunk["chunk_id"], 0) else "not_identified_by_silver_rules",
                        "score": round(float(scores[int(order[rank - 1])]), 8),
                    }
                    for rank, chunk in enumerate(ranked_chunks, 1)
                ],
            })
        return {
            "method": model_key,
            "status": "success",
            "index_path": str((EXPERIMENT_ROOT / model_key).relative_to(ROOT)),
            "query_count": len(case_results),
            "case_results": case_results,
            "macro_average": {
                key: round(sum(item["metrics"][key] for item in case_results) / len(case_results), 4)
                for key in case_results[0]["metrics"]
                if key != "silver_relevant_chunks_grade_2_plus"
            },
            "runtime_seconds": round(time.perf_counter() - started, 3),
        }
    except Exception as exc:
        return {
            "method": model_key,
            "status": "failed",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "runtime_seconds": round(time.perf_counter() - started, 3),
        }


def run_tfidf(
    chunks: list[dict[str, Any]],
    cases: list[dict[str, str]],
    labels: dict[str, dict[str, int]],
) -> dict[str, Any]:
    started = time.perf_counter()
    case_results = []
    for case in cases:
        ranked = tfidf_rank(chunks, case["query"], 10)
        ranked_ids = [item["chunk_id"] for item in ranked]
        grade_map = labels[case["case_id"]]
        relevant = {cid for cid, grade in grade_map.items() if grade >= 2}
        metrics = {
            "precision_at_5": round(precision_at_k(ranked_ids, relevant, 5), 4),
            "precision_at_10": round(precision_at_k(ranked_ids, relevant, 10), 4),
            "recall_at_5": round(recall_at_k(ranked_ids, relevant, 5), 4),
            "recall_at_10": round(recall_at_k(ranked_ids, relevant, 10), 4),
            "mrr": round(mrr(ranked_ids, relevant), 4),
            "ndcg_at_10_graded": round(ndcg_at_k(ranked_ids, grade_map, 10), 4),
            "silver_relevant_chunks_grade_2_plus": len(relevant),
        }
        chunk_by_id = {chunk["chunk_id"]: chunk for chunk in chunks}
        case_results.append({
            "case_id": case["case_id"],
            "query": case["query"],
            "metrics": metrics,
            "top_10": [
                {
                    "rank": rank,
                    "chunk_id": item["chunk_id"],
                    "source_id": chunk_by_id[item["chunk_id"]]["source_id"],
                    "source_type": chunk_by_id[item["chunk_id"]]["source_type"],
                    "title": chunk_by_id[item["chunk_id"]].get("title"),
                    "content": chunk_by_id[item["chunk_id"]].get("content", ""),
                    "silver_grade": grade_map.get(item["chunk_id"], 0),
                    "silver_label_reason": "rule_based_label" if grade_map.get(item["chunk_id"], 0) else "not_identified_by_silver_rules",
                    "score": round(item["score"], 8),
                }
                for rank, item in enumerate(ranked, 1)
            ],
        })
    return {
        "method": "keyword_tfidf_baseline",
        "status": "success",
        "description": "Local TF-IDF cosine baseline; not BM25 and uses no embedding model.",
        "query_count": len(case_results),
        "case_results": case_results,
        "macro_average": {
            key: round(sum(item["metrics"][key] for item in case_results) / len(case_results), 4)
            for key in case_results[0]["metrics"]
            if key != "silver_relevant_chunks_grade_2_plus"
        },
        "runtime_seconds": round(time.perf_counter() - started, 3),
    }


def main() -> None:
    started = time.perf_counter()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    chunks = load_chunks()
    source_counts = Counter(str(chunk.get("source_type", "")) for chunk in chunks)
    print(f"Candidate corpus loaded: {len(chunks)} chunks")
    print("Source types:", dict(source_counts))
    print("Production index read or modified: NO")

    conn = readonly_db_connection()
    try:
        links = build_record_links(conn)
    finally:
        if conn is not None:
            conn.close()

    labels, label_summary = build_silver_labels(chunks, links)
    label_summary["corpus"] = {
        "path": str(CORPUS_FILE.relative_to(ROOT)),
        "chunk_count": len(chunks),
        "source_type_counts": dict(source_counts),
    }
    label_summary["database_relationships"] = {
        "database_path": str(DB_FILE.relative_to(ROOT)),
        "opened_read_only": DB_FILE.exists(),
        "record_link_count": len(links),
        "note": "Only identifiable foreign-key paths were used; records without resolvable links rely on source/text rules.",
    }
    label_summary["limitations"] = [
        "Labels are generated by deterministic rules and database links, not human review.",
        "Grade 0 means the rules did not identify relevance; it does not prove irrelevance.",
        "The database relationship map covers known NCR -> 8D -> RCA/CAPA paths and direct foreign keys; not every possible manufacturing relationship.",
        "Text matching can miss synonyms and can assign relevance to generic or repeated wording.",
        "Metrics are exploratory silver-label metrics, not validated retrieval accuracy.",
        "The same corpus and labeling rules are used for all methods, but labels may favor the fields and terminology encoded in those rules.",
        "Results are limited to five benchmark queries and the current candidate corpus.",
        "Raw similarity scores from different methods are not comparable.",
    ]

    labels_payload = {
        "label_type": "automatic_silver_labels",
        "grades": "0=not identified, 1=weak, 2=relevant support, 3=directly relevant",
        "cases": {
            case["case_id"]: {
                "query": case["query"],
                "chunk_grades": labels[case["case_id"]],
            }
            for case in CASES
        },
        "summary": label_summary,
    }
    labels_file = OUT_DIR / "silver_labels.json"
    labels_file.write_text(json.dumps(labels_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\nSilver-label counts (grade >= 2):")
    for row in label_summary["case_summary"]:
        print(
            f"  {row['case_id']}: relevant={row['silver_relevant_chunk_count_grade_2_plus']}, "
            f"weak_or_better={row['silver_relevant_chunk_count_grade_1_plus']}, "
            f"matching_NCRs={row['matching_ncr_count']}"
        )

    results = [run_tfidf(chunks, CASES, labels)]
    print("\nCompleted keyword TF-IDF baseline.")
    for model_key, config in MODELS.items():
        print(f"Evaluating {model_key} from existing local candidate artifacts (no download)...")
        result = run_model(model_key, config, chunks, CASES, labels)
        results.append(result)
        if result["status"] == "success":
            print(f"  completed; macro nDCG@10={result['macro_average']['ndcg_at_10_graded']}")
        else:
            print(f"  unavailable/failed: {result.get('error_type')}: {result.get('error')}")

    report = {
        "experiment": "five_query_candidate_embedding_comparison_with_silver_labels",
        "corpus": {
            "path": str(CORPUS_FILE.relative_to(ROOT)),
            "chunk_count": len(chunks),
        },
        "database": {
            "path": str(DB_FILE.relative_to(ROOT)),
            "read_only": True,
        },
        "queries": [{"case_id": c["case_id"], "query": c["query"]} for c in CASES],
        "top_k": 10,
        "relevance_policy": {
            "silver_labels": True,
            "grade_0_is_not_proven_irrelevant": True,
            "binary_metrics_relevant_threshold": "silver grade >= 2",
            "ndcg_uses_graded_relevance": True,
        },
        "methods": results,
        "silver_label_summary": label_summary,
        "safety": {
            "production_index_read_or_modified": False,
            "candidate_index_modified": False,
            "model_downloads_attempted": False,
            "e5_base_v2_included": False,
        },
        "total_runtime_seconds": round(time.perf_counter() - started, 3),
    }
    report_file = OUT_DIR / "silver_evaluation_report.json"
    report_file.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n=== COMPACT AGGREGATE RESULTS ===")
    for result in results:
        if result.get("status") != "success":
            print(f"{result['method']}: FAILED/UNAVAILABLE")
            continue
        m = result["macro_average"]
        print(
            f"{result['method']}: "
            f"P@10={m['precision_at_10']:.4f}, "
            f"R@10={m['recall_at_10']:.4f}, "
            f"MRR={m['mrr']:.4f}, "
            f"graded-nDCG@10={m['ndcg_at_10_graded']:.4f}"
        )

    print("\nOutput files:")
    print(f"  Labels: {labels_file.relative_to(ROOT)}")
    print(f"  Report: {report_file.relative_to(ROOT)}")
    print("Production index read or modified: NO")
    print("Model downloads attempted: NO")
    print("Note: results are exploratory silver-label metrics, not human-validated ground truth.")


if __name__ == "__main__":
    main()
