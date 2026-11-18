import pytest
from pydantic import ValidationError

from app.tools.historical_ncr import (
    HistoricalNCRRequest,
    search_historical_ncrs,
)
from app.tools.errors import ToolErrorCode


def test_search_historical_ncrs_success(
    db,
    authorized_role,
):
    request = HistoricalNCRRequest(
        limit=50,
        role=authorized_role,
    )

    result = search_historical_ncrs(db, request)

    assert result.success is True
    assert result.data is not None
    assert isinstance(result.data, list)

    assert len(result.data) <= 50

    if result.data:
        assert result.evidence

        for evidence in result.evidence:
            assert evidence.source_type == "historical_ncr"
            assert evidence.provenance.table == "ncrs"


def test_search_historical_ncrs_limit_51_rejected(
    db,
    authorized_role,
):
    with pytest.raises(ValidationError):
        HistoricalNCRRequest(
            limit=51,
            role=authorized_role,
        )


def test_search_historical_ncrs_zero_limit_rejected(
    db,
    authorized_role,
):
    with pytest.raises(ValidationError):
        HistoricalNCRRequest(
            limit=0,
            role=authorized_role,
        )


def test_search_historical_ncrs_unauthorized(
    db,
    unauthorized_role,
):
    request = HistoricalNCRRequest(
        limit=50,
        role=unauthorized_role,
    )

    result = search_historical_ncrs(db, request)

    assert result.success is False
    assert any(
        error.code == ToolErrorCode.TOOL_UNAUTHORIZED
        for error in result.errors
    )


def test_search_historical_ncrs_by_product(
    db,
    sample_product,
    authorized_role,
):
    if sample_product is None:
        return

    request = HistoricalNCRRequest(
        product_code=sample_product.product_code,
        limit=50,
        role=authorized_role,
    )

    result = search_historical_ncrs(db, request)

    assert result.success is True
    assert result.data is not None

    for item in result.data:
        assert item.product_code == sample_product.product_code

