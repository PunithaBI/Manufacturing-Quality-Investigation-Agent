from __future__ import annotations

from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.db import models

from .authorization import authorize
from .common import ToolError, ToolMetadata, ToolResult
from .evidence import build_evidence
from .errors import ToolErrorCode
from .validation import validate_identifier


MAX_8D_RECORDS = 20


class EightDRequest(BaseModel):
    ncr_number: str | None = Field(
        default=None,
        max_length=30,
    )
    report_number: str | None = Field(
        default=None,
        max_length=30,
    )
    role: str = "investigation_agent"

    @model_validator(mode="after")
    def require_one_identifier(self):
        if not self.ncr_number and not self.report_number:
            raise ValueError(
                "Either ncr_number or report_number is required."
            )

        if self.ncr_number and self.report_number:
            raise ValueError(
                "Provide ncr_number or report_number, not both."
            )

        return self


class EightDData(BaseModel):
    id: int
    report_number: str
    ncr_number: str
    d1_team: str | None
    d2_problem_description: str | None
    d3_containment_action: str | None
    d4_root_cause: str | None
    d5_corrective_action: str | None
    d6_implementation: str | None
    d7_prevention: str | None
    d8_closure: str | None
    status: str | None
    rca: list[dict]
    capa: list[dict]


def get_8d(
    db: Session,
    request: EightDRequest,
) -> ToolResult[list[EightDData]]:

    try:
        authorize(request.role, "get_8d")

        query = db.query(models.EightDReport)

        if request.ncr_number:
            ncr_number = validate_identifier(
                request.ncr_number,
                "ncr_number",
            )

            query = (
                query.join(models.NCR)
                .filter(
                    models.NCR.ncr_number
                    == ncr_number
                )
            )

            scope = f"ncr_number={ncr_number}"

        else:
            report_number = validate_identifier(
                request.report_number,
                "report_number",
            )

            query = query.filter(
                models.EightDReport.report_number
                == report_number
            )

            scope = f"report_number={report_number}"

        rows = (
            query
            .order_by(models.EightDReport.id)
            .limit(MAX_8D_RECORDS + 1)
            .all()
        )

        if len(rows) > MAX_8D_RECORDS:
            return ToolResult(
                success=False,
                errors=[
                    ToolError(
                        code=ToolErrorCode.TOOL_LIMIT_EXCEEDED,
                        message=(
                            f"More than {MAX_8D_RECORDS} 8D reports "
                            "matched the request."
                        ),
                    )
                ],
                metadata=ToolMetadata(
                    tool="get_8d"
                ),
            )

        if not rows:
            return ToolResult(
                success=False,
                errors=[
                    ToolError(
                        code=ToolErrorCode.RECORD_NOT_FOUND,
                        message=(
                            "No 8D report was found for the "
                            "requested identifier."
                        ),
                    )
                ],
                metadata=ToolMetadata(
                    tool="get_8d"
                ),
            )

        data = []
        evidence = []

        for row in rows:

            if row.ncr is None:
                return ToolResult(
                    success=False,
                    errors=[
                        ToolError(
                            code=ToolErrorCode.PROVENANCE_UNAVAILABLE,
                            message=(
                                f"8D report {row.report_number} "
                                "has no NCR relationship."
                            ),
                        )
                    ],
                    metadata=ToolMetadata(
                        tool="get_8d"
                    ),
                )

            rca_data = [
                {
                    "rca_id": rca.id,
                    "method": rca.method,
                    "root_cause_description": (
                        rca.root_cause_description
                    ),
                    "contributing_factors": (
                        rca.contributing_factors
                    ),
                    "date_completed": (
                        rca.date_completed.isoformat()
                        if rca.date_completed
                        else None
                    ),
                }
                for rca in row.rcas
            ]

            capa_data = [
                {
                    "capa_id": capa.id,
                    "capa_number": capa.capa_number,
                    "corrective_action": capa.corrective_action,
                    "preventive_action": capa.preventive_action,
                    "owner": capa.owner,
                    "due_date": (
                        capa.due_date.isoformat()
                        if capa.due_date
                        else None
                    ),
                    "status": capa.status,
                    "effectiveness_check": (
                        capa.effectiveness_check
                    ),
                }
                for capa in row.capas
            ]

            data.append(
                EightDData(
                    id=row.id,
                    report_number=row.report_number,
                    ncr_number=row.ncr.ncr_number,
                    d1_team=row.d1_team,
                    d2_problem_description=(
                        row.d2_problem_description
                    ),
                    d3_containment_action=(
                        row.d3_containment_action
                    ),
                    d4_root_cause=row.d4_root_cause,
                    d5_corrective_action=(
                        row.d5_corrective_action
                    ),
                    d6_implementation=row.d6_implementation,
                    d7_prevention=row.d7_prevention,
                    d8_closure=row.d8_closure,
                    status=row.status,
                    rca=rca_data,
                    capa=capa_data,
                )
            )

            evidence.append(
                build_evidence(
                    source_type="eight_d",
                    source_id=row.report_number,
                    table="eight_d_reports",
                    record_id=row.id,
                    query_scope=f"get_8d:{scope}",
                )
            )

        return ToolResult(
            success=True,
            data=data,
            evidence=evidence,
            metadata=ToolMetadata(
                tool="get_8d",
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
                tool="get_8d"
            ),
        )

    except Exception:
        return ToolResult(
            success=False,
            errors=[
                ToolError(
                    code=ToolErrorCode.DATABASE_QUERY_FAILED,
                    message="8D lookup failed.",
                )
            ],
            metadata=ToolMetadata(
                tool="get_8d"
            ),
        )