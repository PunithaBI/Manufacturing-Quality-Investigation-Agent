from app.db.database import SessionLocal
from app.db.models import EightDReport

db = SessionLocal()
try:
    rows = db.query(EightDReport).limit(5).all()
    for row in rows:
        print("\nReport:", row.report_number)
        print("D5 corrective action:", repr(row.d5_corrective_action))
        print("D6 implementation:", repr(row.d6_implementation))
        print("D7 prevention:", repr(row.d7_prevention))
        print("D8 closure:", repr(row.d8_closure))
finally:
    db.close()
