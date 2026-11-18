from __future__ import annotations

from sqlalchemy.orm import Session

from app.tools.ncr import NCRRequest, get_ncr
from app.tools.product import ProductRequest, get_product

from .models import RetrievalEvidence


ROLE = "investigation_agent"


def retrieve_ncr(
    db: Session,
    ncr_number: str,
) -> list[RetrievalEvidence]:

    result = get_ncr(
        db,
        NCRRequest(
            ncr_number=ncr_number,
            role=ROLE,
        ),
    )

    if not result.success or result.data is None:
        return []

    return [
        RetrievalEvidence(
            evidence_id=e.evidence_id,
            source_type=e.source_type,
            source_id=e.source_id,
            retrieval_method="structured",
            title=f"NCR {result.data.ncr_number}",
            content=result.data.description,
            metadata={
                "severity": result.data.severity,
                "status": result.data.status,
            },
            provenance={
                "table": e.provenance.table,
                "record_id": e.provenance.record_id,
                "query_scope": e.provenance.query_scope,
            },
        )
        for e in result.evidence
    ]


def retrieve_product(
    db: Session,
    product_code: str,
) -> list[RetrievalEvidence]:

    result = get_product(
        db,
        ProductRequest(
            product_code=product_code,
            role=ROLE,
        ),
    )

    if not result.success or result.data is None:
        return []

    return [
        RetrievalEvidence(
            evidence_id=e.evidence_id,
            source_type=e.source_type,
            source_id=e.source_id,
            retrieval_method="structured",
            title=result.data.name,
            content=result.data.description,
            metadata={
                "product_code": result.data.product_code,
                "revision": result.data.revision,
            },
            provenance={
                "table": e.provenance.table,
                "record_id": e.provenance.record_id,
                "query_scope": e.provenance.query_scope,
            },
        )
        for e in result.evidence
    ]