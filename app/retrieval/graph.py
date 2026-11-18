from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class GraphNode:
    node_id: str
    node_type: str
    properties: dict[str, Any] = field(
        default_factory=dict
    )


@dataclass
class GraphEdge:
    source: str
    relationship: str
    target: str


@dataclass
class InvestigationGraph:
    nodes: dict[str, GraphNode] = field(
        default_factory=dict
    )

    edges: list[GraphEdge] = field(
        default_factory=list
    )

    def add_node(
        self,
        node: GraphNode,
    ) -> None:
        self.nodes[node.node_id] = node

    def add_edge(
        self,
        edge: GraphEdge,
    ) -> None:
        self.edges.append(edge)

    def neighbors(
        self,
        node_id: str,
    ) -> list[GraphNode]:

        target_ids = []

        for edge in self.edges:
            if edge.source == node_id:
                target_ids.append(edge.target)

            elif edge.target == node_id:
                target_ids.append(edge.source)

        return [
            self.nodes[node_id]
            for node_id in target_ids
            if node_id in self.nodes
        ]