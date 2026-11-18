from __future__ import annotations

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import models

from .authorization import authorize
from .common import ToolError, ToolMetadata, ToolResult
from .evidence import build_evidence
from .errors import ToolErrorCode
from .validation import validate_identifier, validate_limit


class BOMRequest(BaseModel):
    product_code: str = Field(min_length=1, max_length=30)
    revision: str | None = Field(default=None, max_length=10)
    limit: int = Field(default=500, ge=1, le=500)
    role: str = "investigation_agent"


class BOMItemData(BaseModel):
    bom_id: int
    product_code: str
    component_code: str
    component_name: str
    quantity_per_unit: float
    bom_revision: str | None


def get_bom(
    db: Session,
    request: BOMRequest,
) -> ToolResult[list[BOMItemData]]:

    try:
        authorize(request.role, "get_bom")

        product_code = validate_identifier(
            request.product_code,
            "product_code",
        )

        limit = validate_limit(
            request.limit,
            maximum=500,
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
                metadata=ToolMetadata(tool="get_bom"),
            )

        query = (
            db.query(models.BOM)
            .filter(models.BOM.product_id == product.id)
        )

        if request.revision:
            revision = validate_identifier(
                request.revision,
                "revision",
                max_length=10,
            )
            query = query.filter(
                models.BOM.bom_revision == revision
            )

        rows = (
            query
            .order_by(models.BOM.id)
            .limit(limit)
            .all()
        )

        data = []

        for row in rows:
            if row.component is None:
                return ToolResult(
                    success=False,
                    errors=[
                        ToolError(
                            code=ToolErrorCode.PROVENANCE_UNAVAILABLE,
                            message=(
                                f"BOM record {row.id} references a missing "
                                "component."
                            ),
                        )
                    ],
                    metadata=ToolMetadata(tool="get_bom"),
                )

            data.append(
                BOMItemData(
                    bom_id=row.id,
                    product_code=product.product_code,
                    component_code=row.component.component_code,
                    component_name=row.component.name,
                    quantity_per_unit=row.quantity_per_unit,
                    bom_revision=row.bom_revision,
                )
            )

        evidence = [
            build_evidence(
                source_type="bom",
                source_id=str(row.id),
                table="bom",
                record_id=row.id,
                query_scope=(
                    f"get_bom:product_code={product_code}"
                ),
            )
            for row in rows
        ]

        return ToolResult(
            success=True,
            data=data,
            evidence=evidence,
            metadata=ToolMetadata(
                tool="get_bom",
                result_count=len(data),
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
            metadata=ToolMetadata(tool="get_bom"),
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
            metadata=ToolMetadata(tool="get_bom"),
        )

    except Exception:
        return ToolResult(
            success=False,
            errors=[
                ToolError(
                    code=ToolErrorCode.DATABASE_QUERY_FAILED,
                    message="BOM lookup failed.",
                )
            ],
            metadata=ToolMetadata(tool="get_bom"),
        )