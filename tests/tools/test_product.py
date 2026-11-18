from app.tools.product import ProductRequest, get_product
from app.tools.errors import ToolErrorCode


def test_get_product_success(db, sample_product, authorized_role):
    if sample_product is None:
        return

    request = ProductRequest(
        product_code=sample_product.product_code,
        role=authorized_role,
    )

    result = get_product(db, request)

    assert result.success is True
    assert result.data is not None
    assert result.data.product_code == sample_product.product_code

    assert result.evidence
    assert result.evidence[0].source_type == "product"
    assert result.evidence[0].source_id == sample_product.product_code
    assert result.evidence[0].provenance.table == "products"
    assert result.evidence[0].provenance.record_id == sample_product.id


def test_get_product_not_found(db, authorized_role):
    request = ProductRequest(
        product_code="PRODUCT-DOES-NOT-EXIST-999999",
        role=authorized_role,
    )

    result = get_product(db, request)

    assert result.success is False
    assert any(
        error.code == ToolErrorCode.RECORD_NOT_FOUND
        for error in result.errors
    )


def test_get_product_unauthorized(db, sample_product, unauthorized_role):
    if sample_product is None:
        return

    request = ProductRequest(
        product_code=sample_product.product_code,
        role=unauthorized_role,
    )

    result = get_product(db, request)

    assert result.success is False
    assert any(
        error.code == ToolErrorCode.TOOL_UNAUTHORIZED
        for error in result.errors
    )


def test_get_product_invalid_identifier(db, authorized_role):
    request = ProductRequest(
        product_code="INVALID PRODUCT!!!",
        role=authorized_role,
    )

    result = get_product(db, request)

    assert result.success is False
    assert any(
        error.code == ToolErrorCode.INVALID_INPUT
        for error in result.errors
    )