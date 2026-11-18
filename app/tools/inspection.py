from __future__ import annotations

from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.db import models

from .authorization import authorize
from .common import ToolError, ToolMetadata, ToolResult
from .evidence import build_evidence
from .errors import ToolErrorCode
from .validation import validate_identifier, validate_limit


class InspectionRequest(BaseModel):
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


class InspectionData(BaseModel):
    inspection_id: int
    serial_number: str | None
    mo_number: str | None
    inspection_type: str | None
    inspector: str | None
    inspection_date: str | None
    result: str | None


def get_inspection_results(
    db: Session,
    request: InspectionRequest,
) -> ToolResult[list[InspectionData]]:

    try:
        authorize(request.role, "get_inspection_results")

        limit = validate_limit(
            request.limit,
            maximum=1000,
        )

        query = db.query(models.Inspection)

        if request.serial_number:
            serial_number = validate_identifier(
                request.serial_number,
                "serial_number",
            )

            query = (
                query.join(models.SerialUnit)
                .filter(
                    models.SerialUnit.serial_number
                    == serial_number
                )
            )

            scope = f"serial_number={serial_number}"

        else:
            mo_number = validate_identifier(
                request.mo_number,
                "mo_number",
            )

            query = (
                query.join(models.ManufacturingOrder)
                .filter(
                    models.ManufacturingOrder.mo_number
                    == mo_number
                )
            )

            scope = f"mo_number={mo_number}"

        rows = (
            query
            .order_by(models.Inspection.id)
            .limit(limit)
            .all()
        )

        data = []
        evidence = []

        for row in rows:
            data.append(
                InspectionData(
                    inspection_id=row.id,
                    serial_number=(
                        row.serial_unit.serial_number
                        if row.serial_unit
                        else None
                    ),
                    mo_number=(
                        row.mo.mo_number
                        if row.mo
                        else None
                    ),
                    inspection_type=row.inspection_type,
                    inspector=row.inspector,
                    inspection_date=(
                        row.inspection_date.isoformat()
                        if row.inspection_date
                        else None
                    ),
                    result=row.result,
                )
            )

            evidence.append(
                build_evidence(
                    source_type="inspection",
                    source_id=str(row.id),
                    table="inspections",
                    record_id=row.id,
                    query_scope=(
                        f"get_inspection_results:{scope}"
                    ),
                )
            )

        return ToolResult(
            success=True,
            data=data,
            evidence=evidence,
            metadata=ToolMetadata(
                tool="get_inspection_results",
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
                tool="get_inspection_results"
            ),
        )

    except Exception:
        return ToolResult(
            success=False,
            errors=[
                ToolError(
                    code=ToolErrorCode.DATABASE_QUERY_FAILED,
                    message="Inspection lookup failed.",
                )
            ],
            metadata=ToolMetadata(
                tool="get_inspection_results"
            ),
        )