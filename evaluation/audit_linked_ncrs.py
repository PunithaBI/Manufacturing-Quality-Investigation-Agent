
import sqlite3
from pathlib import Path

db = Path("data/Northwind_db/nordwind.db").resolve()
uri = db.as_uri() + "?mode=ro"

with sqlite3.connect(uri, uri=True) as conn:
    conn.row_factory = sqlite3.Row

    query = """
    SELECT
        e.id AS eight_d_id,
        e.report_number,
        e.ncr_id AS linked_ncr_id,
        n.ncr_number AS linked_ncr_number,
        n.description AS linked_ncr_description,
        n.severity AS linked_ncr_severity,
        n.status AS linked_ncr_status,
        r.id AS rca_id,
        r.root_cause_description,
        c.id AS capa_id,
        c.status AS capa_status,
        c.effectiveness_check
    FROM eight_d_reports e
    LEFT JOIN ncrs n ON n.id = e.ncr_id
    LEFT JOIN rca r ON r.eight_d_id = e.id
    LEFT JOIN capa c ON c.eight_d_id = e.id
    WHERE e.id IN (12, 17)
    ORDER BY e.id
    """

    for row in conn.execute(query):
        print(dict(row))
