
import sqlite3
from pathlib import Path

DATABASES = [
    Path("data/Northwind_db/nordwind.db"),
    Path("data/evaluation/evaluation.db"),
]

TABLE_HINTS = (
    "ncr", "eightd", "8d", "rca", "capa", "inspection",
    "measurement", "manufacturing_order", "operation",
)

FIELD_HINTS = (
    "root_cause", "cause", "analysis", "finding", "conclusion",
    "corrective", "preventive", "problem_description", "description",
    "measurement", "value", "lower_limit", "upper_limit",
    "specification", "result", "remarks", "disposition",
)

def quote_identifier(name):
    return '"' + name.replace('"', '""') + '"'

for db_path in DATABASES:
    print("\n" + "=" * 72)
    print(f"DATABASE: {db_path}")

    if not db_path.exists():
        print("NOT FOUND — skipping.")
        continue

    try:
        # Read-only connection: this script cannot modify the database.
        uri = db_path.resolve().as_uri() + "?mode=ro"
        connection = sqlite3.connect(uri, uri=True)
        connection.execute("PRAGMA query_only = ON")

        tables = [
            row[0] for row in connection.execute("""
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)
        ]

        for table in tables:
            if not any(hint in table.lower() for hint in TABLE_HINTS):
                continue

            qt = quote_identifier(table)
            count = connection.execute(
                f"SELECT COUNT(*) FROM {qt}"
            ).fetchone()[0]

            print(f"\nTABLE: {table} | ROWS: {count}")

            columns = connection.execute(
                f"PRAGMA table_info({qt})"
            ).fetchall()

            selected = [
                col[1] for col in columns
                if any(hint in col[1].lower() for hint in FIELD_HINTS)
            ]

            if not selected:
                print("  No matching investigation/evidence fields found.")
                continue

            for column in selected:
                qc = quote_identifier(column)
                nonempty = connection.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM {qt}
                    WHERE {qc} IS NOT NULL
                      AND TRIM(CAST({qc} AS TEXT)) <> ''
                    """
                ).fetchone()[0]

                examples = connection.execute(
                    f"""
                    SELECT DISTINCT SUBSTR(CAST({qc} AS TEXT), 1, 100)
                    FROM {qt}
                    WHERE {qc} IS NOT NULL
                      AND TRIM(CAST({qc} AS TEXT)) <> ''
                    LIMIT 2
                    """
                ).fetchall()

                print(
                    f"  {column}: populated {nonempty}/{count}"
                    if count else f"  {column}: populated 0/0"
                )

                for example, in examples:
                    print(f"    example: {example}")

        connection.close()

    except Exception as exc:
        print(f"AUDIT ERROR: {type(exc).__name__}: {exc}")

print("\nAUDIT FINISHED. No database writes were performed.")