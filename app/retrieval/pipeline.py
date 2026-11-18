from __future__ import annotations

from sqlalchemy.orm import Session

from .models import (
    InvestigationContext,
    RetrievalEvidence,
    RetrievalRequest,
)
from .structured import retrieve_ncr, retrieve_product
from .graph_retrieval import retrieve_graph
from .keyword import search_ncr_keywords
from .vector import SentenceTransformerRetriever, VectorRetriever
from .hybrid import combine_evidence
from .validation import validate_evidence
from .compression import compress_context


DEFAULT_MAX_RESULTS = 20
DEFAULT_COMPRESSION_ITEMS = 10
DEFAULT_GRAPH_DEPTH = 3


class HybridRetrievalPipeline:

    def __init__(
        self,
        *,
        vector_retriever: VectorRetriever | None = None,
    ) -> None:

        self.vector_retriever = (
            vector_retriever
            if vector_retriever is not None
            else SentenceTransformerRetriever()
        )

    def retrieve(
        self,
        db: Session,
        request: RetrievalRequest,
    ) -> InvestigationContext:

        query = request.query.strip()

        if not query:
            return InvestigationContext(
                query=request.query,
                evidence=[],
                evidence_count=0,
                compression_ratio=1.0,
            )

        max_results = min(
            max(request.max_results, 1),
            DEFAULT_MAX_RESULTS,
        )

        all_evidence: list[RetrievalEvidence] = []

        # ---------------------------------------------------------
        # 1. Structured retrieval
        # ---------------------------------------------------------

        structured_evidence = self._structured_retrieval(
            db=db,
            query=query,
            investigation_id=request.investigation_id,
        )

        all_evidence.extend(structured_evidence)

        # ---------------------------------------------------------
        # 2. Graph retrieval
        # ---------------------------------------------------------

        graph_evidence = self._graph_retrieval(
            db=db,
            query=query,
            investigation_id=request.investigation_id,
            max_results=max_results,
        )

        all_evidence.extend(graph_evidence)

        # ---------------------------------------------------------
        # 3. Keyword retrieval
        # ---------------------------------------------------------

        keyword_evidence = search_ncr_keywords(
            db=db,
            query=query,
            limit=max_results,
        )

        all_evidence.extend(keyword_evidence)

        # ---------------------------------------------------------
        # 4. Vector retrieval
        # ---------------------------------------------------------

        try:
            vector_evidence = self.vector_retriever.search(
                query=query,
                limit=max_results,
            )

            all_evidence.extend(vector_evidence)

        except Exception:
            # Vector retrieval failure must not destroy
            # the structured/graph investigation path.
            pass

        # ---------------------------------------------------------
        # 5. Hybrid ranking
        # ---------------------------------------------------------

        hybrid_result = combine_evidence(
            all_evidence,
            max_results=max_results,
        )

        if not hybrid_result.success:
            return InvestigationContext(
                query=query,
                evidence=[],
                evidence_count=0,
                compression_ratio=1.0,
            )

        # ---------------------------------------------------------
        # 6. Evidence validation
        # ---------------------------------------------------------

        validated_evidence = validate_evidence(
            hybrid_result.evidence
        )

        # ---------------------------------------------------------
        # 7. Context compression
        # ---------------------------------------------------------

        return compress_context(
            query=query,
            evidence=validated_evidence,
            max_items=DEFAULT_COMPRESSION_ITEMS,
        )

    # ------------------------------------------------------------------
    # Structured retrieval
    # ------------------------------------------------------------------

    def _structured_retrieval(
        self,
        *,
        db: Session,
        query: str,
        investigation_id: str | None,
    ) -> list[RetrievalEvidence]:

        results: list[RetrievalEvidence] = []

        if investigation_id:
            results.extend(
                retrieve_ncr(
                    db=db,
                    ncr_number=investigation_id,
                )
            )

        if query != investigation_id:
            results.extend(
                retrieve_ncr(
                    db=db,
                    ncr_number=query,
                )
            )

        results.extend(
            retrieve_product(
                db=db,
                product_code=query,
            )
        )

        return results

    # ------------------------------------------------------------------
    # Graph retrieval
    # ------------------------------------------------------------------

    def _graph_retrieval(
        self,
        *,
        db: Session,
        query: str,
        investigation_id: str | None,
        max_results: int,
    ) -> list[RetrievalEvidence]:

        ncr_number = investigation_id or query

        if not ncr_number:
            return []

        try:
            return retrieve_graph(
                db=db,
                ncr_number=ncr_number,
                max_results=max_results,
                max_depth=DEFAULT_GRAPH_DEPTH,
                include_historical_ncrs=True,
            )

        except Exception:
            return []


def retrieve_investigation_context(
    db: Session,
    request: RetrievalRequest,
    *,
    vector_retriever: VectorRetriever | None = None,
) -> InvestigationContext:

    pipeline = HybridRetrievalPipeline(
        vector_retriever=vector_retriever,
    )

    return pipeline.retrieve(
        db=db,
        request=request,
    )