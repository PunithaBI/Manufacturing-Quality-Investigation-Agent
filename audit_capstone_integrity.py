
from pathlib import Path
import json
import sqlite3
import struct

ROOT = Path(__file__).resolve().parent
DB = ROOT / "data" / "Northwind_db" / "nordwind.db"
INDEX_DIRS = [
    ROOT / "data" / "vector_index",
    ROOT / "data" / "vector_index_candidate",
]
CODE_DIRS = [
    ROOT / "app" / "retrieval",
    ROOT / "app" / "agents",
    ROOT / "app" / "tools",
]

def section(title):
    print(f"\n{'=' * 18} {title} {'=' * 18}")

def load_chunks(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("chunks", "documents", "items", "data"):
                if isinstance(data.get(key), list):
                    return data[key]
        print("  Unrecognized JSON structure:", type(data).__name__)
        if isinstance(data, dict):
            print("  Top-level keys:", list(data)[:15])
        return []
    except Exception as exc:
        print("  Cannot read chunks:", repr(exc))
        return []

def inspect_index(folder):
    section(f"INDEX: {folder.relative_to(ROOT)}")
    chunks_file = folder / "chunks.json"
    vectors_file = folder / "vectors.npy"

    if not folder.exists():
        print("  DIRECTORY MISSING")
        return

    print("  chunks.json exists:", chunks_file.exists())
    print("  vectors.npy exists:", vectors_file.exists())

    if not chunks_file.exists():
        return

    chunks = load_chunks(chunks_file)
    print("  Chunk count:", len(chunks))

    if chunks:
        print("  First chunk fields:", list(chunks[0])[:20]
              if isinstance(chunks[0], dict) else type(chunks[0]).__name__)

        def field(item, *names):
            if not isinstance(item, dict):
                return None
            for name in names:
                if item.get(name) is not None:
                    return item[name]
            return None

        counts = {}
        for item in chunks:
            source_type = field(item, "source_type", "document_type", "type")
            source_type = str(source_type or "(missing)")
            counts[source_type] = counts.get(source_type, 0) + 1

        print("  Counts by source type:")
        for name, count in sorted(counts.items()):
            print(f"    {name}: {count}")

        for target in ("8D-20260012", "RCA-20260012", "CAPA-20260012"):
            matches = []
            for item in chunks:
                text = json.dumps(item, ensure_ascii=False).lower()
                if target.lower() in text:
                    matches.append(item)
            print(f"  References to {target}: {len(matches)} chunk(s)")
            for item in matches[:2]:
                print("    ", json.dumps(item, ensure_ascii=False)[:450])

    if vectors_file.exists():
        try:
            with vectors_file.open("rb") as f:
                header = f.read(128)
            if header[:6] == b"\x93NUMPY":
                major, minor = header[6], header[7]
                if major == 1:
                    header_len = struct.unpack("<H", header[8:10])[0]
                    start = 10
                else:
                    header_len = struct.unpack("<I", header[8:12])[0]
                    start = 12
                meta = header[start:start + header_len].decode(
                    "latin1", errors="replace"
                )
                print("  Vector array header:", meta.strip())
            else:
                print("  Unrecognized vectors.npy header")
        except Exception as exc:
            print("  Vector header error:", repr(exc))

def inspect_database():
    section("DATABASE")
    if not DB.exists():
        print("  DATABASE FILE MISSING:", DB)
        return

    print("  Database:", DB.relative_to(ROOT))
    con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row

    try:
        tables = {
            r["name"] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }

        for table in (
            "ncrs", "eight_d_reports", "rca", "capa",
            "investigations", "investigation_trace_events",
            "investigation_audit_records",
        ):
            if table in tables:
                count = con.execute(
                    f'SELECT COUNT(*) FROM "{table}"'
                ).fetchone()[0]
                print(f"  {table}: {count} rows")
            else:
                print(f"  {table}: NOT FOUND")

        if "eight_d_reports" in tables:
            report = con.execute(
                "SELECT * FROM eight_d_reports WHERE report_number=?",
                ("8D-20260012",),
            ).fetchone()

            print("\n  8D-20260012:")
            if not report:
                print("    NOT FOUND")
            else:
                print("    id:", report["id"])
                print("    ncr_id:", report["ncr_id"])
                print("    d4_root_cause:", report["d4_root_cause"])
                print("    d5_corrective_action:", report["d5_corrective_action"])

                for table, label in (("rca", "RCA"), ("capa", "CAPA")):
                    if table not in tables:
                        continue
                    rows = con.execute(
                        f'SELECT * FROM "{table}" WHERE eight_d_id=?',
                        (report["id"],),
                    ).fetchall()
                    print(f"    Linked {label} records: {len(rows)}")
                    for row in rows[:3]:
                        print("     ", dict(row))

    except Exception as exc:
        print("  Database inspection error:", repr(exc))
    finally:
        con.close()

def inspect_code():
    section("CODE REFERENCES")
    terms = (
        "vector_index",
        "LocalVectorStore",
        "SentenceTransformerRetriever",
        "retrieval_method",
        "root_cause_description",
        "eight_d_id",
        "EvidenceRetrievalAgent",
        "RCAAnalystAgent",
    )
    files = []
    for folder in CODE_DIRS:
        if folder.exists():
            files.extend(folder.rglob("*.py"))

    # Include common index/retrieval configuration files under app/.
    app = ROOT / "app"
    if app.exists():
        for path in app.glob("*.py"):
            files.append(path)

    hits = []
    for path in sorted(set(files)):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue
        for number, line in enumerate(lines, 1):
            if any(term.lower() in line.lower() for term in terms):
                hits.append((path.relative_to(ROOT), number, line.strip()))

    print("  Matching code lines:", len(hits))
    for path, number, line in hits[:55]:
        print(f"  {path}:{number}: {line[:180]}")
    if len(hits) > 55:
        print(f"  ... {len(hits) - 55} additional matches omitted")

if __name__ == "__main__":
    section("READ-ONLY CAPSTONE INTEGRITY AUDIT")
    print("Project root:", ROOT)
    print("This script does not write to the database or indexes.")
    inspect_database()
    for folder in INDEX_DIRS:
        inspect_index(folder)
    inspect_code()
    section("AUDIT COMPLETE")
