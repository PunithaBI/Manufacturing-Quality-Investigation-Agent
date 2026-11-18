from __future__ import annotations

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import models

from .authorization import authorize
from .common import ToolError, ToolMetadata, ToolResult
from .evidence import build_evidence
from .errors import ToolErrorCode
from .validation import validate_identifier


class GenealogyRequest(BaseModel):
    serial_number: str = Field(min_length=1, max_length=40)
    role: str = "investigation_agent"


class GenealogyData(BaseModel):
    serial_number: str
    product_code: str
    manufacturing_order: str
    status: str | None
    operations: list[dict]
    process_measurements: list[dict]
    inspections: list[dict]
    ncrs: list[dict]
    bom_components: list[dict]
    lot_traceability_status: str


def get_serial_genealogy(
    db: Session,
    request: GenealogyRequest,
) -> ToolResult[GenealogyData]:

    try:
        authorize(request.role, "get_serial_genealogy")

        serial_number = validate_identifier(
            request.serial_number,
            "serial_number",
        )

        serial = (
            db.query(models.SerialUnit)
            .filter(
                models.SerialUnit.serial_number == serial_number
            )
            .first()
        )

        if serial is None:
            return ToolResult(
                success=False,
                errors=[
                    ToolError(
                        code=ToolErrorCode.RECORD_NOT_FOUND,
                        message=(
                            f"Serial unit '{serial_number}' "
                            "was not found."
                        ),
                    )
                ],
                metadata=ToolMetadata(
                    tool="get_serial_genealogy"
                ),
            )

        if serial.product is None or serial.mo is None:
            return ToolResult(
                success=False,
                errors=[
                    ToolError(
                        code=ToolErrorCode.PROVENANCE_UNAVAILABLE,
                        message=(
                            "Serial unit is missing required "
                            "product or manufacturing-order relationship."
                        ),
                    )
                ],
                metadata=ToolMetadata(
                    tool="get_serial_genealogy"
                ),
            )

        product = serial.product
        mo = serial.mo

        bom_rows = (
            db.query(models.BOM)
            .filter(models.BOM.product_id == product.id)
            .all()
        )

        operations = [
            {
                "operation_id": operation.id,
                "sequence": operation.operation_seq,
                "name": operation.operation_name,
                "work_center": operation.work_center,
                "status": operation.status,
            }
            for operation in mo.operations
        ]

        measurements = [
            {
                "measurement_id": measurement.id,
                "operation_id": measurement.operation_id,
                "parameter": measurement.parameter_name,
                "nominal": measurement.nominal_value,
                "actual": measurement.actual_value,
                "unit": measurement.unit,
                "lsl": measurement.lsl,
                "usl": measurement.usl,
                "in_spec": measurement.in_spec,
                "measured_at": (
                    measurement.measured_at.isoformat()
                    if measurement.measured_at
                    else None
                ),
            }
            for measurement in serial.process_measurements
        ]

        inspections = [
            {
                "inspection_id": inspection.id,
                "type": inspection.inspection_type,
                "result": inspection.result,
                "inspector": inspection.inspector,
                "date": (
                    inspection.inspection_date.isoformat()
                    if inspection.inspection_date
                    else None
                ),
            }
            for inspection in serial.inspections
        ]

        ncrs = [
            {
                "ncr_id": ncr.id,
                "ncr_number": ncr.ncr_number,
                "severity": ncr.severity,
                "status": ncr.status,
            }
            for ncr in serial.ncrs
        ]

        bom_components = [
            {
                "bom_id": row.id,
                "component_code": (
                    row.component.component_code
                    if row.component
                    else None
                ),
                "quantity_per_unit": row.quantity_per_unit,
            }
            for row in bom_rows
        ]

        evidence = [
            build_evidence(
                source_type="serial_unit",
                source_id=serial.serial_number,
                table="serial_units",
                record_id=serial.id,
                query_scope=(
                    f"get_serial_genealogy:"
                    f"serial_number={serial_number}"
                ),
            )
        ]

        return ToolResult(
            success=True,
            data=GenealogyData(
                serial_number=serial.serial_number,
                product_code=product.product_code,
                manufacturing_order=mo.mo_number,
                status=serial.status,
                operations=operations,
                process_measurements=measurements,
                inspections=inspections,
                ncrs=ncrs,
                bom_components=bom_components,
                lot_traceability_status=(
                    "NOT_AVAILABLE: current schema does not contain "
                    "serial/MO-to-lot consumption records"
                ),
            ),
            evidence=evidence,
            metadata=ToolMetadata(
                tool="get_serial_genealogy",
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
            metadata=ToolMetadata(
                tool="get_serial_genealogy"
            ),
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
            metadata=ToolMetadata(
                tool="get_serial_genealogy"
            ),
        )

    except Exception:
        return ToolResult(
            success=False,
            errors=[
                ToolError(
                    code=ToolErrorCode.DATABASE_QUERY_FAILED,
                    message="Serial genealogy lookup failed.",
                )
            ],
            metadata=ToolMetadata(
                tool="get_serial_genealogy"
            ),
        )