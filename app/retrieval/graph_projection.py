from __future__ import annotations

from sqlalchemy.orm import Session

from app.db import models

from .graph import GraphEdge, GraphNode, InvestigationGraph


def _node_id(node_type: str, value: object) -> str:
    return f"{node_type}:{value}"


def _safe_value(obj: object, *names: str, default: object = None) -> object:
    for name in names:
        if hasattr(obj, name):
            value = getattr(obj, name)
            if value is not None:
                return value

    return default


def _add_node(
    graph: InvestigationGraph,
    *,
    node_type: str,
    source_id: object,
    properties: dict | None = None,
) -> str:
    node_id = _node_id(node_type, source_id)

    graph.add_node(
        GraphNode(
            node_id=node_id,
            node_type=node_type,
            properties=properties or {},
        )
    )

    return node_id


def _add_edge(
    graph: InvestigationGraph,
    source: str,
    relationship: str,
    target: str,
) -> None:
    graph.add_edge(
        GraphEdge(
            source=source,
            relationship=relationship,
            target=target,
        )
    )


def build_investigation_graph(
    db: Session,
    *,
    ncr_number: str,
    include_historical_ncrs: bool = True,
    historical_limit: int = 20,
) -> InvestigationGraph:
    """
    Build a scoped manufacturing investigation graph starting from an NCR.

    The relational NordWind database remains the system of record.

    This function creates a retrieval projection only.

    Supported relationships:

        NCR
          ├── SerialUnit
          ├── Lot
          ├── ManufacturingOrder
          ├── Inspection
          └── EightD
                ├── RCA
                └── CAPA

        SerialUnit
          └── ManufacturingOrder
                └── Operation
                      └── ProcessMeasurement

        Product
          └── BOM
                └── Component

    The current NordWind schema does NOT provide a true serial/component
    consumption genealogy table, so no SerialUnit -> Component/Lot
    consumption edge is fabricated.
    """

    graph = InvestigationGraph()

    ncr = (
        db.query(models.NCR)
        .filter(models.NCR.ncr_number == ncr_number)
        .first()
    )

    if ncr is None:
        return graph

    # ---------------------------------------------------------
    # NCR
    # ---------------------------------------------------------

    ncr_number_value = _safe_value(
        ncr,
        "ncr_number",
        default=ncr_number,
    )

    ncr_node = _add_node(
        graph,
        node_type="ncr",
        source_id=ncr_number_value,
        properties={
            "id": ncr.id,
            "ncr_number": ncr_number_value,
            "description": _safe_value(ncr, "description"),
            "severity": _safe_value(ncr, "severity"),
            "status": _safe_value(ncr, "status"),
        },
    )

    # ---------------------------------------------------------
    # SerialUnit
    # ---------------------------------------------------------

    serial = getattr(ncr, "serial_unit", None)

    if serial is not None:
        serial_number = _safe_value(
            serial,
            "serial_number",
            "serial_no",
            "number",
            default=serial.id,
        )

        serial_node = _add_node(
            graph,
            node_type="serial",
            source_id=serial_number,
            properties={
                "id": serial.id,
                "serial_number": serial_number,
            },
        )

        _add_edge(
            graph,
            ncr_node,
            "AFFECTS",
            serial_node,
        )

        # -----------------------------------------------------
        # Serial -> Manufacturing Order
        # -----------------------------------------------------

        manufacturing_order = getattr(
            serial,
            "manufacturing_order",
            None,
        )

        if manufacturing_order is not None:
            mo_number = _safe_value(
                manufacturing_order,
                "order_number",
                "mo_number",
                "number",
                default=manufacturing_order.id,
            )

            mo_node = _add_node(
                graph,
                node_type="manufacturing_order",
                source_id=mo_number,
                properties={
                    "id": manufacturing_order.id,
                    "order_number": mo_number,
                },
            )

            _add_edge(
                graph,
                serial_node,
                "PRODUCED_BY",
                mo_node,
            )

            _add_operations(
                graph,
                manufacturing_order,
                mo_node,
            )

    # ---------------------------------------------------------
    # NCR -> Manufacturing Order
    # ---------------------------------------------------------

    ncr_mo = getattr(
        ncr,
        "manufacturing_order",
        None,
    )

    if ncr_mo is not None:
        mo_number = _safe_value(
            ncr_mo,
            "order_number",
            "mo_number",
            "number",
            default=ncr_mo.id,
        )

        mo_node = _add_node(
            graph,
            node_type="manufacturing_order",
            source_id=mo_number,
            properties={
                "id": ncr_mo.id,
                "order_number": mo_number,
            },
        )

        _add_edge(
            graph,
            ncr_node,
            "ASSOCIATED_WITH",
            mo_node,
        )

        _add_operations(
            graph,
            ncr_mo,
            mo_node,
        )

    # ---------------------------------------------------------
    # NCR -> Lot
    # ---------------------------------------------------------

    lot = getattr(ncr, "lot", None)

    if lot is not None:
        lot_number = _safe_value(
            lot,
            "lot_number",
            "lot_no",
            "number",
            default=lot.id,
        )

        lot_node = _add_node(
            graph,
            node_type="lot",
            source_id=lot_number,
            properties={
                "id": lot.id,
                "lot_number": lot_number,
            },
        )

        _add_edge(
            graph,
            ncr_node,
            "AFFECTS_LOT",
            lot_node,
        )

        component = getattr(
            lot,
            "component",
            None,
        )

        if component is not None:
            component_code = _safe_value(
                component,
                "component_code",
                "code",
                "part_number",
                "number",
                default=component.id,
            )

            component_node = _add_node(
                graph,
                node_type="component",
                source_id=component_code,
                properties={
                    "id": component.id,
                    "component_code": component_code,
                    "name": _safe_value(
                        component,
                        "name",
                    ),
                },
            )

            _add_edge(
                graph,
                lot_node,
                "LOT_OF",
                component_node,
            )

    # ---------------------------------------------------------
    # NCR -> Inspection
    # ---------------------------------------------------------

    inspection = getattr(
        ncr,
        "inspection",
        None,
    )

    if inspection is not None:
        inspection_node = _add_node(
            graph,
            node_type="inspection",
            source_id=inspection.id,
            properties={
                "id": inspection.id,
                "result": _safe_value(
                    inspection,
                    "result",
                    "status",
                ),
            },
        )

        _add_edge(
            graph,
            ncr_node,
            "IDENTIFIED_BY",
            inspection_node,
        )

    # ---------------------------------------------------------
    # NCR -> EightD
    # ---------------------------------------------------------

    eight_d_collection = getattr(
        ncr,
        "eight_d_reports",
        None,
    )

    if eight_d_collection is None:
        eight_d_collection = getattr(
            ncr,
            "eight_d",
            None,
        )

    if eight_d_collection is not None:

        if not isinstance(
            eight_d_collection,
            (list, tuple, set),
        ):
            eight_d_collection = [eight_d_collection]

        for report in list(eight_d_collection)[:20]:

            report_number = _safe_value(
                report,
                "report_number",
                "number",
                default=report.id,
            )

            eight_d_node = _add_node(
                graph,
                node_type="8d",
                source_id=report_number,
                properties={
                    "id": report.id,
                    "report_number": report_number,
                    "summary": _safe_value(
                        report,
                        "summary",
                        "description",
                    ),
                    "status": _safe_value(
                        report,
                        "status",
                    ),
                },
            )

            _add_edge(
                graph,
                ncr_node,
                "HAS_8D",
                eight_d_node,
            )

            _add_rca_and_capa(
                graph,
                report,
                eight_d_node,
            )

    # ---------------------------------------------------------
    # Product
    # ---------------------------------------------------------

    product = None

    if serial is not None:
        product = getattr(
            serial,
            "product",
            None,
        )

    if product is None and ncr_mo is not None:
        product = getattr(
            ncr_mo,
            "product",
            None,
        )

    if product is not None:
        product_code = _safe_value(
            product,
            "product_code",
            "code",
            "part_number",
            "number",
            default=product.id,
        )

        product_node = _add_node(
            graph,
            node_type="product",
            source_id=product_code,
            properties={
                "id": product.id,
                "product_code": product_code,
                "name": _safe_value(
                    product,
                    "name",
                ),
                "revision": _safe_value(
                    product,
                    "revision",
                ),
            },
        )

        _add_edge(
            graph,
            ncr_node,
            "RELATES_TO_PRODUCT",
            product_node,
        )

        _add_product_bom(
            graph,
            product,
            product_node,
        )

        if include_historical_ncrs:
            _add_historical_ncrs(
                graph,
                db,
                product,
                product_node,
                current_ncr_id=ncr.id,
                limit=historical_limit,
            )

    return graph


def _add_operations(
    graph: InvestigationGraph,
    manufacturing_order: object,
    mo_node: str,
) -> None:
    operations = getattr(
        manufacturing_order,
        "operations",
        None,
    )

    if operations is None:
        return

    for operation in list(operations):

        operation_number = _safe_value(
            operation,
            "operation_number",
            "operation_code",
            "code",
            "number",
            default=operation.id,
        )

        operation_node = _add_node(
            graph,
            node_type="operation",
            source_id=operation_number,
            properties={
                "id": operation.id,
                "operation_number": operation_number,
                "name": _safe_value(
                    operation,
                    "name",
                    "description",
                ),
            },
        )

        _add_edge(
            graph,
            mo_node,
            "HAS_OPERATION",
            operation_node,
        )

        measurements = getattr(
            operation,
            "process_measurements",
            None,
        )

        if measurements is None:
            measurements = getattr(
                operation,
                "measurements",
                None,
            )

        if measurements is not None:
            for measurement in list(measurements):

                measurement_node = _add_node(
                    graph,
                    node_type="process_measurement",
                    source_id=measurement.id,
                    properties={
                        "id": measurement.id,
                        "parameter": _safe_value(
                            measurement,
                            "parameter",
                            "measurement_type",
                            "name",
                        ),
                        "value": _safe_value(
                            measurement,
                            "value",
                            "measurement_value",
                        ),
                        "unit": _safe_value(
                            measurement,
                            "unit",
                        ),
                    },
                )

                _add_edge(
                    graph,
                    operation_node,
                    "HAS_MEASUREMENT",
                    measurement_node,
                )


def _add_rca_and_capa(
    graph: InvestigationGraph,
    report: object,
    eight_d_node: str,
) -> None:

    rca = getattr(
        report,
        "rca",
        None,
    )

    if rca is not None:

        rca_node = _add_node(
            graph,
            node_type="rca",
            source_id=rca.id,
            properties={
                "id": rca.id,
                "method": _safe_value(
                    rca,
                    "method",
                ),
                "root_cause": _safe_value(
                    rca,
                    "root_cause",
                    "description",
                ),
            },
        )

        _add_edge(
            graph,
            eight_d_node,
            "HAS_RCA",
            rca_node,
        )

    capa = getattr(
        report,
        "capa",
        None,
    )

    if capa is not None:

        capa_node = _add_node(
            graph,
            node_type="capa",
            source_id=capa.id,
            properties={
                "id": capa.id,
                "description": _safe_value(
                    capa,
                    "description",
                    "action",
                ),
                "status": _safe_value(
                    capa,
                    "status",
                ),
            },
        )

        _add_edge(
            graph,
            eight_d_node,
            "HAS_CAPA",
            capa_node,
        )


def _add_product_bom(
    graph: InvestigationGraph,
    product: object,
    product_node: str,
) -> None:

    boms = getattr(
        product,
        "boms",
        None,
    )

    if boms is None:
        return

    for bom in list(boms):

        bom_node = _add_node(
            graph,
            node_type="bom",
            source_id=bom.id,
            properties={
                "id": bom.id,
                "quantity": _safe_value(
                    bom,
                    "quantity",
                ),
            },
        )

        _add_edge(
            graph,
            product_node,
            "HAS_BOM",
            bom_node,
        )

        component = getattr(
            bom,
            "component",
            None,
        )

        if component is None:
            continue

        component_code = _safe_value(
            component,
            "component_code",
            "code",
            "part_number",
            "number",
            default=component.id,
        )

        component_node = _add_node(
            graph,
            node_type="component",
            source_id=component_code,
            properties={
                "id": component.id,
                "component_code": component_code,
                "name": _safe_value(
                    component,
                    "name",
                ),
            },
        )

        _add_edge(
            graph,
            bom_node,
            "CONTAINS_COMPONENT",
            component_node,
        )


def _add_historical_ncrs(
    graph: InvestigationGraph,
    db: Session,
    product: object,
    product_node: str,
    *,
    current_ncr_id: int,
    limit: int,
) -> None:

    historical_ncrs = (
        db.query(models.NCR)
        .join(models.SerialUnit)
        .filter(
            models.SerialUnit.product_id == product.id,
            models.NCR.id != current_ncr_id,
        )
        .order_by(models.NCR.id.desc())
        .limit(limit)
        .all()
    )

    for ncr in historical_ncrs:

        ncr_number = _safe_value(
            ncr,
            "ncr_number",
            default=ncr.id,
        )

        historical_node = _add_node(
            graph,
            node_type="ncr",
            source_id=ncr_number,
            properties={
                "id": ncr.id,
                "ncr_number": ncr_number,
                "description": _safe_value(
                    ncr,
                    "description",
                ),
                "severity": _safe_value(
                    ncr,
                    "severity",
                ),
                "status": _safe_value(
                    ncr,
                    "status",
                ),
                "historical": True,
            },
        )

        _add_edge(
            graph,
            product_node,
            "HAS_HISTORICAL_NCR",
            historical_node,
        )