from __future__ import annotations

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import models

from .authorization import authorize
from .common import ToolError, ToolMetadata, ToolResult
from .evidence import build_evidence
from .errors import ToolErrorCode
from .validation import validate_identifier


class NCRRequest(BaseModel):
    ncr_number: str = Field(min_length=1, max_length=30)
    role: str = "investigation_agent"


class NCRData(BaseModel):
    id: int
    ncr_number: str
    serial_unit_id: int | None
    serial_number: str | None
    lot_id: int | None
    mo_id: int
    inspection_id: int | None
    description: str | None
    severity: str | None
    status: str | None
    date_opened: str | None
    date_closed: str | None


def get_ncr(
    db: Session,
    request: NCRRequest,
) -> ToolResult[NCRData]:

    try:
        authorize(request.role, "get_ncr")

        ncr_number = validate_identifier(
            request.ncr_number,
            "ncr_number",
        )

        ncr = (
            db.query(models.NCR)
            .filter(models.NCR.ncr_number == ncr_number)
            .first()
        )

        if ncr is None:
            return ToolResult(
                success=False,
                errors=[
                    ToolError(
                        code=ToolErrorCode.RECORD_NOT_FOUND,
                        message=f"NCR '{ncr_number}' was not found.",
                    )
                ],
                metadata=ToolMetadata(
                    tool="get_ncr",
                    result_count=0,
                ),
            )

        evidence = build_evidence(
            source_type="ncr",
            source_id=ncr.ncr_number,
            table="ncrs",
            record_id=ncr.id,
            query_scope=f"get_ncr:ncr_number={ncr_number}",
        )

        data = NCRData(
            id=ncr.id,
            ncr_number=ncr.ncr_number,
            serial_unit_id=ncr.serial_unit_id,
            serial_number=(
                ncr.serial_unit.serial_number
                if ncr.serial_unit
                else None
            ),
            lot_id=ncr.lot_id,
            mo_id=ncr.mo_id,
            inspection_id=ncr.inspection_id,
            description=ncr.description,
            severity=ncr.severity,
            status=ncr.status,
            date_opened=(
                ncr.date_opened.isoformat()
                if ncr.date_opened
                else None
            ),
            date_closed=(
                ncr.date_closed.isoformat()
                if ncr.date_closed
                else None
            ),
)

        return ToolResult(
            success=True,
            data=data,
            evidence=[evidence],
            metadata=ToolMetadata(
                tool="get_ncr",
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
            metadata=ToolMetadata(tool="get_ncr"),
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
            metadata=ToolMetadata(tool="get_ncr"),
        )

    except Exception:
        return ToolResult(
            success=False,
            errors=[
                ToolError(
                    code=ToolErrorCode.DATABASE_QUERY_FAILED,
                    message="NCR lookup failed.",
                )
            ],
            metadata=ToolMetadata(tool="get_ncr"),
        )