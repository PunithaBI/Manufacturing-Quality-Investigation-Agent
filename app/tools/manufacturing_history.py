from __future__ import annotations

from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.db import models

from .authorization import authorize
from .common import ToolError, ToolMetadata, ToolResult
from .evidence import build_evidence
from .errors import ToolErrorCode
from .validation import validate_identifier, validate_limit


class ManufacturingHistoryRequest(BaseModel):
    serial_number: str | None = None
    mo_number: str | None = None
    limit: int = Field(default=500, ge=1, le=1000)
    role: str = "investigation_agent"

    @model_validator(mode="after")
    def require_identifier(self):
        if not self.serial_number and not self.mo_number:
            raise ValueError(
                "Either serial_number or mo_number is required."
            )
        if self.serial_number and self.mo_number:
            raise ValueError(
                "Provide serial_number or mo_number, not both."
            )
        return self


class ManufacturingHistoryData(BaseModel):
    mo_number: str
    product_code: str
    quantity_planned: int
    quantity_completed: int
    status: str | None
    operations: list[dict]


def get_manufacturing_history(
    db: Session,
    request: ManufacturingHistoryRequest,
) -> ToolResult[list[ManufacturingHistoryData]]:

    try:
        authorize(request.role, "get_manufacturing_history")

        limit = validate_limit(
            request.limit,
            maximum=1000,
        )

        if request.serial_number:
            identifier = validate_identifier(
                request.serial_number,
                "serial_number",
            )

            serial = (
                db.query(models.SerialUnit)
                .filter(
                    models.SerialUnit.serial_number == identifier
                )
                .first()
            )

            if serial is None:
                return ToolResult(
                    success=False,
                    errors=[
                        ToolError(
                            code=ToolErrorCode.RECORD_NOT_FOUND,
                            message=f"Serial '{identifier}' was not found.",
                        )
                    ],
                    metadata=ToolMetadata(
                        tool="get_manufacturing_history"
                    ),
                )

            orders = [serial.mo]

        else:
            identifier = validate_identifier(
                request.mo_number,
                "mo_number",
            )

            orders = (
                db.query(models.ManufacturingOrder)
                .filter(
                    models.ManufacturingOrder.mo_number == identifier
                )
                .limit(limit)
                .all()
            )

        if not orders or orders[0] is None:
            return ToolResult(
                success=False,
                errors=[
                    ToolError(
                        code=ToolErrorCode.RECORD_NOT_FOUND,
                        message="Manufacturing history was not found.",
                    )
                ],
                metadata=ToolMetadata(
                    tool="get_manufacturing_history"
                ),
            )

        data = []
        evidence = []

        for mo in orders[:limit]:
            if mo.product is None:
                return ToolResult(
                    success=False,
                    errors=[
                        ToolError(
                            code=ToolErrorCode.PROVENANCE_UNAVAILABLE,
                            message=(
                                f"Manufacturing order {mo.mo_number} "
                                "has no product relationship."
                            ),
                        )
                    ],
                    metadata=ToolMetadata(
                        tool="get_manufacturing_history"
                    ),
                )

            operations = [
                {
                    "operation_id": operation.id,
                    "sequence": operation.operation_seq,
                    "name": operation.operation_name,
                    "work_center": operation.work_center,
                    "operator": operation.operator,
                    "status": operation.status,
                    "start_time": (
                        operation.start_time.isoformat()
                        if operation.start_time
                        else None
                    ),
                    "end_time": (
                        operation.end_time.isoformat()
                        if operation.end_time
                        else None
                    ),
                }
                for operation in mo.operations
            ]

            data.append(
                ManufacturingHistoryData(
                    mo_number=mo.mo_number,
                    product_code=mo.product.product_code,
                    quantity_planned=mo.quantity_planned,
                    quantity_completed=mo.quantity_completed,
                    status=mo.status,
                    operations=operations,
                )
            )

            evidence.append(
                build_evidence(
                    source_type="manufacturing_order",
                    source_id=mo.mo_number,
                    table="manufacturing_orders",
                    record_id=mo.id,
                    query_scope=(
                        f"get_manufacturing_history:"
                        f"{'serial_number' if request.serial_number else 'mo_number'}"
                        f"={identifier}"
                    ),
                )
            )

        return ToolResult(
            success=True,
            data=data,
            evidence=evidence,
            metadata=ToolMetadata(
                tool="get_manufacturing_history",
                result_count=len(data),
            ),
        )

    except (PermissionError, ValueError) as exc:
        return ToolResult(
            success=False,
            errors=[
                ToolError(
                    code=(
                        ToolErrorCode.TOOL_UNAUTHORIZED
                        if isinstance(exc, PermissionError)
                        else ToolErrorCode.INVALID_INPUT
                    ),
                    message=str(exc),
                )
            ],
            metadata=ToolMetadata(
                tool="get_manufacturing_history"
            ),
        )

    except Exception:
        return ToolResult(
            success=False,
            errors=[
                ToolError(
                    code=ToolErrorCode.DATABASE_QUERY_FAILED,
                    message="Manufacturing history lookup failed.",
                )
            ],
            metadata=ToolMetadata(
                tool="get_manufacturing_history"
            ),
        )