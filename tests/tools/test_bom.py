import pytest
from pydantic import ValidationError

from app.tools.bom import BOMRequest, get_bom
from app.tools.errors import ToolErrorCode


def test_get_bom_success(db, sample_product, authorized_role):
    if sample_product is None:
        return

    request = BOMRequest(
        product_code=sample_product.product_code,
        role=authorized_role,
    )

    result = get_bom(db, request)

    assert result.success is True
    assert result.data is not None
    assert isinstance(result.data, list)

    if result.data:
        assert result.evidence

        for item in result.data:
            assert item.product_code == sample_product.product_code

        for evidence in result.evidence:
            assert evidence.source_type == "bom"
            assert evidence.provenance.table == "bom"


def test_get_bom_not_found(db, authorized_role):
    request = BOMRequest(
        product_code="PRODUCT-DOES-NOT-EXIST-999999",
        role=authorized_role,
    )

    result = get_bom(db, request)

    assert result.success is False
    assert any(
        error.code == ToolErrorCode.RECORD_NOT_FOUND
        for error in result.errors
    )


def test_get_bom_limit_rejected(db, sample_product, authorized_role):
    if sample_product is None:
        return

    with pytest.raises(ValidationError):
        BOMRequest(
            product_code=sample_product.product_code,
            limit=501,
            role=authorized_role,
        )


def test_get_bom_unauthorized(db, sample_product, unauthorized_role):
    if sample_product is None:
        return

    request = BOMRequest(
        product_code=sample_product.product_code,
        role=unauthorized_role,
    )

    result = get_bom(db, request)

    assert result.success is False
    assert any(
        error.code == ToolErrorCode.TOOL_UNAUTHORIZED
        for error in result.errors
    )
