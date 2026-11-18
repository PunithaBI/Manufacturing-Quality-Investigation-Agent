from __future__ import annotations

from sqlalchemy.orm import Session

from app.db import models

from .models import RetrievalEvidence
from app.tools.evidence import create_evidence_id

def search_ncr_keywords(
    db: Session,
    query: str,
    limit: int = 20,
) -> list[RetrievalEvidence]:

    query = query.strip()

    if not query:
        return []

    rows = (
        db.query(models.NCR)
        .filter(models.NCR.description.ilike(f"%{query}%"))
        .limit(limit)
        .all()
    )

    results: list[RetrievalEvidence] = []

    for row in rows:
        results.append(
            RetrievalEvidence(
                evidence_id=create_evidence_id(source_type="ncr",source_id=row.ncr_number,),
                source_type="ncr",
                source_id=row.ncr_number,
                retrieval_method="keyword",
                title=f"NCR {row.ncr_number}",
                content=row.description,
                score=1.0,
                provenance={
                    "table": "ncrs",
                    "record_id": row.id,
                    "query_scope": query,
                },
            )
        )

    return results