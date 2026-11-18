from __future__ import annotations

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import models

from .authorization import authorize
from .common import ToolError, ToolMetadata, ToolResult
from .evidence import build_evidence
from .errors import ToolErrorCode
from .validation import validate_identifier, validate_limit


class HistoricalNCRRequest(BaseModel):
    product_code: str | None = None
    component_id: int | None = Field(default=None, ge=1)
    severity: str | None = Field(default=None, max_length=20)
    status: str | None = Field(default=None, max_length=20)
    search_text: str | None = Field(default=None, max_length=200)
    limit: int = Field(default=50, ge=1, le=50)
    role: str = "investigation_agent"


class HistoricalNCRData(BaseModel):
    id: int
    ncr_number: str
    product_code: str | None
    serial_number: str | None
    mo_number: str | None
    lot_id: int | None
    description: str | None
    severity: str | None
    status: str | None
    date_opened: str | None


def search_historical_ncrs(
    db: Session,
    request: HistoricalNCRRequest,
) -> ToolResult[list[HistoricalNCRData]]:

    try:
        authorize(
            request.role,
            "search_historical_ncrs",
        )

        limit = validate_limit(
            request.limit,
            maximum=50,
        )

        query = (
            db.query(models.NCR)
            .outerjoin(
                models.SerialUnit,
                models.NCR.serial_unit_id
                == models.SerialUnit.id,
            )
            .outerjoin(
                models.Product,
                models.SerialUnit.product_id
                == models.Product.id,
            )
        )

        if request.product_code:
            product_code = validate_identifier(
                request.product_code,
                "product_code",
            )

            query = query.filter(
                models.Product.product_code
                == product_code
            )

        if request.component_id is not None:
            query = (
                query.join(
                    models.Lot,
                    models.NCR.lot_id
                    == models.Lot.id,
                )
                .filter(
                    models.Lot.component_id
                    == request.component_id
                )
            )

        if request.severity:
            severity = request.severity.strip()

            query = query.filter(
                models.NCR.severity == severity
            )

        if request.status:
            status = request.status.strip()

            query = query.filter(
                models.NCR.status == status
            )

        if request.search_text:
            search_text = request.search_text.strip()

            if not search_text:
                raise ValueError(
                    "search_text cannot be empty."
                )

            pattern = f"%{search_text}%"

            query = query.filter(
                models.NCR.description.ilike(pattern)
            )

        rows = (
            query
            .order_by(
                models.NCR.date_opened.desc(),
                models.NCR.id.desc(),
            )
            .limit(limit)
            .all()
        )

        data = []
        evidence = []

        for row in rows:
            serial = row.serial_unit
            product = (
                serial.product
                if serial
                else None
            )

            data.append(
                HistoricalNCRData(
                    id=row.id,
                    ncr_number=row.ncr_number,
                    product_code=(
                        product.product_code
                        if product
                        else None
                    ),
                    serial_number=(
                        serial.serial_number
                        if serial
                        else None
                    ),
                    mo_number=(
                        row.mo.mo_number
                        if row.mo
                        else None
                    ),
                    lot_id=row.lot_id,
                    description=row.description,
                    severity=row.severity,
                    status=row.status,
                    date_opened=(
                        row.date_opened.isoformat()
                        if row.date_opened
                        else None
                    ),
                )
            )

            evidence.append(
                build_evidence(
                    source_type="historical_ncr",
                    source_id=row.ncr_number,
                    table="ncrs",
                    record_id=row.id,
                    query_scope="search_historical_ncrs",
                )
            )

        return ToolResult(
            success=True,
            data=data,
            evidence=evidence,
            metadata=ToolMetadata(
                tool="search_historical_ncrs",
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
                tool="search_historical_ncrs"
            ),
        )

    except Exception:
        return ToolResult(
            success=False,
            errors=[
                ToolError(
                    code=ToolErrorCode.DATABASE_QUERY_FAILED,
                    message="Historical NCR search failed.",
                )
            ],
            metadata=ToolMetadata(
                tool="search_historical_ncrs"
            ),
        )