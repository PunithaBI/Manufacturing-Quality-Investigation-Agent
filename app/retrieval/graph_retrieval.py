from __future__ import annotations

from collections import deque

from sqlalchemy.orm import Session

from app.tools.evidence import create_evidence_id

from .graph_projection import build_investigation_graph
from .models import RetrievalEvidence


def retrieve_graph(
    db: Session,
    *,
    ncr_number: str,
    max_results: int = 20,
    max_depth: int = 3,
    include_historical_ncrs: bool = True,
) -> list[RetrievalEvidence]:
    """
    Retrieve investigation evidence by traversing the
    manufacturing graph starting from an NCR.

    The graph itself is a projection of the NordWind
    relational database.
    """

    if not ncr_number or not ncr_number.strip():
        return []

    if max_results < 1:
        return []

    if max_depth < 0:
        return []

    graph = build_investigation_graph(
        db,
        ncr_number=ncr_number.strip(),
        include_historical_ncrs=include_historical_ncrs,
    )

    start_node = f"ncr:{ncr_number.strip()}"

    if start_node not in graph.nodes:
        return []

    visited: set[str] = set()

    queue = deque(
        [
            (
                start_node,
                0,
            )
        ]
    )

    results: list[RetrievalEvidence] = []

    while queue and len(results) < max_results:

        node_id, depth = queue.popleft()

        if node_id in visited:
            continue

        visited.add(node_id)

        node = graph.nodes.get(node_id)

        if node is None:
            continue

        if depth > 0:
            evidence = _node_to_evidence(
                graph,
                node_id=node_id,
                depth=depth,
            )

            if evidence is not None:
                results.append(evidence)

        if depth >= max_depth:
            continue

        for neighbor in _neighbor_ids(
            graph,
            node_id,
        ):
            if neighbor not in visited:
                queue.append(
                    (
                        neighbor,
                        depth + 1,
                    )
                )

    return results[:max_results]


def _neighbor_ids(
    graph,
    node_id: str,
) -> list[str]:
    neighbors: list[str] = []

    for edge in graph.edges:

        if edge.source == node_id:
            neighbors.append(edge.target)

        elif edge.target == node_id:
            neighbors.append(edge.source)

    return neighbors


def _relationship_between(
    graph,
    source_node_id: str,
    target_node_id: str,
) -> str | None:

    for edge in graph.edges:

        if (
            edge.source == source_node_id
            and edge.target == target_node_id
        ):
            return edge.relationship

        if (
            edge.target == source_node_id
            and edge.source == target_node_id
        ):
            return edge.relationship

    return None


def _node_to_evidence(
    graph,
    *,
    node_id: str,
    depth: int,
) -> RetrievalEvidence | None:

    node = graph.nodes.get(node_id)

    if node is None:
        return None

    source_type = node.node_type

    properties = node.properties

    source_id = _source_id(
        node,
    )

    if source_id is None:
        return None

    evidence_id = create_evidence_id(
        source_type=source_type,
        source_id=str(source_id),
    )

    relationship = _relationship_to_anchor(
        graph,
        node_id,
    )

    title = _title_for_node(
        node,
        source_id,
    )

    content = _content_for_node(
        node,
    )

    return RetrievalEvidence(
        evidence_id=evidence_id,
        source_type=source_type,
        source_id=str(source_id),
        retrieval_method="graph",
        title=title,
        content=content,
        score=_graph_score(depth),
        metadata={
            "graph_depth": depth,
            "relationship": relationship,
            "node_type": source_type,
        },
        provenance={
            "table": _table_for_node_type(
                source_type,
            ),
            "record_id": properties.get(
                "id",
            ),
            "query_scope": (
                "manufacturing_investigation_graph"
            ),
        },
    )


def _relationship_to_anchor(
    graph,
    node_id: str,
) -> str | None:

    for edge in graph.edges:

        if edge.source == node_id:
            return edge.relationship

        if edge.target == node_id:
            return edge.relationship

    return None


def _source_id(node) -> str | None:

    properties = node.properties

    candidates = [
        properties.get("ncr_number"),
        properties.get("serial_number"),
        properties.get("order_number"),
        properties.get("component_code"),
        properties.get("report_number"),
        properties.get("id"),
    ]

    for value in candidates:
        if value is not None:
            return str(value)

    return None


def _title_for_node(
    node,
    source_id: str,
) -> str:

    node_type = node.node_type

    if node_type == "ncr":
        return f"NCR {source_id}"

    if node_type == "serial":
        return f"Serial {source_id}"

    if node_type == "manufacturing_order":
        return f"Manufacturing Order {source_id}"

    if node_type == "operation":
        return f"Operation {source_id}"

    if node_type == "process_measurement":
        return f"Process Measurement {source_id}"

    if node_type == "inspection":
        return f"Inspection {source_id}"

    if node_type == "8d":
        return f"8D Report {source_id}"

    if node_type == "rca":
        return f"RCA {source_id}"

    if node_type == "capa":
        return f"CAPA {source_id}"

    if node_type == "product":
        return f"Product {source_id}"

    if node_type == "bom":
        return f"BOM {source_id}"

    if node_type == "component":
        return f"Component {source_id}"

    if node_type == "lot":
        return f"Lot {source_id}"

    return f"{node_type} {source_id}"


def _content_for_node(node) -> str | None:

    properties = node.properties

    preferred_fields = [
        "description",
        "summary",
        "root_cause",
        "name",
        "parameter",
        "value",
    ]

    values: list[str] = []

    for field in preferred_fields:

        value = properties.get(field)

        if value is None:
            continue

        values.append(
            f"{field}: {value}"
        )

    if not values:
        return None

    return "; ".join(values)


def _graph_score(depth: int) -> float:

    if depth <= 1:
        return 1.0

    if depth == 2:
        return 0.85

    if depth == 3:
        return 0.70

    return 0.50


def _table_for_node_type(
    node_type: str,
) -> str:

    mapping = {
        "ncr": "ncrs",
        "serial": "serial_units",
        "manufacturing_order": "manufacturing_orders",
        "operation": "operations",
        "process_measurement": "process_measurements",
        "inspection": "inspections",
        "8d": "eight_d_reports",
        "rca": "rcas",
        "capa": "capas",
        "product": "products",
        "bom": "boms",
        "component": "components",
        "lot": "lots",
    }

    return mapping.get(
        node_type,
        node_type,
    )