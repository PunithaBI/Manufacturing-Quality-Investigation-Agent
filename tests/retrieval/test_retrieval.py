from __future__ import annotations

from app.retrieval.models import (
    HybridEvidence,
    RetrievalEvidence,
)
from app.retrieval.hybrid import combine_evidence
from app.retrieval.validation import validate_evidence
from app.retrieval.compression import compress_context
from app.retrieval.keyword import search_ncr_keywords
from app.retrieval.structured import (
    retrieve_ncr,
    retrieve_product,
)
from app.retrieval.vector import EmptyVectorRetriever
from app.retrieval.graph import (
    GraphNode,
    GraphEdge,
    InvestigationGraph,
)


# ---------------------------------------------------------------------------
# Structured retrieval
# ---------------------------------------------------------------------------


def test_structured_ncr_retrieval(
    db,
    sample_ncr,
):
    if sample_ncr is None:
        return

    evidence = retrieve_ncr(
        db,
        sample_ncr.ncr_number,
    )

    assert isinstance(evidence, list)
    assert evidence

    for item in evidence:
        assert isinstance(item, RetrievalEvidence)
        assert item.retrieval_method == "structured"
        assert item.source_type == "ncr"
        assert item.source_id == sample_ncr.ncr_number
        assert item.provenance
        assert item.provenance["table"] == "ncrs"
        assert item.provenance["record_id"] == sample_ncr.id


def test_structured_product_retrieval(
    db,
    sample_product,
):
    if sample_product is None:
        return

    evidence = retrieve_product(
        db,
        sample_product.product_code,
    )

    assert isinstance(evidence, list)
    assert evidence

    for item in evidence:
        assert item.retrieval_method == "structured"
        assert item.source_type == "product"
        assert item.source_id == sample_product.product_code
        assert item.provenance
        assert item.provenance["table"] == "products"
        assert item.provenance["record_id"] == sample_product.id


# ---------------------------------------------------------------------------
# Graph retrieval
# ---------------------------------------------------------------------------


def test_graph_node_creation():
    graph = InvestigationGraph()

    node = GraphNode(
        node_id="ncr:NCR-001",
        node_type="ncr",
        properties={
            "ncr_number": "NCR-001",
        },
    )

    graph.add_node(node)

    assert "ncr:NCR-001" in graph.nodes
    assert graph.nodes["ncr:NCR-001"].node_type == "ncr"


def test_graph_relationship_creation():
    graph = InvestigationGraph()

    ncr = GraphNode(
        node_id="ncr:NCR-001",
        node_type="ncr",
    )

    serial = GraphNode(
        node_id="serial:SN-001",
        node_type="serial",
    )

    graph.add_node(ncr)
    graph.add_node(serial)

    graph.add_edge(
        GraphEdge(
            source="ncr:NCR-001",
            relationship="AFFECTS",
            target="serial:SN-001",
        )
    )

    neighbors = graph.neighbors("ncr:NCR-001")

    assert len(neighbors) == 1
    assert neighbors[0].node_id == "serial:SN-001"


def test_graph_bidirectional_neighbor_lookup():
    graph = InvestigationGraph()

    ncr = GraphNode(
        node_id="ncr:NCR-001",
        node_type="ncr",
    )

    serial = GraphNode(
        node_id="serial:SN-001",
        node_type="serial",
    )

    graph.add_node(ncr)
    graph.add_node(serial)

    graph.add_edge(
        GraphEdge(
            source="ncr:NCR-001",
            relationship="AFFECTS",
            target="serial:SN-001",
        )
    )

    neighbors = graph.neighbors("serial:SN-001")

    assert len(neighbors) == 1
    assert neighbors[0].node_id == "ncr:NCR-001"


# ---------------------------------------------------------------------------
# Keyword retrieval
# ---------------------------------------------------------------------------


def test_keyword_retrieval(
    db,
    sample_ncr,
):
    if sample_ncr is None:
        return

    description = sample_ncr.description

    if not description:
        return

    # Use a small substring so we do not depend on exact full-text matching.
    query = description[:20]

    evidence = search_ncr_keywords(
        db,
        query=query,
        limit=20,
    )

    assert isinstance(evidence, list)

    for item in evidence:
        assert item.retrieval_method == "keyword"
        assert item.source_type == "ncr"
        assert item.provenance["table"] == "ncrs"
        assert item.provenance["record_id"] >= 1


def test_keyword_empty_query_returns_empty(db):
    evidence = search_ncr_keywords(
        db,
        query="",
        limit=20,
    )

    assert evidence == []


# ---------------------------------------------------------------------------
# Vector retrieval interface
# ---------------------------------------------------------------------------


def test_empty_vector_retriever():
    retriever = EmptyVectorRetriever()

    evidence = retriever.search(
        query="bearing overheating",
        limit=20,
    )

    assert evidence == []


def test_vector_retriever_interface_is_safe():
    retriever = EmptyVectorRetriever()

    evidence = retriever.search(
        query="test query",
        limit=1,
    )

    assert isinstance(evidence, list)


# ---------------------------------------------------------------------------
# Hybrid evidence
# ---------------------------------------------------------------------------


def test_hybrid_combines_multiple_retrieval_methods():
    evidence = [
        RetrievalEvidence(
            evidence_id="EV-001",
            source_type="ncr",
            source_id="NCR-001",
            retrieval_method="structured",
            title="NCR-001",
            content="Bearing temperature exceeded limit.",
            score=1.0,
            provenance={
                "table": "ncrs",
                "record_id": 1,
            },
        ),
        RetrievalEvidence(
            evidence_id="EV-001",
            source_type="ncr",
            source_id="NCR-001",
            retrieval_method="keyword",
            title="NCR-001",
            content="Bearing temperature exceeded limit.",
            score=1.0,
            provenance={
                "table": "ncrs",
                "record_id": 1,
            },
        ),
        RetrievalEvidence(
            evidence_id="EV-002",
            source_type="ncr",
            source_id="NCR-002",
            retrieval_method="vector",
            title="NCR-002",
            content="Abnormal thermal rise detected.",
            score=0.85,
            provenance={
                "table": "ncrs",
                "record_id": 2,
            },
        ),
    ]

    result = combine_evidence(
        evidence,
        max_results=20,
    )

    assert result.success is True
    assert len(result.evidence) == 2

    first = result.evidence[0]

    assert first.evidence_id == "EV-001"
    assert "structured" in first.retrieval_methods
    assert "keyword" in first.retrieval_methods
    assert first.combined_score is not None


def test_hybrid_respects_result_limit():
    evidence = []

    for index in range(10):
        evidence.append(
            RetrievalEvidence(
                evidence_id=f"EV-{index}",
                source_type="ncr",
                source_id=f"NCR-{index}",
                retrieval_method="keyword",
                content=f"NCR evidence {index}",
                score=1.0,
                provenance={
                    "table": "ncrs",
                    "record_id": index + 1,
                },
            )
        )

    result = combine_evidence(
        evidence,
        max_results=3,
    )

    assert result.success is True
    assert len(result.evidence) == 3


def test_hybrid_empty_input():
    result = combine_evidence(
        [],
        max_results=20,
    )

    assert result.success is True
    assert result.evidence == []


# ---------------------------------------------------------------------------
# Evidence validation
# ---------------------------------------------------------------------------


def test_evidence_validation_accepts_valid_evidence():
    evidence = [
        HybridEvidence(
            evidence_id="EV-001",
            source_type="ncr",
            source_id="NCR-001",
            retrieval_methods=["structured"],
            content="Valid evidence.",
            combined_score=1.0,
            provenance={
                "table": "ncrs",
                "record_id": 1,
            },
        )
    ]

    validated = validate_evidence(evidence)

    assert len(validated) == 1
    assert validated[0].evidence_id == "EV-001"


def test_evidence_validation_rejects_missing_evidence_id():
    evidence = [
        HybridEvidence(
            evidence_id="",
            source_type="ncr",
            source_id="NCR-001",
            retrieval_methods=["structured"],
            content="Invalid evidence.",
            provenance={
                "table": "ncrs",
                "record_id": 1,
            },
        )
    ]

    validated = validate_evidence(evidence)

    assert validated == []


def test_evidence_validation_rejects_missing_source():
    evidence = [
        HybridEvidence(
            evidence_id="EV-001",
            source_type="",
            source_id="NCR-001",
            retrieval_methods=["structured"],
            content="Invalid evidence.",
            provenance={
                "table": "ncrs",
                "record_id": 1,
            },
        )
    ]

    validated = validate_evidence(evidence)

    assert validated == []


def test_evidence_validation_rejects_missing_provenance():
    evidence = [
        HybridEvidence(
            evidence_id="EV-001",
            source_type="ncr",
            source_id="NCR-001",
            retrieval_methods=["structured"],
            content="Invalid evidence.",
            provenance={},
        )
    ]

    validated = validate_evidence(evidence)

    assert validated == []


def test_evidence_validation_rejects_invalid_record_id():
    evidence = [
        HybridEvidence(
            evidence_id="EV-001",
            source_type="ncr",
            source_id="NCR-001",
            retrieval_methods=["structured"],
            content="Invalid evidence.",
            provenance={
                "table": "ncrs",
                "record_id": 0,
            },
        )
    ]

    validated = validate_evidence(evidence)

    assert validated == []


# ---------------------------------------------------------------------------
# Context compression
# ---------------------------------------------------------------------------


def test_context_compression():
    evidence = [
        HybridEvidence(
            evidence_id="EV-001",
            source_type="ncr",
            source_id="NCR-001",
            retrieval_methods=["structured", "keyword"],
            title="NCR-001",
            content="Bearing temperature exceeded the process limit.",
            combined_score=2.0,
            provenance={
                "table": "ncrs",
                "record_id": 1,
            },
        ),
        HybridEvidence(
            evidence_id="EV-002",
            source_type="ncr",
            source_id="NCR-002",
            retrieval_methods=["vector"],
            title="NCR-002",
            content="Historical thermal failure.",
            combined_score=0.8,
            provenance={
                "table": "ncrs",
                "record_id": 2,
            },
        ),
    ]

    context = compress_context(
        query="bearing overheating",
        evidence=evidence,
        max_items=10,
    )

    assert context.query == "bearing overheating"
    assert context.evidence_count == 2
    assert len(context.evidence) == 2

    assert context.evidence[0].evidence_id == "EV-001"
    assert context.evidence[0].summary
    assert context.evidence[0].provenance


def test_context_compression_limits_items():
    evidence = []

    for index in range(20):
        evidence.append(
            HybridEvidence(
                evidence_id=f"EV-{index}",
                source_type="ncr",
                source_id=f"NCR-{index}",
                retrieval_methods=["keyword"],
                content=f"Evidence {index}",
                combined_score=1.0,
                provenance={
                    "table": "ncrs",
                    "record_id": index + 1,
                },
            )
        )

    context = compress_context(
        query="test",
        evidence=evidence,
        max_items=5,
    )

    assert context.evidence_count == 5
    assert len(context.evidence) == 5


def test_context_compression_empty_evidence():
    context = compress_context(
        query="test",
        evidence=[],
        max_items=10,
    )

    assert context.evidence_count == 0
    assert context.evidence == []
    assert context.compression_ratio == 1.0


# ---------------------------------------------------------------------------
# End-to-end retrieval pipeline
# ---------------------------------------------------------------------------


def test_hybrid_pipeline(
    db,
    sample_ncr,
):
    if sample_ncr is None:
        return

    structured = retrieve_ncr(
        db,
        sample_ncr.ncr_number,
    )

    keyword = []

    if sample_ncr.description:
        keyword = search_ncr_keywords(
            db,
            sample_ncr.description[:20],
            limit=10,
        )

    vector = EmptyVectorRetriever().search(
        query=sample_ncr.description or sample_ncr.ncr_number,
        limit=10,
    )

    all_evidence = (
        structured
        + keyword
        + vector
    )

    hybrid = combine_evidence(
        all_evidence,
        max_results=20,
    )

    assert hybrid.success is True

    validated = validate_evidence(
        hybrid.evidence
    )

    context = compress_context(
        query=sample_ncr.description or sample_ncr.ncr_number,
        evidence=validated,
        max_items=10,
    )

    assert context.query
    assert context.evidence_count <= 10

    for item in context.evidence:
        assert item.evidence_id
        assert item.source_type
        assert item.source_id
        assert item.provenance