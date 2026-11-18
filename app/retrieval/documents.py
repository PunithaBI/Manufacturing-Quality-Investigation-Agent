from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ManufacturingDocument:
    """
    Canonical document representation used by the ingestion layer.

    A document can originate from:
        - NCR
        - 8D report
        - RCA
        - CAPA
        - work instruction
        - inspection document
        - process document
        - historical investigation
        - uploaded PDF/DOCX/TXT
    """

    document_id: str
    source_type: str
    title: str
    content: str

    source_id: str | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    provenance: dict[str, Any] = field(
        default_factory=dict
    )