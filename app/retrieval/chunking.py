from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DocumentChunk:
    chunk_id: str
    document_id: str
    source_type: str
    source_id: str

    title: str
    content: str

    chunk_type: str

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    provenance: dict[str, Any] = field(
        default_factory=dict
    )


DEFAULT_CHUNK_SIZE = 1200
DEFAULT_CHUNK_OVERLAP = 200


def chunk_document(
    document,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[DocumentChunk]:

    content = document.content.strip()

    if not content:
        return []

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")

    if overlap < 0:
        raise ValueError("overlap cannot be negative")

    if overlap >= chunk_size:
        raise ValueError(
            "overlap must be smaller than chunk_size"
        )

    chunks: list[DocumentChunk] = []

    start = 0
    chunk_number = 0

    while start < len(content):

        end = min(
            start + chunk_size,
            len(content),
        )

        chunk_text = content[start:end].strip()

        if chunk_text:

            chunk_id = (
                f"{document.document_id}:"
                f"chunk:{chunk_number}"
            )

            chunks.append(
                DocumentChunk(
                    chunk_id=chunk_id,
                    document_id=document.document_id,
                    source_type=document.source_type,
                    source_id=(
                        document.source_id
                        or document.document_id
                    ),
                    title=document.title,
                    content=chunk_text,
                    chunk_type="text",
                    metadata={
                        **document.metadata,
                        "chunk_number": chunk_number,
                    },
                    provenance=document.provenance,
                )
            )

        if end >= len(content):
            break

        start = end - overlap
        chunk_number += 1

    return chunks