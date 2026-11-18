from __future__ import annotations

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import models

from .authorization import authorize
from .common import ToolError, ToolMetadata, ToolResult
from .evidence import build_evidence
from .errors import ToolErrorCode
from .validation import validate_identifier, validate_limit


class ProcessMeasurementRequest(BaseModel):
    serial_number: str = Field(min_length=1, max_length=40)
    parameter_name: str | None = Field(default=None, max_length=80)
    limit: int = Field(default=1000, ge=1, le=1000)
    role: str = "investigation_agent"


class ProcessMeasurementData(BaseModel):
    measurement_id: int
    operation_id: int
    parameter_name: str
    nominal_value: float | None
    actual_value: float | None
    unit: str | None
    lsl: float | None
    usl: float | None
    in_spec: bool | None
    measured_at: str | None


def get_process_measurements(
    db: Session,
    request: ProcessMeasurementRequest,
) -> ToolResult[list[ProcessMeasurementData]]:

    try:
        authorize(request.role, "get_process_measurements")

        serial_number = validate_identifier(
            request.serial_number,
            "serial_number",
        )

        limit = validate_limit(
            request.limit,
            maximum=1000,
        )

        query = (
            db.query(models.ProcessMeasurement)
            .join(models.SerialUnit)
            .filter(
                models.SerialUnit.serial_number
                == serial_number
            )
        )

        if request.parameter_name:
            parameter_name = request.parameter_name.strip()

            if not parameter_name:
                raise ValueError(
                    "parameter_name cannot be empty."
                )

            query = query.filter(
                models.ProcessMeasurement.parameter_name
                == parameter_name
            )

        rows = (
            query
            .order_by(models.ProcessMeasurement.id)
            .limit(limit)
            .all()
        )

        data = []
        evidence = []

        for row in rows:
            data.append(
                ProcessMeasurementData(
                    measurement_id=row.id,
                    operation_id=row.operation_id,
                    parameter_name=row.parameter_name,
                    nominal_value=row.nominal_value,
                    actual_value=row.actual_value,
                    unit=row.unit,
                    lsl=row.lsl,
                    usl=row.usl,
                    in_spec=row.in_spec,
                    measured_at=(
                        row.measured_at.isoformat()
                        if row.measured_at
                        else None
                    ),
                )
            )

            evidence.append(
                build_evidence(
                    source_type="process_measurement",
                    source_id=str(row.id),
                    table="process_measurements",
                    record_id=row.id,
                    query_scope=(
                        "get_process_measurements:"
                        f"serial_number={serial_number}"
                    ),
                )
            )

        return ToolResult(
            success=True,
            data=data,
            evidence=evidence,
            metadata=ToolMetadata(
                tool="get_process_measurements",
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
                tool="get_process_measurements"
            ),
        )

    except Exception:
        return ToolResult(
            success=False,
            errors=[
                ToolError(
                    code=ToolErrorCode.DATABASE_QUERY_FAILED,
                    message="Process measurement lookup failed.",
                )
            ],
            metadata=ToolMetadata(
                tool="get_process_measurements"
            ),
        )