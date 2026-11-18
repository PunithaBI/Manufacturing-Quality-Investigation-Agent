from __future__ import annotations

from sqlalchemy.orm import Session

from app.tools.bom import BOMRequest, get_bom
from app.tools.genealogy import GenealogyRequest, get_serial_genealogy
from app.tools.manufacturing_history import (
    ManufacturingHistoryRequest,
    get_manufacturing_history,
)
from app.tools.ncr import NCRRequest, get_ncr
from app.tools.errors import ToolErrorCode
from app.tools.product import ProductRequest, get_product

from .models import (
    AgentStatus,
    InvestigationRequest,
    TraceabilityResult,
)


ROLE = "investigation_agent"


class ProductTraceabilityAgent:
    """
    Identifies the manufacturing entities connected to an NCR.

    The agent does not directly query arbitrary SQL.

    It uses only controlled manufacturing tools.
    """

    def run(
        self,
        db: Session,
        request: InvestigationRequest,
    ) -> TraceabilityResult:

        ncr_number = request.ncr_number.strip()

        if not ncr_number:
            return TraceabilityResult(
                status=AgentStatus.FAILED,
                ncr_number=ncr_number,
                errors=[
                    "NCR number is required."
                ],
            )

        result = TraceabilityResult(
            status=AgentStatus.SUCCESS,
            ncr_number=ncr_number,
        )

        # ---------------------------------------------------------
        # NCR
        # ---------------------------------------------------------

        ncr_result = get_ncr(
            db,
            NCRRequest(
                ncr_number=ncr_number,
                role=ROLE,
            ),
        )

        if not ncr_result.success or ncr_result.data is None:

            blocked_codes = {
                ToolErrorCode.RECORD_NOT_FOUND,
                ToolErrorCode.INVALID_INPUT,
            }

            if any(
                error.code in blocked_codes
                for error in ncr_result.errors
            ):
                result.status = AgentStatus.BLOCKED
            else:
                result.status = AgentStatus.FAILED

            result.errors.append(
                "NCR could not be retrieved."
            )

            return result

        ncr = ncr_result.data

        result.evidence.extend(
            self._tool_evidence(
                ncr_result.evidence
            )
        )

        # ---------------------------------------------------------
        # Initial values from NCR
        # ---------------------------------------------------------

        product_code = self._get_value(
            ncr,
            [
                "product_code",
                "product",
            ],
        )

        serial_number = self._get_value(
            ncr,
            [
                "serial_number",
            ],
        )

        # ---------------------------------------------------------
        # Serial genealogy
        # ---------------------------------------------------------

        if serial_number:

            genealogy_result = get_serial_genealogy(
                db,
                GenealogyRequest(
                    serial_number=str(
                        serial_number
                    ),
                    role=ROLE,
                ),
            )

            if genealogy_result.success:

                genealogy_data = self._extract_data(
                    genealogy_result.data
                )

                result.serial_unit = genealogy_data

                result.evidence.extend(
                    self._tool_evidence(
                        genealogy_result.evidence
                    )
                )

                # -------------------------------------------------
                # Enrich traceability from genealogy
                # -------------------------------------------------

                if isinstance(
                    genealogy_data,
                    dict,
                ):

                    resolved_product_code = (
                        genealogy_data.get(
                            "product_code"
                        )
                    )

                    resolved_manufacturing_order = (
                        genealogy_data.get(
                            "manufacturing_order"
                        )
                    )

                    # Genealogy can resolve the product even when
                    # the NCR itself does not expose product_code.
                    if resolved_product_code:
                        product_code = (
                            resolved_product_code
                        )

                    if resolved_manufacturing_order:
                        result.manufacturing_order = {
                            "manufacturing_order": (
                                resolved_manufacturing_order
                            )
                        }

            else:

                result.evidence_gaps.append(
                    "Serial genealogy unavailable."
                )

        else:

            result.evidence_gaps.append(
                "NCR is not linked to a serial number."
            )

        # ---------------------------------------------------------
        # Product
        # ---------------------------------------------------------

        if product_code:

            product_result = get_product(
                db,
                ProductRequest(
                    product_code=str(
                        product_code
                    ),
                    role=ROLE,
                ),
            )

            if (
                product_result.success
                and product_result.data is not None
            ):

                result.product = (
                    product_result.data.model_dump()
                    if hasattr(
                        product_result.data,
                        "model_dump",
                    )
                    else product_result.data.__dict__.copy()
                )

                result.evidence.extend(
                    self._tool_evidence(
                        product_result.evidence
                    )
                )

            else:

                result.evidence_gaps.append(
                    "Product could not be resolved."
                )

        else:

            result.evidence_gaps.append(
                "NCR does not expose a product code."
            )

        # ---------------------------------------------------------
        # Manufacturing history
        # ---------------------------------------------------------

        if serial_number:

            history_result = (
                get_manufacturing_history(
                    db,
                    ManufacturingHistoryRequest(
                        serial_number=str(
                            serial_number
                        ),
                        role=ROLE,
                    ),
                )
            )

            if history_result.success:

                history_data = self._extract_data(
                    history_result.data
                )

                if isinstance(
                    history_data,
                    dict,
                ):

                    history_manufacturing_order = (
                        history_data.get(
                            "manufacturing_order"
                        )
                    )

                    if history_manufacturing_order:
                        result.manufacturing_order = {
                            "manufacturing_order": (
                                history_manufacturing_order
                            )
                        }

                result.evidence.extend(
                    self._tool_evidence(
                        history_result.evidence
                    )
                )

            else:

                result.evidence_gaps.append(
                    "Manufacturing history unavailable."
                )

        # ---------------------------------------------------------
        # BOM
        # ---------------------------------------------------------

        if product_code:

            bom_result = get_bom(
                db,
                BOMRequest(
                    product_code=str(
                        product_code
                    ),
                    role=ROLE,
                ),
            )

            if bom_result.success:

                bom_data = self._extract_data(
                    bom_result.data
                )

                if bom_data is not None:

                    result.relationships.append(
                        {
                            "relationship": (
                                "product_has_bom"
                            ),
                            "data": bom_data,
                        }
                    )

                result.evidence.extend(
                    self._tool_evidence(
                        bom_result.evidence
                    )
                )

            else:

                result.evidence_gaps.append(
                    "BOM could not be retrieved."
                )

        # ---------------------------------------------------------
        # Final status
        # ---------------------------------------------------------

        if result.evidence_gaps:
            result.status = AgentStatus.PARTIAL

        return result

    @staticmethod
    def _get_value(
        obj,
        names: list[str],
    ):

        for name in names:

            if hasattr(obj, name):

                value = getattr(
                    obj,
                    name,
                )

                if value is not None:
                    return value

            if isinstance(obj, dict):

                value = obj.get(name)

                if value is not None:
                    return value

        return None

    @staticmethod
    def _extract_data(data):

        if data is None:
            return None

        if hasattr(
            data,
            "model_dump",
        ):
            return data.model_dump()

        if isinstance(
            data,
            dict,
        ):
            return data

        if hasattr(
            data,
            "__dict__",
        ):
            return data.__dict__.copy()

        return data

    @staticmethod
    def _tool_evidence(
        evidence,
    ) -> list[dict]:

        output = []

        for item in evidence:

            if hasattr(
                item,
                "model_dump",
            ):
                output.append(
                    item.model_dump()
                )

            elif isinstance(
                item,
                dict,
            ):
                output.append(item)

            else:
                output.append(
                    {
                        "evidence_id": getattr(
                            item,
                            "evidence_id",
                            None,
                        ),
                        "source_type": getattr(
                            item,
                            "source_type",
                            None,
                        ),
                        "source_id": getattr(
                            item,
                            "source_id",
                            None,
                        ),
                    }
                )

        return output