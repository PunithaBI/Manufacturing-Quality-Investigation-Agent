from app.tools.ncr import NCRRequest, get_ncr
from app.tools.errors import ToolErrorCode


def test_get_ncr_success(db, sample_ncr, authorized_role):
    if sample_ncr is None:
        return

    request = NCRRequest(
        ncr_number=sample_ncr.ncr_number,
        role=authorized_role,
    )

    result = get_ncr(db, request)

    assert result.success is True
    assert result.data is not None
    assert result.data.ncr_number == sample_ncr.ncr_number

    assert result.evidence
    assert result.evidence[0].source_type == "ncr"
    assert result.evidence[0].source_id == sample_ncr.ncr_number
    assert result.evidence[0].provenance.table == "ncrs"
    assert result.evidence[0].provenance.record_id == sample_ncr.id


def test_get_ncr_not_found(db, authorized_role):
    request = NCRRequest(
        ncr_number="NCR-DOES-NOT-EXIST-999999",
        role=authorized_role,
    )

    result = get_ncr(db, request)

    assert result.success is False
    assert any(
        error.code == ToolErrorCode.RECORD_NOT_FOUND
        for error in result.errors
    )


def test_get_ncr_unauthorized(db, sample_ncr, unauthorized_role):
    if sample_ncr is None:
        return

    request = NCRRequest(
        ncr_number=sample_ncr.ncr_number,
        role=unauthorized_role,
    )

    result = get_ncr(db, request)

    assert result.success is False
    assert any(
        error.code == ToolErrorCode.TOOL_UNAUTHORIZED
        for error in result.errors
    )


def test_get_ncr_invalid_identifier(db, authorized_role):
    request = NCRRequest(
        ncr_number="INVALID NCR VALUE!!!",
        role=authorized_role,
    )

    result = get_ncr(db, request)

    assert result.success is False
    assert any(
        error.code == ToolErrorCode.INVALID_INPUT
        for error in result.errors
    )