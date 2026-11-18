from __future__ import annotations

from typing import Protocol

from sentence_transformers import SentenceTransformer

from app.config.settings import settings
from app.tools.evidence import create_evidence_id

from .models import RetrievalEvidence
from .vector_store import LocalVectorStore


class VectorRetriever(Protocol):

    def search(
        self,
        query: str,
        limit: int = 20,
    ) -> list[RetrievalEvidence]:
        ...


class EmptyVectorRetriever:

    def search(
        self,
        query: str,
        limit: int = 20,
    ) -> list[RetrievalEvidence]:

        return []


class SentenceTransformerRetriever:
    """
    Real semantic vector retriever.

    Embeddings are generated with Sentence Transformers
    and searched using cosine similarity.
    """

    def __init__(
        self,
        *,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        index_directory: str | None = None,
    ) -> None:

        self.model_name = model_name

        self.model = SentenceTransformer(
            model_name
        )

        self.store = LocalVectorStore(
            index_directory
            or settings.vector_index_directory
        )

    def search(
        self,
        query: str,
        limit: int = 20,
    ) -> list[RetrievalEvidence]:

        query = query.strip()

        if not query:
            return []

        if limit < 1:
            return []

        query_vector = self.model.encode(
            query,
            normalize_embeddings=False,
        )

        matches = self.store.search(
            query_vector,
            limit=limit,
        )

        results: list[RetrievalEvidence] = []

        for chunk, score in matches:

            source_id = (
                chunk.source_id
                or chunk.document_id
            )

            evidence_id = create_evidence_id(
                source_type=chunk.source_type,
                source_id=str(source_id),
            )

            results.append(
                RetrievalEvidence(
                    evidence_id=evidence_id,
                    source_type=chunk.source_type,
                    source_id=str(source_id),
                    retrieval_method="vector",
                    title=chunk.title,
                    content=chunk.content,
                    score=score,
                    metadata={
                        **chunk.metadata,
                        "chunk_id": chunk.chunk_id,
                        "document_id": chunk.document_id,
                        "chunk_type": chunk.chunk_type,
                        "embedding_model": self.model_name,
                    },
                    provenance=chunk.provenance,
                )
            )

        return results