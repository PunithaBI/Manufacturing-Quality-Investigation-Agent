from __future__ import annotations

from pathlib import Path

from sentence_transformers import SentenceTransformer

from .chunking import DocumentChunk
from .documents import ManufacturingDocument
from .manufacturing_chunking import (
    chunk_manufacturing_document,
)
from .vector_store import LocalVectorStore


class VectorIngestionService:
    """
    Converts manufacturing documents into embeddings
    and stores them in the local vector index.
    """

    def __init__(
        self,
        *,
        model_name: str = (
            "sentence-transformers/"
            "all-MiniLM-L6-v2"
        ),
        index_directory: str = (
            "data/vector_index"
        ),
    ) -> None:

        self.model_name = model_name

        self.model = SentenceTransformer(
            model_name
        )

        self.store = LocalVectorStore(
            index_directory
        )

    def ingest(
        self,
        documents: list[ManufacturingDocument],
    ) -> int:

        all_chunks: list[DocumentChunk] = []

        for document in documents:

            chunks = chunk_manufacturing_document(
                document
            )

            all_chunks.extend(chunks)

        if not all_chunks:
            return 0

        texts = [
            self._embedding_text(chunk)
            for chunk in all_chunks
        ]

        embeddings = self.model.encode(
            texts,
            normalize_embeddings=False,
            show_progress_bar=True,
        )

        self.store.add(
            embeddings,
            all_chunks,
        )

        return len(all_chunks)

    def ingest_text_file(
        self,
        path: str | Path,
        *,
        source_type: str = "document",
        source_id: str | None = None,
        title: str | None = None,
    ) -> int:

        path = Path(path)

        content = path.read_text(
            encoding="utf-8"
        )

        document = ManufacturingDocument(
            document_id=(
                source_id
                or path.stem
            ),
            source_type=source_type,
            source_id=(
                source_id
                or path.stem
            ),
            title=(
                title
                or path.name
            ),
            content=content,
            provenance={
                "file": str(path),
            },
        )

        return self.ingest(
            [document]
        )

    @staticmethod
    def _embedding_text(
        chunk: DocumentChunk,
    ) -> str:

        # Include the manufacturing section and source
        # context in the embedding.
        return "\n".join(
            [
                f"Source type: {chunk.source_type}",
                f"Title: {chunk.title}",
                f"Section: "
                f"{chunk.metadata.get('section', '')}",
                chunk.content,
            ]
        )