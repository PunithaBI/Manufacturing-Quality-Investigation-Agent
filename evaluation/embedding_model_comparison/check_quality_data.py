
import sqlite3

conn = sqlite3.connect("data/Northwind_db/nordwind.db")

queries = {
    "Total NCRs": "SELECT COUNT(*) FROM ncrs",
    "NCRs linked to 8D": """
        SELECT COUNT(DISTINCT n.id)
        FROM ncrs n
        JOIN eight_d_reports e ON e.ncr_id = n.id
    """,
    "Total 8D reports": "SELECT COUNT(*) FROM eight_d_reports",
    "8D reports linked to NCR": """
        SELECT COUNT(DISTINCT e.id)
        FROM eight_d_reports e
        JOIN ncrs n ON n.id = e.ncr_id
    """,
    "Total CAPAs": "SELECT COUNT(*) FROM capa",
    "CAPAs linked to 8D": """
        SELECT COUNT(DISTINCT a.id)
        FROM capa a
        JOIN eight_d_reports e ON e.id = a.eight_d_id
    """,
}

for label, sql in queries.items():
    print(f"{label}: {conn.execute(sql).fetchone()[0]}")

print("\n8D REPORT LINKAGE")
for row in conn.execute("""
    SELECT e.report_number, e.ncr_id, n.ncr_number
    FROM eight_d_reports e
    LEFT JOIN ncrs n ON n.id = e.ncr_id
    LIMIT 25
"""):
    print(row)

conn.close()
