from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .chunking import DocumentChunk


class LocalVectorStore:
    """
    Persistent local vector store.

    Storage:

        vectors.npy
        chunks.json

    Chunk IDs are treated as stable keys.

    Re-ingesting the same database records replaces their
    existing chunks instead of creating duplicates.
    """

    def __init__(
        self,
        directory: str | Path = "data/vector_index",
    ) -> None:

        self.directory = Path(directory)

        self.directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.vectors_path = (
            self.directory / "vectors.npy"
        )

        self.chunks_path = (
            self.directory / "chunks.json"
        )

        self.vectors: np.ndarray | None = None
        self.chunks: list[DocumentChunk] = []

        self.load()

    def add(
        self,
        vectors: np.ndarray,
        chunks: list[DocumentChunk],
    ) -> None:

        if len(vectors) != len(chunks):
            raise ValueError(
                "Number of vectors must equal "
                "number of chunks"
            )

        if not chunks:
            return

        vectors = np.asarray(
            vectors,
            dtype=np.float32,
        )

        if vectors.ndim != 2:
            raise ValueError(
                "Vectors must be a 2-dimensional array"
            )

        # ---------------------------------------------------------
        # First ingestion
        # ---------------------------------------------------------

        if self.vectors is None:

            self.vectors = vectors
            self.chunks = list(chunks)

            self.save()
            return

        if self.vectors.shape[1] != vectors.shape[1]:

            raise ValueError(
                "Embedding dimensions do not match"
            )

        # ---------------------------------------------------------
        # Upsert by chunk_id
        # ---------------------------------------------------------

        existing_index = {
            chunk.chunk_id: index
            for index, chunk in enumerate(
                self.chunks
            )
        }

        new_vectors: list[np.ndarray] = []
        new_chunks: list[DocumentChunk] = []

        for index, chunk in enumerate(chunks):

            if chunk.chunk_id in existing_index:

                old_index = existing_index[
                    chunk.chunk_id
                ]

                self.vectors[old_index] = (
                    vectors[index]
                )

                self.chunks[old_index] = chunk

            else:

                new_vectors.append(
                    vectors[index]
                )

                new_chunks.append(
                    chunk
                )

        if new_vectors:

            self.vectors = np.vstack(
                [
                    self.vectors,
                    np.asarray(
                        new_vectors,
                        dtype=np.float32,
                    ),
                ]
            )

            self.chunks.extend(
                new_chunks
            )

        self.save()

    def search(
        self,
        query_vector: np.ndarray,
        *,
        limit: int = 20,
    ) -> list[tuple[DocumentChunk, float]]:

        if (
            self.vectors is None
            or not self.chunks
        ):
            return []

        if limit < 1:
            return []

        query_vector = np.asarray(
            query_vector,
            dtype=np.float32,
        ).reshape(-1)

        if (
            query_vector.shape[0]
            != self.vectors.shape[1]
        ):
            raise ValueError(
                "Query vector dimension does not "
                "match index"
            )

        query_norm = np.linalg.norm(
            query_vector
        )

        if query_norm == 0:
            return []

        matrix_norms = np.linalg.norm(
            self.vectors,
            axis=1,
        )

        denominator = (
            matrix_norms * query_norm
        )

        scores = np.divide(
            self.vectors @ query_vector,
            denominator,
            out=np.zeros_like(
                denominator
            ),
            where=denominator != 0,
        )

        top_indices = np.argsort(
            scores
        )[::-1][:limit]

        return [
            (
                self.chunks[index],
                float(scores[index]),
            )
            for index in top_indices
        ]

    def save(self) -> None:

        if self.vectors is not None:

            np.save(
                self.vectors_path,
                self.vectors,
            )

        payload = [
            {
                "chunk_id": chunk.chunk_id,
                "document_id": chunk.document_id,
                "source_type": chunk.source_type,
                "source_id": chunk.source_id,
                "title": chunk.title,
                "content": chunk.content,
                "chunk_type": chunk.chunk_type,
                "metadata": chunk.metadata,
                "provenance": chunk.provenance,
            }
            for chunk in self.chunks
        ]

        self.chunks_path.write_text(
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )

    def load(self) -> None:

        if self.vectors_path.exists():

            self.vectors = np.load(
                self.vectors_path
            )

        if self.chunks_path.exists():

            payload = json.loads(
                self.chunks_path.read_text(
                    encoding="utf-8"
                )
            )

            self.chunks = [
                DocumentChunk(
                    chunk_id=item["chunk_id"],
                    document_id=item[
                        "document_id"
                    ],
                    source_type=item[
                        "source_type"
                    ],
                    source_id=item[
                        "source_id"
                    ],
                    title=item["title"],
                    content=item["content"],
                    chunk_type=item[
                        "chunk_type"
                    ],
                    metadata=item.get(
                        "metadata",
                        {},
                    ),
                    provenance=item.get(
                        "provenance",
                        {},
                    ),
                )
                for item in payload
            ]

    @property
    def count(self) -> int:
        return len(self.chunks)