import pytest
from pydantic import ValidationError

from app.tools.errors import ToolErrorCode
from app.tools.process_measurements import (
    ProcessMeasurementRequest,
    get_process_measurements,
)


def test_get_process_measurements_success(
    db,
    sample_serial,
    authorized_role,
):
    if sample_serial is None:
        return

    request = ProcessMeasurementRequest(
        serial_number=sample_serial.serial_number,
        role=authorized_role,
    )

    result = get_process_measurements(db, request)

    assert result.success is True
    assert result.data is not None
    assert isinstance(result.data, list)

    if result.data:
        for item in result.data:
            assert item.measurement_id is not None
            assert item.operation_id is not None
            assert item.parameter_name


def test_get_process_measurements_not_found(
    db,
    authorized_role,
):
    request = ProcessMeasurementRequest(
        serial_number="SN-DOES-NOT-EXIST-999999",
        role=authorized_role,
    )

    result = get_process_measurements(db, request)

    assert result.success is True
    assert result.data == []
    assert result.evidence == []
    assert result.errors == []
    assert result.metadata.result_count == 0


def test_get_process_measurements_limit(
    db,
    sample_serial,
    authorized_role,
):
    if sample_serial is None:
        return

    with pytest.raises(ValidationError):
        ProcessMeasurementRequest(
            serial_number=sample_serial.serial_number,
            limit=1001,
            role=authorized_role,
        )


def test_get_process_measurements_unauthorized(
    db,
    sample_serial,
    unauthorized_role,
):
    if sample_serial is None:
        return

    request = ProcessMeasurementRequest(
        serial_number=sample_serial.serial_number,
        role=unauthorized_role,
    )

    result = get_process_measurements(db, request)

    assert result.success is False
    assert any(
        error.code == ToolErrorCode.TOOL_UNAUTHORIZED
        for error in result.errors
    )