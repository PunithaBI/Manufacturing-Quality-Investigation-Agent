# NordWind Manufacturing Quality Database

FastAPI + SQLite implementation of the NordWind manufacturing/quality traceability
schema: Products, Components, BOM, Lots, Serial Units, Manufacturing Orders,
Operations, Process Measurements, Inspections, NCRs, 8D Reports, RCA, CAPA,
and Documents/Evidence — fully connected with realistic synthetic data.

## Structure
```
app/
  models.py     SQLAlchemy models for all 14 entities (with FKs/relationships)
  database.py   SQLite engine/session setup (nordwind.db)
  main.py       FastAPI app — generic list/get/count routes per entity,
                 plus a /traceability/{serial_number} genealogy endpoint
seed.py         Populates the DB with connected, realistic synthetic data
validate.py     Referential-integrity + logical-consistency checks (PASS/FAIL)
nordwind.db     The seeded SQLite database
```

## Run it
```bash
pip install fastapi uvicorn sqlalchemy
python3 seed.py                 # (re)builds nordwind.db with fresh data
python3 validate.py             # runs all integrity/consistency checks
uvicorn app.main:app --reload   # starts the API at http://127.0.0.1:8000
```
Then open `http://127.0.0.1:8000/docs` for interactive Swagger docs.

## Data model / relationships
```
Product 1---N BOM N---1 Component 1---N Lot
Product 1---N ManufacturingOrder 1---N Operation
ManufacturingOrder 1---N SerialUnit
Operation + SerialUnit ---N ProcessMeasurement
SerialUnit + ManufacturingOrder ---N Inspection
NCR --- SerialUnit (or Lot) + ManufacturingOrder + Inspection
NCR 1---N EightDReport 1---N RCA
EightDReport 1---N CAPA
Document.related_table/related_id ---> polymorphic link to any of the above
```

## Seeded volumes (this run)
5 products · 12 components · 12 BOM lines · 29 lots · 15 manufacturing orders ·
74 operations · 209 serial units · 619 process measurements · 418 inspections ·
43 NCRs · 19 8D reports · 19 RCAs · 19 CAPAs · 237 documents.

## Validation result
`python3 validate.py` → **VALIDATION PASS (0 errors, 0 warnings)** — checks
every foreign key for orphans, confirms every table is populated, and verifies
business logic (every Major/Critical NCR has an 8D, every 8D has an RCA and a
CAPA, closed dates are consistent, in-spec flags match LSL/USL, etc.).

## Example: full genealogy trace
`GET /traceability/SN-1001-000001` walks Product → BOM → Components → Lots →
Operations → Process Measurements → Inspections → NCRs for one serial unit.
