"""
Validates the NordWind database: referential integrity (no orphan foreign
keys), reasonable row counts, and logical consistency between related
tables. Prints a PASS/FAIL report.
"""
from app.database import SessionLocal
from app import models

db = SessionLocal()
errors = []
warnings = []


def check_fk(child_model, fk_attr, parent_model, nullable=False, label=None):
    label = label or f"{child_model.__tablename__}.{fk_attr} -> {parent_model.__tablename__}"
    parent_ids = {row.id for row in db.query(parent_model.id).all()}
    rows = db.query(child_model).all()
    orphans = 0
    for r in rows:
        val = getattr(r, fk_attr)
        if val is None:
            if not nullable:
                orphans += 1
            continue
        if val not in parent_ids:
            orphans += 1
    if orphans:
        errors.append(f"FAIL  {label}: {orphans} orphan/invalid reference(s) out of {len(rows)} rows")
    else:
        print(f"PASS  {label}  ({len(rows)} rows checked)")


def check_min_count(model, minimum, label=None):
    label = label or model.__tablename__
    n = db.query(model).count()
    if n < minimum:
        errors.append(f"FAIL  {label}: expected >= {minimum} rows, found {n}")
    else:
        print(f"PASS  {label}: {n} rows (>= {minimum} required)")


print("=" * 70)
print("REFERENTIAL INTEGRITY CHECKS")
print("=" * 70)

check_fk(models.BOM, "product_id", models.Product)
check_fk(models.BOM, "component_id", models.Component)
check_fk(models.Lot, "component_id", models.Component)
check_fk(models.ManufacturingOrder, "product_id", models.Product)
check_fk(models.SerialUnit, "product_id", models.Product)
check_fk(models.SerialUnit, "mo_id", models.ManufacturingOrder)
check_fk(models.Operation, "mo_id", models.ManufacturingOrder)
check_fk(models.ProcessMeasurement, "operation_id", models.Operation)
check_fk(models.ProcessMeasurement, "serial_unit_id", models.SerialUnit)
check_fk(models.Inspection, "serial_unit_id", models.SerialUnit)
check_fk(models.Inspection, "mo_id", models.ManufacturingOrder)
check_fk(models.NCR, "mo_id", models.ManufacturingOrder)
check_fk(models.NCR, "serial_unit_id", models.SerialUnit, nullable=True)
check_fk(models.NCR, "lot_id", models.Lot, nullable=True)
check_fk(models.NCR, "inspection_id", models.Inspection, nullable=True)
check_fk(models.EightDReport, "ncr_id", models.NCR)
check_fk(models.RCA, "eight_d_id", models.EightDReport)
check_fk(models.CAPA, "eight_d_id", models.EightDReport)

print()
print("=" * 70)
print("MINIMUM POPULATION / COMPLETENESS CHECKS")
print("=" * 70)
check_min_count(models.Product, 1)
check_min_count(models.Component, 1)
check_min_count(models.BOM, 1)
check_min_count(models.Lot, 1)
check_min_count(models.ManufacturingOrder, 1)
check_min_count(models.Operation, 1)
check_min_count(models.SerialUnit, 1)
check_min_count(models.ProcessMeasurement, 1)
check_min_count(models.Inspection, 1)
check_min_count(models.NCR, 1)
check_min_count(models.EightDReport, 1)
check_min_count(models.RCA, 1)
check_min_count(models.CAPA, 1)
check_min_count(models.Document, 1)

print()
print("=" * 70)
print("LOGICAL CONSISTENCY CHECKS")
print("=" * 70)

# Every NCR must reference at least a serial_unit OR a lot
ncrs = db.query(models.NCR).all()
bad = [n for n in ncrs if n.serial_unit_id is None and n.lot_id is None]
if bad:
    errors.append(f"FAIL  NCRs with neither serial_unit_id nor lot_id set: {len(bad)}")
else:
    print(f"PASS  All {len(ncrs)} NCRs reference a serial unit or a lot")

# Every Major/Critical NCR should have an 8D (business rule enforced at seed time)
major_ncrs = [n for n in ncrs if n.severity in ("Major", "Critical")]
ncr_ids_with_8d = {d.ncr_id for d in db.query(models.EightDReport).all()}
missing_8d = [n for n in major_ncrs if n.id not in ncr_ids_with_8d]
if missing_8d:
    warnings.append(f"WARN  {len(missing_8d)} Major/Critical NCR(s) have no 8D report")
else:
    print(f"PASS  All {len(major_ncrs)} Major/Critical NCRs have an associated 8D report")

# Every 8D should have exactly one RCA and at least one CAPA
eight_ds = db.query(models.EightDReport).all()
rca_by_8d = {}
for r in db.query(models.RCA).all():
    rca_by_8d.setdefault(r.eight_d_id, 0)
    rca_by_8d[r.eight_d_id] += 1
capa_by_8d = {}
for c in db.query(models.CAPA).all():
    capa_by_8d.setdefault(c.eight_d_id, 0)
    capa_by_8d[c.eight_d_id] += 1

missing_rca = [d.id for d in eight_ds if rca_by_8d.get(d.id, 0) == 0]
missing_capa = [d.id for d in eight_ds if capa_by_8d.get(d.id, 0) == 0]
if missing_rca:
    errors.append(f"FAIL  8D reports without an RCA: {missing_rca}")
else:
    print(f"PASS  All {len(eight_ds)} 8D reports have >=1 RCA")
if missing_capa:
    errors.append(f"FAIL  8D reports without a CAPA: {missing_capa}")
else:
    print(f"PASS  All {len(eight_ds)} 8D reports have >=1 CAPA")

# Closed NCRs must have a date_closed >= date_opened
bad_dates = [n for n in ncrs if n.status == "Closed" and (n.date_closed is None or n.date_closed < n.date_opened)]
if bad_dates:
    errors.append(f"FAIL  Closed NCRs with missing/invalid date_closed: {len(bad_dates)}")
else:
    closed = [n for n in ncrs if n.status == "Closed"]
    print(f"PASS  All {len(closed)} closed NCRs have a valid date_closed >= date_opened")

# Every product referenced by BOM has at least one component
products_with_bom = {b.product_id for b in db.query(models.BOM).all()}
products = db.query(models.Product).all()
no_bom = [p for p in products if p.id not in products_with_bom]
if no_bom:
    errors.append(f"FAIL  Products with no BOM entries: {[p.product_code for p in no_bom]}")
else:
    print(f"PASS  All {len(products)} products have at least one BOM component")

# Every MO has at least one operation and at least one serial unit
mo_list = db.query(models.ManufacturingOrder).all()
op_mo_ids = {o.mo_id for o in db.query(models.Operation).all()}
su_mo_ids = {s.mo_id for s in db.query(models.SerialUnit).all()}
no_ops = [m for m in mo_list if m.id not in op_mo_ids]
no_su = [m for m in mo_list if m.id not in su_mo_ids]
if no_ops:
    errors.append(f"FAIL  MOs with zero operations: {[m.mo_number for m in no_ops]}")
else:
    print(f"PASS  All {len(mo_list)} manufacturing orders have >=1 operation")
if no_su:
    errors.append(f"FAIL  MOs with zero serial units: {[m.mo_number for m in no_su]}")
else:
    print(f"PASS  All {len(mo_list)} manufacturing orders have >=1 serial unit")

# Process measurements marked in_spec should actually fall within lsl/usl (and vice versa)
pms = db.query(models.ProcessMeasurement).all()
mismatch = 0
for pm in pms:
    actually_in_spec = pm.lsl <= pm.actual_value <= pm.usl
    if actually_in_spec != pm.in_spec:
        mismatch += 1
if mismatch:
    errors.append(f"FAIL  {mismatch} process measurements have in_spec flag inconsistent with lsl/usl/actual")
else:
    print(f"PASS  All {len(pms)} process measurements have a consistent in_spec flag")

# Documents point to existing parent rows for the tables we track
doc_targets = {
    "inspections": models.Inspection,
    "ncrs": models.NCR,
    "8d_reports": models.EightDReport,
    "rca": models.RCA,
    "capa": models.CAPA,
    "lots": models.Lot,
}
docs = db.query(models.Document).all()
doc_orphans = 0
for tbl, model in doc_targets.items():
    valid_ids = {row.id for row in db.query(model.id).all()}
    for d in [d for d in docs if d.related_table == tbl]:
        if d.related_id not in valid_ids:
            doc_orphans += 1
if doc_orphans:
    errors.append(f"FAIL  Documents pointing to non-existent parent rows: {doc_orphans}")
else:
    print(f"PASS  All {len(docs)} documents reference an existing parent record")

print()
print("=" * 70)
print("SUMMARY")
print("=" * 70)
if warnings:
    for w in warnings:
        print(w)
if errors:
    for e in errors:
        print(e)
    print(f"\nRESULT: FAIL  ({len(errors)} error(s), {len(warnings)} warning(s))")
else:
    print(f"RESULT: VALIDATION PASS  (0 errors, {len(warnings)} warning(s))")

db.close()
