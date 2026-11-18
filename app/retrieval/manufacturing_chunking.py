from __future__ import annotations

import re

from .chunking import DocumentChunk


SECTION_PATTERNS = [
    r"^\s*D[1-8]\s*[:\-].*$",
    r"^\s*root cause\s*[:\-].*$",
    r"^\s*corrective action\s*[:\-].*$",
    r"^\s*containment\s*[:\-].*$",
    r"^\s*problem description\s*[:\-].*$",
    r"^\s*failure mode\s*[:\-].*$",
    r"^\s*inspection results?\s*[:\-].*$",
    r"^\s*findings?\s*[:\-].*$",
    r"^\s*conclusion\s*[:\-].*$",
]


def is_section_heading(line: str) -> bool:
    """Recognize standalone headings without discarding inline evidence."""
    heading_patterns = [
        r"^\s*D[1-8]\s*[:\-]\s*$",
        r"^\s*root cause\s*[:\-]\s*$",
        r"^\s*corrective action\s*[:\-]\s*$",
        r"^\s*containment\s*[:\-]\s*$",
        r"^\s*problem description\s*[:\-]\s*$",
        r"^\s*failure mode\s*[:\-]\s*$",
        r"^\s*inspection results?\s*[:\-]\s*$",
        r"^\s*findings?\s*[:\-]\s*$",
        r"^\s*conclusion\s*[:\-]\s*$",
    ]

    return any(
        re.match(pattern, line, flags=re.IGNORECASE)
        for pattern in heading_patterns
    )


def chunk_manufacturing_document(
    document,
    *,
    max_characters: int = 1800,
) -> list[DocumentChunk]:

    content = document.content.strip()

    if not content:
        return []

    lines = content.splitlines()

    sections: list[tuple[str, list[str]]] = []

    current_title = document.title
    current_lines: list[str] = []

    for line in lines:

        if is_section_heading(line):

            if current_lines:
                sections.append(
                    (
                        current_title,
                        current_lines,
                    )
                )

            current_title = line.strip()
            current_lines = []

        else:

            current_lines.append(line)

    if current_lines:
        sections.append(
            (
                current_title,
                current_lines,
            )
        )

    chunks: list[DocumentChunk] = []

    chunk_number = 0

    for section_title, section_lines in sections:

        section_text = "\n".join(
            line
            for line in section_lines
            if line.strip()
        ).strip()

        if not section_text:
            continue

        # Keep a manufacturing section together
        # when it is reasonably small.
        if len(section_text) <= max_characters:

            chunks.append(
                _create_chunk(
                    document,
                    section_title,
                    section_text,
                    chunk_number,
                    chunk_type="section",
                )
            )

            chunk_number += 1
            continue

        # Large section: split while retaining section identity.
        start = 0

        while start < len(section_text):

            end = min(
                start + max_characters,
                len(section_text),
            )

            text = section_text[start:end].strip()

            if text:

                chunks.append(
                    _create_chunk(
                        document,
                        section_title,
                        text,
                        chunk_number,
                        chunk_type="section_part",
                    )
                )

                chunk_number += 1

            if end >= len(section_text):
                break

            start = end

    return chunks


def _create_chunk(
    document,
    section_title: str,
    content: str,
    chunk_number: int,
    *,
    chunk_type: str,
) -> DocumentChunk:

    return DocumentChunk(
        chunk_id=(
            f"{document.document_id}:"
            f"chunk:{chunk_number}"
        ),
        document_id=document.document_id,
        source_type=document.source_type,
        source_id=(
            document.source_id
            or document.document_id
        ),
        title=section_title,
        content=content,
        chunk_type=chunk_type,
        metadata={
            **document.metadata,
            "section": section_title,
            "chunk_number": chunk_number,
        },
        provenance=document.provenance,
    )