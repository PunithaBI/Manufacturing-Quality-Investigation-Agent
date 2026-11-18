from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db import models


@pytest.fixture
def db() -> Session:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def authorized_role() -> str:
    return "investigation_agent"


@pytest.fixture
def unauthorized_role() -> str:
    return "unknown_role"


@pytest.fixture
def sample_ncr(db: Session):
    return db.query(models.NCR).order_by(models.NCR.id).first()


@pytest.fixture
def sample_product(db: Session):
    return db.query(models.Product).order_by(models.Product.id).first()


@pytest.fixture
def sample_serial(db: Session):
    return db.query(models.SerialUnit).order_by(models.SerialUnit.id).first()


@pytest.fixture
def sample_mo(db: Session):
    return db.query(models.ManufacturingOrder).order_by(
        models.ManufacturingOrder.id
    ).first()


@pytest.fixture
def sample_bom(db: Session):
    return db.query(models.BOM).order_by(models.BOM.id).first()


@pytest.fixture
def sample_8d(db: Session):
    return db.query(models.EightDReport).order_by(
        models.EightDReport.id
    ).first()