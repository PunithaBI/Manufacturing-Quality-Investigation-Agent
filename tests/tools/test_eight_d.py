import pytest
from pydantic import ValidationError

from app.tools.eight_d import EightDRequest, get_8d
from app.tools.errors import ToolErrorCode


def test_get_8d_by_ncr(
    db,
    sample_8d,
    authorized_role,
):
    if sample_8d is None:
        return

    assert sample_8d.ncr is not None

    request = EightDRequest(
        ncr_number=sample_8d.ncr.ncr_number,
        role=authorized_role,
    )

    result = get_8d(db, request)

    assert result.success is True
    assert result.data is not None
    assert isinstance(result.data, list)

    assert len(result.data) >= 1
    assert len(result.data) <= 20

    assert result.evidence

    for evidence in result.evidence:
        assert evidence.source_type == "eight_d"
        assert evidence.provenance.table == "eight_d_reports"


def test_get_8d_by_report_number(
    db,
    sample_8d,
    authorized_role,
):
    if sample_8d is None:
        return

    request = EightDRequest(
        report_number=sample_8d.report_number,
        role=authorized_role,
    )

    result = get_8d(db, request)

    assert result.success is True
    assert result.data is not None
    assert isinstance(result.data, list)
    assert len(result.data) >= 1


def test_get_8d_requires_ncr_or_report(
    db,
    authorized_role,
):
    with pytest.raises(ValidationError):
        EightDRequest(
            role=authorized_role,
        )


def test_get_8d_rejects_both_identifiers(
    db,
    sample_8d,
    authorized_role,
):
    if sample_8d is None or sample_8d.ncr is None:
        return

    with pytest.raises(ValidationError):
        EightDRequest(
            ncr_number=sample_8d.ncr.ncr_number,
            report_number=sample_8d.report_number,
            role=authorized_role,
        )


def test_get_8d_not_found(
    db,
    authorized_role,
):
    request = EightDRequest(
        ncr_number="NCR-DOES-NOT-EXIST-999999",
        role=authorized_role,
    )

    result = get_8d(db, request)

    assert result.success is False
    assert any(
        error.code == ToolErrorCode.RECORD_NOT_FOUND
        for error in result.errors
    )


def test_get_8d_unauthorized(
    db,
    sample_8d,
    unauthorized_role,
):
    if sample_8d is None or sample_8d.ncr is None:
        return

    request = EightDRequest(
        ncr_number=sample_8d.ncr.ncr_number,
        role=unauthorized_role,
    )

    result = get_8d(db, request)

    assert result.success is False
    assert any(
        error.code == ToolErrorCode.TOOL_UNAUTHORIZED
        for error in result.errors
    )

