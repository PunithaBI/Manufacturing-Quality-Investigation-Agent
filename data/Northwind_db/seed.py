"""
Seed the NordWind manufacturing database with realistic, fully-connected
synthetic data across all 14 entities.
"""
import random
import datetime
from app.database import engine, SessionLocal, Base
from app import models

random.seed(42)

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

db = SessionLocal()

NOW = datetime.datetime(2026, 9, 1)


def days_ago(n):
    return NOW - datetime.timedelta(days=n)


# ---------------------------------------------------------------- PRODUCTS
product_defs = [
    ("PRD-1001", "NordWind Turbine Blade Assembly TB-40", "40m composite wind turbine blade assembly"),
    ("PRD-1002", "NordWind Gearbox Unit GB-500", "500kW planetary gearbox unit"),
    ("PRD-1003", "NordWind Nacelle Control Module NCM-2", "Nacelle-mounted control & sensor module"),
    ("PRD-1004", "NordWind Yaw Drive Assembly YD-12", "12-motor yaw drive assembly"),
    ("PRD-1005", "NordWind Pitch Bearing PB-3000", "Main pitch bearing, 3000mm bore"),
]
products = []
for code, name, desc in product_defs:
    p = models.Product(product_code=code, name=name, description=desc, revision="B",
                        created_at=days_ago(400))
    db.add(p)
    products.append(p)
db.commit()

# ---------------------------------------------------------------- COMPONENTS
component_defs = [
    ("CMP-2001", "Carbon Fiber Spar Cap", "Baltic Composites GmbH", "M"),
    ("CMP-2002", "Epoxy Resin System", "ResinTech AS", "L"),
    ("CMP-2003", "Root Insert Bolt M36", "Nordic Fasteners AB", "EA"),
    ("CMP-2004", "Planetary Gear Set", "Precision Gear Co.", "EA"),
    ("CMP-2005", "Gearbox Housing Casting", "Ferro Cast Ltd.", "EA"),
    ("CMP-2006", "Lubrication Pump Module", "HydroFlow Systems", "EA"),
    ("CMP-2007", "PCB Control Board Rev C", "CircuitWorks Elektronik", "EA"),
    ("CMP-2008", "Vibration Sensor Array", "SensAll Technologies", "EA"),
    ("CMP-2009", "Yaw Motor 3-Phase 15kW", "ElektroDrive GmbH", "EA"),
    ("CMP-2010", "Slew Ring Gear", "HeavyRing Manufacturing", "EA"),
    ("CMP-2011", "Bearing Raceway Steel Ring", "SteelForm Industries", "EA"),
    ("CMP-2012", "Sealing Kit PB-3000", "SealTech Nordic", "SET"),
]
components = []
for code, name, supplier, uom in component_defs:
    c = models.Component(component_code=code, name=name, description=f"{name} used in NordWind assemblies",
                          supplier=supplier, unit_of_measure=uom)
    db.add(c)
    components.append(c)
db.commit()

# ---------------------------------------------------------------- BOM
# Assign 2-4 components per product
bom_map = {
    products[0]: components[0:3],   # Blade -> spar cap, resin, root bolt
    products[1]: components[3:6],   # Gearbox -> gear set, housing, lube pump
    products[2]: components[6:8],   # Control module -> PCB, sensor array
    products[3]: components[8:10],  # Yaw drive -> motor, slew ring
    products[4]: [components[10], components[11]],  # Pitch bearing -> raceway, seal kit
}
boms = []
for product, comps in bom_map.items():
    for comp in comps:
        b = models.BOM(product_id=product.id, component_id=comp.id,
                        quantity_per_unit=round(random.uniform(1, 12), 1),
                        bom_revision="B")
        db.add(b)
        boms.append(b)
db.commit()

# ---------------------------------------------------------------- LOTS
lots = []
lot_counter = 1
for comp in components:
    for _ in range(random.randint(2, 3)):
        lot = models.Lot(
            lot_number=f"LOT-{comp.component_code[-4:]}-{lot_counter:04d}",
            component_id=comp.id,
            supplier_lot_number=f"SUP-{random.randint(100000,999999)}",
            receipt_date=days_ago(random.randint(30, 380)),
            quantity=round(random.uniform(50, 2000), 1),
            quality_status=random.choices(
                ["Released", "Quarantine", "Rejected"], weights=[0.85, 0.1, 0.05]
            )[0],
        )
        db.add(lot)
        lots.append(lot)
        lot_counter += 1
db.commit()

lots_by_component = {}
for lot in lots:
    lots_by_component.setdefault(lot.component_id, []).append(lot)

# ---------------------------------------------------------------- MANUFACTURING ORDERS
mo_list = []
mo_counter = 1
for product in products:
    for _ in range(random.randint(3, 4)):
        qty_planned = random.choice([5, 10, 15, 20, 25])
        start = days_ago(random.randint(20, 300))
        duration = random.randint(3, 12)
        end = start + datetime.timedelta(days=duration)
        status = random.choices(["Closed", "In Progress", "Open"], weights=[0.7, 0.2, 0.1])[0]
        qty_completed = qty_planned if status == "Closed" else random.randint(0, qty_planned - 1)
        mo = models.ManufacturingOrder(
            mo_number=f"MO-{2026}{mo_counter:05d}",
            product_id=product.id,
            quantity_planned=qty_planned,
            quantity_completed=qty_completed,
            start_date=start,
            end_date=end if status == "Closed" else None,
            status=status,
        )
        db.add(mo)
        mo_list.append(mo)
        mo_counter += 1
db.commit()

# ---------------------------------------------------------------- OPERATIONS
OP_TEMPLATES = [
    "Material Kitting", "Layup / Assembly", "Curing / Heat Treatment",
    "Machining", "Sub-Assembly Integration", "Torque & Fastening",
    "Calibration", "Functional Test", "Final Assembly", "Packaging",
]
operations = []
op_counter = 1
for mo in mo_list:
    n_ops = random.randint(4, 6)
    op_names = random.sample(OP_TEMPLATES, n_ops)
    t = mo.start_date
    for seq, name in enumerate(op_names, start=1):
        op_start = t
        op_end = op_start + datetime.timedelta(hours=random.randint(2, 10))
        t = op_end
        op = models.Operation(
            mo_id=mo.id,
            operation_seq=seq,
            operation_name=name,
            work_center=f"WC-{random.randint(1,8):02d}",
            start_time=op_start,
            end_time=op_end,
            operator=random.choice(["A. Larsen", "M. Kowalski", "S. Ivanova", "J. Berg", "T. Nilsen"]),
            status="Completed" if mo.status == "Closed" else random.choice(["Completed", "In Progress"]),
        )
        db.add(op)
        operations.append(op)
        op_counter += 1
db.commit()

ops_by_mo = {}
for op in operations:
    ops_by_mo.setdefault(op.mo_id, []).append(op)

# ---------------------------------------------------------------- SERIAL UNITS
serial_units = []
su_counter = 1
for mo in mo_list:
    n_units = mo.quantity_completed if mo.quantity_completed > 0 else min(mo.quantity_planned, 2)
    n_units = max(n_units, 1)
    for i in range(n_units):
        status = "Shipped" if mo.status == "Closed" else random.choice(["In Process", "Passed"])
        su = models.SerialUnit(
            serial_number=f"SN-{mo.product.product_code[-4:]}-{su_counter:06d}",
            product_id=mo.product_id,
            mo_id=mo.id,
            status=status,
            build_date=(mo.end_date or mo.start_date) + datetime.timedelta(days=i % 3),
        )
        db.add(su)
        serial_units.append(su)
        su_counter += 1
db.commit()

su_by_mo = {}
for su in serial_units:
    su_by_mo.setdefault(su.mo_id, []).append(su)

# ---------------------------------------------------------------- PROCESS MEASUREMENTS
PARAM_TEMPLATES = [
    ("Cure Temperature", 120.0, 5.0, "C"),
    ("Bolt Torque", 450.0, 20.0, "Nm"),
    ("Bore Diameter", 3000.0, 0.5, "mm"),
    ("Vibration RMS", 2.0, 0.5, "mm/s"),
    ("Insulation Resistance", 100.0, 10.0, "MOhm"),
    ("Gear Backlash", 0.15, 0.05, "mm"),
]
measurements = []
for mo in mo_list:
    ops = ops_by_mo.get(mo.id, [])
    units = su_by_mo.get(mo.id, [])
    if not ops or not units:
        continue
    for su in units:
        for _ in range(random.randint(2, 4)):
            op = random.choice(ops)
            name, nominal, tol, unit = random.choice(PARAM_TEMPLATES)
            actual = round(random.gauss(nominal, tol * 0.5), 2)
            lsl, usl = nominal - tol, nominal + tol
            in_spec = lsl <= actual <= usl
            pm = models.ProcessMeasurement(
                operation_id=op.id,
                serial_unit_id=su.id,
                parameter_name=name,
                nominal_value=nominal,
                actual_value=actual,
                unit=unit,
                lsl=lsl,
                usl=usl,
                in_spec=in_spec,
                measured_at=op.end_time,
            )
            db.add(pm)
            measurements.append(pm)
db.commit()

# ---------------------------------------------------------------- INSPECTIONS
inspections = []
for mo in mo_list:
    units = su_by_mo.get(mo.id, [])
    for su in units:
        for itype in ["In-Process", "Final"]:
            result = random.choices(["Pass", "Fail"], weights=[0.9, 0.1])[0]
            insp = models.Inspection(
                serial_unit_id=su.id,
                mo_id=mo.id,
                inspection_type=itype,
                inspector=random.choice(["K. Svendsen", "R. Haugen", "L. Weiss", "P. Dahl"]),
                inspection_date=su.build_date,
                result=result,
            )
            db.add(insp)
            inspections.append(insp)
db.commit()

failed_inspections = [i for i in inspections if i.result == "Fail"]

# ---------------------------------------------------------------- NCRs
NCR_DESCRIPTIONS = [
    "Dimensional non-conformance found on final inspection.",
    "Torque value out of specification during assembly.",
    "Surface defect detected on composite layup.",
    "Incoming material lot failed acceptance criteria.",
    "Vibration reading exceeded upper spec limit during test.",
    "Bore diameter measured out of tolerance.",
]
ncrs = []
ncr_counter = 1
# NCRs from failed inspections
for insp in failed_inspections:
    ncr = models.NCR(
        ncr_number=f"NCR-{2026}{ncr_counter:04d}",
        serial_unit_id=insp.serial_unit_id,
        lot_id=None,
        mo_id=insp.mo_id,
        inspection_id=insp.id,
        description=random.choice(NCR_DESCRIPTIONS),
        severity=random.choices(["Minor", "Major", "Critical"], weights=[0.5, 0.35, 0.15])[0],
        status=random.choices(["Open", "Under Review", "Closed"], weights=[0.2, 0.2, 0.6])[0],
        date_opened=insp.inspection_date,
    )
    if ncr.status == "Closed":
        ncr.date_closed = ncr.date_opened + datetime.timedelta(days=random.randint(3, 20))
    db.add(ncr)
    ncrs.append(ncr)
    ncr_counter += 1

# A few NCRs tied to rejected/quarantined incoming lots
bad_lots = [l for l in lots if l.quality_status in ("Rejected", "Quarantine")]
for lot in bad_lots:
    mo = random.choice(mo_list)
    ncr = models.NCR(
        ncr_number=f"NCR-{2026}{ncr_counter:04d}",
        serial_unit_id=None,
        lot_id=lot.id,
        mo_id=mo.id,
        inspection_id=None,
        description="Incoming material lot failed acceptance criteria.",
        severity=random.choices(["Minor", "Major", "Critical"], weights=[0.4, 0.4, 0.2])[0],
        status=random.choices(["Open", "Under Review", "Closed"], weights=[0.2, 0.2, 0.6])[0],
        date_opened=lot.receipt_date + datetime.timedelta(days=1),
    )
    if ncr.status == "Closed":
        ncr.date_closed = ncr.date_opened + datetime.timedelta(days=random.randint(3, 20))
    db.add(ncr)
    ncrs.append(ncr)
    ncr_counter += 1

db.commit()

# 8D reports are opened for Major/Critical NCRs
major_ncrs = [n for n in ncrs if n.severity in ("Major", "Critical")]

# ---------------------------------------------------------------- 8D REPORTS
eight_ds = []
d8_counter = 1
for ncr in major_ncrs:
    d8 = models.EightDReport(
        report_number=f"8D-{2026}{d8_counter:04d}",
        ncr_id=ncr.id,
        d1_team="Quality Engineer, Process Engineer, Production Supervisor, Supplier Quality Rep",
        d2_problem_description=ncr.description,
        d3_containment_action="Quarantined affected units/lot; halted downstream operations pending review.",
        d4_root_cause="Pending RCA" if ncr.status != "Closed" else "See linked RCA for root cause.",
        d5_corrective_action="See linked CAPA for corrective action plan.",
        d6_implementation="Corrective action implemented on production line.",
        d7_prevention="Updated work instructions and inspection checklist to prevent recurrence.",
        d8_closure="Closed after effectiveness verification." if ncr.status == "Closed" else "Open",
        status=ncr.status,
        date_opened=ncr.date_opened + datetime.timedelta(days=1),
        date_closed=ncr.date_closed,
    )
    db.add(d8)
    eight_ds.append(d8)
    d8_counter += 1
db.commit()

# ---------------------------------------------------------------- RCA
RCA_METHODS = ["5-Why", "Fishbone", "Fault Tree"]
ROOT_CAUSES = [
    "Insufficient torque wrench calibration frequency led to under-torqued fasteners.",
    "Operator training gap on updated cure cycle parameters.",
    "Supplier process drift caused dimensional variation in raw material.",
    "Fixture wear caused misalignment during machining operation.",
    "Sensor drift caused inaccurate vibration readings during test.",
]
rcas = []
for d8 in eight_ds:
    rca = models.RCA(
        eight_d_id=d8.id,
        method=random.choice(RCA_METHODS),
        root_cause_description=random.choice(ROOT_CAUSES),
        contributing_factors="Maintenance schedule adherence, operator workload, environmental humidity.",
        date_completed=d8.date_opened + datetime.timedelta(days=random.randint(2, 10)),
    )
    db.add(rca)
    rcas.append(rca)
db.commit()

# ---------------------------------------------------------------- CAPA
capas = []
capa_counter = 1
for d8 in eight_ds:
    due = d8.date_opened + datetime.timedelta(days=random.randint(15, 45))
    status = d8.status if d8.status in ("Open", "Closed") else "In Progress"
    capa = models.CAPA(
        capa_number=f"CAPA-{2026}{capa_counter:04d}",
        eight_d_id=d8.id,
        corrective_action="Re-calibrated equipment and reworked/replaced non-conforming units.",
        preventive_action="Revised PM schedule and added in-process checkpoint to control plan.",
        owner=random.choice(["Quality Manager", "Process Engineer", "Production Manager"]),
        due_date=due,
        status=status,
        effectiveness_check=("Effective" if status == "Closed" else "Pending"),
        date_closed=d8.date_closed,
    )
    db.add(capa)
    capas.append(capa)
    capa_counter += 1
db.commit()

# ---------------------------------------------------------------- DOCUMENTS / EVIDENCE
documents = []
doc_counter = 1


def add_doc(table, obj_id, doc_type, fname_hint):
    global doc_counter
    doc = models.Document(
        related_table=table,
        related_id=obj_id,
        doc_type=doc_type,
        file_name=f"{fname_hint}_{doc_counter:05d}.pdf",
        description=f"{doc_type} evidence for {table} record {obj_id}",
        uploaded_by=random.choice(["Q. System (auto)", "K. Svendsen", "R. Haugen"]),
        uploaded_at=NOW - datetime.timedelta(days=random.randint(0, 200)),
    )
    db.add(doc)
    documents.append(doc)
    doc_counter += 1


for insp in inspections:
    if insp.result == "Fail" or random.random() < 0.15:
        add_doc("inspections", insp.id, "Inspection Report", "INSP")

for ncr in ncrs:
    add_doc("ncrs", ncr.id, "NCR Form", "NCR")
    if random.random() < 0.6:
        add_doc("ncrs", ncr.id, "Photo", "NCR_PHOTO")

for d8 in eight_ds:
    add_doc("8d_reports", d8.id, "8D Report", "8D")

for rca in rcas:
    add_doc("rca", rca.id, "RCA Diagram", "RCA")

for capa in capas:
    add_doc("capa", capa.id, "CAPA Verification Record", "CAPA")

for lot in lots:
    if random.random() < 0.3:
        add_doc("lots", lot.id, "Certificate of Conformance", "COC")

db.commit()

# ---------------------------------------------------------------- SUMMARY
print("=== SEED COMPLETE ===")
counts = {
    "products": len(products),
    "components": len(components),
    "bom": len(boms),
    "lots": len(lots),
    "manufacturing_orders": len(mo_list),
    "operations": len(operations),
    "serial_units": len(serial_units),
    "process_measurements": len(measurements),
    "inspections": len(inspections),
    "ncrs": len(ncrs),
    "8d_reports": len(eight_ds),
    "rca": len(rcas),
    "capa": len(capas),
    "documents": len(documents),
}
for k, v in counts.items():
    print(f"{k:22s}: {v}")

db.close()
