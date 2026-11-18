from sqlalchemy import (
    Column, Integer, String, Float, Boolean, ForeignKey, DateTime, Text, UniqueConstraint
)
from sqlalchemy.orm import relationship
from .database import Base
import datetime


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    product_code = Column(String(30), unique=True, nullable=False)
    name = Column(String(120), nullable=False)
    description = Column(Text)
    revision = Column(String(10), default="A")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    boms = relationship("BOM", back_populates="product")
    manufacturing_orders = relationship("ManufacturingOrder", back_populates="product")
    serial_units = relationship("SerialUnit", back_populates="product")


class Component(Base):
    __tablename__ = "components"
    id = Column(Integer, primary_key=True)
    component_code = Column(String(30), unique=True, nullable=False)
    name = Column(String(120), nullable=False)
    description = Column(Text)
    supplier = Column(String(120))
    unit_of_measure = Column(String(10), default="EA")

    boms = relationship("BOM", back_populates="component")
    lots = relationship("Lot", back_populates="component")


class BOM(Base):
    __tablename__ = "bom"
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    component_id = Column(Integer, ForeignKey("components.id"), nullable=False)
    quantity_per_unit = Column(Float, nullable=False, default=1.0)
    bom_revision = Column(String(10), default="A")
    __table_args__ = (UniqueConstraint("product_id", "component_id", "bom_revision"),)

    product = relationship("Product", back_populates="boms")
    component = relationship("Component", back_populates="boms")


class Lot(Base):
    __tablename__ = "lots"
    id = Column(Integer, primary_key=True)
    lot_number = Column(String(40), unique=True, nullable=False)
    component_id = Column(Integer, ForeignKey("components.id"), nullable=False)
    supplier_lot_number = Column(String(40))
    receipt_date = Column(DateTime)
    quantity = Column(Float)
    quality_status = Column(String(20), default="Released")  # Released, Quarantine, Rejected

    component = relationship("Component", back_populates="lots")
    ncrs = relationship("NCR", back_populates="lot")


class ManufacturingOrder(Base):
    __tablename__ = "manufacturing_orders"
    id = Column(Integer, primary_key=True)
    mo_number = Column(String(30), unique=True, nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity_planned = Column(Integer, nullable=False)
    quantity_completed = Column(Integer, default=0)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    status = Column(String(20), default="Open")  # Open, In Progress, Closed

    product = relationship("Product", back_populates="manufacturing_orders")
    operations = relationship("Operation", back_populates="mo")
    serial_units = relationship("SerialUnit", back_populates="mo")
    inspections = relationship("Inspection", back_populates="mo")
    ncrs = relationship("NCR", back_populates="mo")


class SerialUnit(Base):
    __tablename__ = "serial_units"
    id = Column(Integer, primary_key=True)
    serial_number = Column(String(40), unique=True, nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    mo_id = Column(Integer, ForeignKey("manufacturing_orders.id"), nullable=False)
    status = Column(String(20), default="In Process")  # In Process, Passed, Scrapped, Shipped
    build_date = Column(DateTime)

    product = relationship("Product", back_populates="serial_units")
    mo = relationship("ManufacturingOrder", back_populates="serial_units")
    process_measurements = relationship("ProcessMeasurement", back_populates="serial_unit")
    inspections = relationship("Inspection", back_populates="serial_unit")
    ncrs = relationship("NCR", back_populates="serial_unit")


class Operation(Base):
    __tablename__ = "operations"
    id = Column(Integer, primary_key=True)
    mo_id = Column(Integer, ForeignKey("manufacturing_orders.id"), nullable=False)
    operation_seq = Column(Integer, nullable=False)
    operation_name = Column(String(80), nullable=False)
    work_center = Column(String(60))
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    operator = Column(String(60))
    status = Column(String(20), default="Completed")

    mo = relationship("ManufacturingOrder", back_populates="operations")
    process_measurements = relationship("ProcessMeasurement", back_populates="operation")


class ProcessMeasurement(Base):
    __tablename__ = "process_measurements"
    id = Column(Integer, primary_key=True)
    operation_id = Column(Integer, ForeignKey("operations.id"), nullable=False)
    serial_unit_id = Column(Integer, ForeignKey("serial_units.id"), nullable=False)
    parameter_name = Column(String(80), nullable=False)
    nominal_value = Column(Float)
    actual_value = Column(Float)
    unit = Column(String(20))
    lsl = Column(Float)
    usl = Column(Float)
    in_spec = Column(Boolean, default=True)
    measured_at = Column(DateTime)

    operation = relationship("Operation", back_populates="process_measurements")
    serial_unit = relationship("SerialUnit", back_populates="process_measurements")


class Inspection(Base):
    __tablename__ = "inspections"
    id = Column(Integer, primary_key=True)
    serial_unit_id = Column(Integer, ForeignKey("serial_units.id"), nullable=False)
    mo_id = Column(Integer, ForeignKey("manufacturing_orders.id"), nullable=False)
    inspection_type = Column(String(40))  # Incoming, In-Process, Final
    inspector = Column(String(60))
    inspection_date = Column(DateTime)
    result = Column(String(20), default="Pass")  # Pass, Fail

    serial_unit = relationship("SerialUnit", back_populates="inspections")
    mo = relationship("ManufacturingOrder", back_populates="inspections")
    ncrs = relationship("NCR", back_populates="inspection")


class NCR(Base):
    __tablename__ = "ncrs"
    id = Column(Integer, primary_key=True)
    ncr_number = Column(String(30), unique=True, nullable=False)
    serial_unit_id = Column(Integer, ForeignKey("serial_units.id"), nullable=True)
    lot_id = Column(Integer, ForeignKey("lots.id"), nullable=True)
    mo_id = Column(Integer, ForeignKey("manufacturing_orders.id"), nullable=False)
    inspection_id = Column(Integer, ForeignKey("inspections.id"), nullable=True)
    description = Column(Text)
    severity = Column(String(20), default="Minor")  # Minor, Major, Critical
    status = Column(String(20), default="Open")  # Open, Under Review, Closed
    date_opened = Column(DateTime)
    date_closed = Column(DateTime, nullable=True)

    serial_unit = relationship("SerialUnit", back_populates="ncrs")
    lot = relationship("Lot", back_populates="ncrs")
    mo = relationship("ManufacturingOrder", back_populates="ncrs")
    inspection = relationship("Inspection", back_populates="ncrs")
    eight_d_reports = relationship("EightDReport", back_populates="ncr")


class EightDReport(Base):
    __tablename__ = "eight_d_reports"
    id = Column(Integer, primary_key=True)
    report_number = Column(String(30), unique=True, nullable=False)
    ncr_id = Column(Integer, ForeignKey("ncrs.id"), nullable=False)
    d1_team = Column(String(200))
    d2_problem_description = Column(Text)
    d3_containment_action = Column(Text)
    d4_root_cause = Column(Text)
    d5_corrective_action = Column(Text)
    d6_implementation = Column(Text)
    d7_prevention = Column(Text)
    d8_closure = Column(Text)
    status = Column(String(20), default="Open")
    date_opened = Column(DateTime)
    date_closed = Column(DateTime, nullable=True)

    ncr = relationship("NCR", back_populates="eight_d_reports")
    rcas = relationship("RCA", back_populates="eight_d_report")
    capas = relationship("CAPA", back_populates="eight_d_report")


class RCA(Base):
    __tablename__ = "rca"
    id = Column(Integer, primary_key=True)
    eight_d_id = Column(Integer, ForeignKey("eight_d_reports.id"), nullable=False)
    method = Column(String(40))  # 5-Why, Fishbone, Fault Tree
    root_cause_description = Column(Text)
    contributing_factors = Column(Text)
    date_completed = Column(DateTime)

    eight_d_report = relationship("EightDReport", back_populates="rcas")


class CAPA(Base):
    __tablename__ = "capa"
    id = Column(Integer, primary_key=True)
    capa_number = Column(String(30), unique=True, nullable=False)
    eight_d_id = Column(Integer, ForeignKey("eight_d_reports.id"), nullable=False)
    corrective_action = Column(Text)
    preventive_action = Column(Text)
    owner = Column(String(80))
    due_date = Column(DateTime)
    status = Column(String(20), default="Open")  # Open, In Progress, Closed, Verified
    effectiveness_check = Column(String(20), nullable=True)  # Pending, Effective, Not Effective
    date_closed = Column(DateTime, nullable=True)

    eight_d_report = relationship("EightDReport", back_populates="capas")


class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True)
    related_table = Column(String(40), nullable=False)  # e.g. "ncrs", "capa", "inspections"
    related_id = Column(Integer, nullable=False)
    doc_type = Column(String(40))  # Photo, Report, Certificate, Drawing
    file_name = Column(String(200))
    description = Column(Text)
    uploaded_by = Column(String(60))
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)
