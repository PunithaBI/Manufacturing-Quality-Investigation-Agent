import pytest
from pydantic import ValidationError

from app.tools.errors import ToolErrorCode
from app.tools.inspection import InspectionRequest, get_inspection_results


def test_get_inspection_by_serial(
    db,
    sample_serial,
    authorized_role,
):
    if sample_serial is None:
        return

    request = InspectionRequest(
        serial_number=sample_serial.serial_number,
        role=authorized_role,
    )

    result = get_inspection_results(db, request)

    assert result.success is True
    assert result.data is not None
    assert isinstance(result.data, list)

    if result.data:
        for item in result.data:
            assert item.serial_number == sample_serial.serial_number


def test_get_inspection_by_mo(
    db,
    sample_mo,
    authorized_role,
):
    if sample_mo is None:
        return

    request = InspectionRequest(
        mo_number=sample_mo.mo_number,
        role=authorized_role,
    )

    result = get_inspection_results(db, request)

    assert result.success is True
    assert result.data is not None
    assert isinstance(result.data, list)


def test_get_inspection_requires_identifier(
    db,
    authorized_role,
):
    with pytest.raises(ValidationError):
        InspectionRequest(
            role=authorized_role,
        )


def test_get_inspection_rejects_both_identifiers(
    db,
    sample_serial,
    sample_mo,
    authorized_role,
):
    if sample_serial is None or sample_mo is None:
        return

    with pytest.raises(ValidationError):
        InspectionRequest(
            serial_number=sample_serial.serial_number,
            mo_number=sample_mo.mo_number,
            role=authorized_role,
        )


def test_get_inspection_limit(
    db,
    sample_serial,
    authorized_role,
):
    if sample_serial is None:
        return

    with pytest.raises(ValidationError):
        InspectionRequest(
            serial_number=sample_serial.serial_number,
            limit=1001,
            role=authorized_role,
        )


def test_get_inspection_not_found(
    db,
    authorized_role,
):
    request = InspectionRequest(
        serial_number="SN-DOES-NOT-EXIST-999999",
        role=authorized_role,
    )

    result = get_inspection_results(db, request)

    assert result.success is True
    assert result.data == []
    assert result.evidence == []
    assert result.errors == []
    assert result.metadata.result_count == 0


def test_get_inspection_unauthorized(
    db,
    sample_serial,
    authorized_role,
    unauthorized_role,
):
    if sample_serial is None:
        return

    request = InspectionRequest(
        serial_number=sample_serial.serial_number,
        role=unauthorized_role,
    )

    result = get_inspection_results(db, request)

    assert result.success is False
    assert any(
        error.code == ToolErrorCode.TOOL_UNAUTHORIZED
        for error in result.errors
    )