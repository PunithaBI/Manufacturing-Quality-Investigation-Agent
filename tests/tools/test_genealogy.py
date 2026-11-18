from app.tools.genealogy import GenealogyRequest, get_serial_genealogy
from app.tools.errors import ToolErrorCode


def test_get_serial_genealogy_success(db, sample_serial, authorized_role):
    if sample_serial is None:
        return

    request = GenealogyRequest(
        serial_number=sample_serial.serial_number,
        role=authorized_role,
    )

    result = get_serial_genealogy(db, request)

    assert result.success is True
    assert result.data is not None
    assert result.data.serial_number == sample_serial.serial_number

    # Important: the current schema does not contain actual
    # component-consumption genealogy.
    assert result.data.lot_traceability_status.startswith(
        "NOT_AVAILABLE:"
    )


def test_get_serial_genealogy_not_found(db, authorized_role):
    request = GenealogyRequest(
        serial_number="SERIAL-DOES-NOT-EXIST-999999",
        role=authorized_role,
    )

    result = get_serial_genealogy(db, request)

    assert result.success is False
    assert any(
        error.code == ToolErrorCode.RECORD_NOT_FOUND
        for error in result.errors
    )


def test_get_serial_genealogy_unauthorized(
    db,
    sample_serial,
    unauthorized_role,
):
    if sample_serial is None:
        return

    request = GenealogyRequest(
        serial_number=sample_serial.serial_number,
        role=unauthorized_role,
    )

    result = get_serial_genealogy(db, request)

    assert result.success is False
    assert any(
        error.code == ToolErrorCode.TOOL_UNAUTHORIZED
        for error in result.errors
    )


def test_get_serial_genealogy_invalid_identifier(db, authorized_role):
    request = GenealogyRequest(
        serial_number="INVALID SERIAL!!!",
        role=authorized_role,
    )

    result = get_serial_genealogy(db, request)

    assert result.success is False
    assert any(
        error.code == ToolErrorCode.INVALID_INPUT
        for error in result.errors
    )