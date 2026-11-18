from __future__ import annotations

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import models

from .authorization import authorize
from .common import ToolError, ToolMetadata, ToolResult
from .evidence import build_evidence
from .errors import ToolErrorCode
from .validation import validate_identifier


class ProductRequest(BaseModel):
    product_code: str = Field(min_length=1, max_length=30)
    role: str = "investigation_agent"


class ProductData(BaseModel):
    id: int
    product_code: str
    name: str
    description: str | None
    revision: str | None


def get_product(
    db: Session,
    request: ProductRequest,
) -> ToolResult[ProductData]:

    try:
        authorize(request.role, "get_product")

        product_code = validate_identifier(
            request.product_code,
            "product_code",
        )

        product = (
            db.query(models.Product)
            .filter(models.Product.product_code == product_code)
            .first()
        )

        if product is None:
            return ToolResult(
                success=False,
                errors=[
                    ToolError(
                        code=ToolErrorCode.RECORD_NOT_FOUND,
                        message=f"Product '{product_code}' was not found.",
                    )
                ],
                metadata=ToolMetadata(
                    tool="get_product",
                ),
            )

        evidence = build_evidence(
            source_type="product",
            source_id=product.product_code,
            table="products",
            record_id=product.id,
            query_scope=f"get_product:product_code={product_code}",
        )

        data = ProductData(
            id=product.id,
            product_code=product.product_code,
            name=product.name,
            description=product.description,
            revision=product.revision,
        )

        return ToolResult(
            success=True,
            data=data,
            evidence=[evidence],
            metadata=ToolMetadata(
                tool="get_product",
                result_count=1,
            ),
        )

    except PermissionError as exc:
        return ToolResult(
            success=False,
            errors=[
                ToolError(
                    code=ToolErrorCode.TOOL_UNAUTHORIZED,
                    message=str(exc),
                )
            ],
            metadata=ToolMetadata(tool="get_product"),
        )

    except ValueError as exc:
        return ToolResult(
            success=False,
            errors=[
                ToolError(
                    code=ToolErrorCode.INVALID_INPUT,
                    message=str(exc),
                )
            ],
            metadata=ToolMetadata(tool="get_product"),
        )

    except Exception:
        return ToolResult(
            success=False,
            errors=[
                ToolError(
                    code=ToolErrorCode.DATABASE_QUERY_FAILED,
                    message="Product lookup failed.",
                )
            ],
            metadata=ToolMetadata(tool="get_product"),
        )