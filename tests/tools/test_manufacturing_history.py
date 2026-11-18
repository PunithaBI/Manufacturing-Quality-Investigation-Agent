import pytest
from pydantic import ValidationError

from app.tools.errors import ToolErrorCode
from app.tools.manufacturing_history import (
    ManufacturingHistoryRequest,
    get_manufacturing_history,
)


def test_manufacturing_history_by_serial(
    db,
    sample_serial,
    authorized_role,
):
    if sample_serial is None:
        return

    request = ManufacturingHistoryRequest(
        serial_number=sample_serial.serial_number,
        role=authorized_role,
    )

    result = get_manufacturing_history(db, request)

    assert result.success is True
    assert result.data is not None
    assert isinstance(result.data, list)

    if result.data:
        for item in result.data:
            assert item.mo_number == sample_serial.mo.mo_number


def test_manufacturing_history_by_mo(
    db,
    sample_mo,
    authorized_role,
):
    if sample_mo is None:
        return

    request = ManufacturingHistoryRequest(
        mo_number=sample_mo.mo_number,
        role=authorized_role,
    )

    result = get_manufacturing_history(db, request)

    assert result.success is True
    assert result.data is not None
    assert isinstance(result.data, list)


def test_manufacturing_history_requires_serial_or_mo(
    db,
    authorized_role,
):
    with pytest.raises(ValidationError):
        ManufacturingHistoryRequest(
            role=authorized_role,
        )


def test_manufacturing_history_rejects_both(
    db,
    sample_serial,
    sample_mo,
    authorized_role,
):
    if sample_serial is None or sample_mo is None:
        return

    with pytest.raises(ValidationError):
        ManufacturingHistoryRequest(
            serial_number=sample_serial.serial_number,
            mo_number=sample_mo.mo_number,
            role=authorized_role,
        )


def test_manufacturing_history_limit(
    db,
    sample_serial,
    authorized_role,
):
    if sample_serial is None:
        return

    with pytest.raises(ValidationError):
        ManufacturingHistoryRequest(
            serial_number=sample_serial.serial_number,
            limit=1001,
            role=authorized_role,
        )


def test_manufacturing_history_not_found(
    db,
    authorized_role,
):
    request = ManufacturingHistoryRequest(
        serial_number="SN-DOES-NOT-EXIST-999999",
        role=authorized_role,
    )

    result = get_manufacturing_history(db, request)

    assert result.success is False
    assert any(
        error.code == ToolErrorCode.RECORD_NOT_FOUND
        for error in result.errors
    )


def test_manufacturing_history_unauthorized(
    db,
    sample_serial,
    unauthorized_role,
):
    if sample_serial is None:
        return

    request = ManufacturingHistoryRequest(
        serial_number=sample_serial.serial_number,
        role=unauthorized_role,
    )

    result = get_manufacturing_history(db, request)

    assert result.success is False
    assert any(
        error.code == ToolErrorCode.TOOL_UNAUTHORIZED
        for error in result.errors
    )