from __future__ import annotations

from sqlalchemy.orm import Session

from app.db import models

from .documents import ManufacturingDocument
from .ingestion import VectorIngestionService


class ManufacturingDatabaseIngestion:
    """
    Build the semantic RAG corpus from the NordWind database.

    Current sources:

        NCR
        8D
        RCA
        CAPA
        Inspection
        ProcessMeasurement
        ManufacturingOrder
        Operation

    The relational database remains the system of record.

    The vector index is only a retrieval projection.
    """

    def __init__(
        self,
        *,
        ingestion_service: VectorIngestionService | None = None,
        index_directory: str = "data/vector_index",
    ) -> None:

        self.ingestion_service = (
            ingestion_service
            or VectorIngestionService(
                index_directory=index_directory,
            )
        )

    def ingest_all(
        self,
        db: Session,
        *,
        ncr_limit: int = 500,
        eight_d_limit: int = 500,
        rca_limit: int = 500,
        capa_limit: int = 500,
        inspection_limit: int = 1000,
        measurement_limit: int = 2000,
        manufacturing_order_limit: int = 500,
        operation_limit: int = 1000,
    ) -> dict[str, int]:

        documents: list[ManufacturingDocument] = []

        documents.extend(
            self._load_ncrs(
                db,
                limit=ncr_limit,
            )
        )

        documents.extend(
            self._load_8d_reports(
                db,
                limit=eight_d_limit,
            )
        )

        documents.extend(
            self._load_rcas(
                db,
                limit=rca_limit,
            )
        )

        documents.extend(
            self._load_capas(
                db,
                limit=capa_limit,
            )
        )

        documents.extend(
            self._load_inspections(
                db,
                limit=inspection_limit,
            )
        )

        documents.extend(
            self._load_process_measurements(
                db,
                limit=measurement_limit,
            )
        )

        documents.extend(
            self._load_manufacturing_orders(
                db,
                limit=manufacturing_order_limit,
            )
        )

        documents.extend(
            self._load_operations(
                db,
                limit=operation_limit,
            )
        )

        chunk_count = self.ingestion_service.ingest(
            documents
        )

        return {
            "documents": len(documents),
            "chunks": chunk_count,
        }

    # =============================================================
    # NCR
    # =============================================================

    def _load_ncrs(
        self,
        db: Session,
        *,
        limit: int,
    ) -> list[ManufacturingDocument]:

        rows = (
            db.query(models.NCR)
            .order_by(models.NCR.id)
            .limit(limit)
            .all()
        )

        documents: list[ManufacturingDocument] = []

        for row in rows:

            parts: list[str] = []

            self._append_field(
                parts,
                "NCR description",
                row,
                ["description"],
            )

            self._append_field(
                parts,
                "Severity",
                row,
                ["severity"],
            )

            self._append_field(
                parts,
                "Status",
                row,
                ["status"],
            )

            self._append_field(
                parts,
                "Disposition",
                row,
                ["disposition"],
            )

            content = "\n".join(parts).strip()

            if not content:
                continue

            ncr_number = self._first_value(
                row,
                [
                    "ncr_number",
                    "number",
                    "id",
                ],
            )

            documents.append(
                ManufacturingDocument(
                    document_id=f"ncr:{ncr_number}",
                    source_type="ncr",
                    source_id=str(ncr_number),
                    title=f"NCR {ncr_number}",
                    content=content,
                    metadata={
                        "record_id": row.id,
                        "severity": getattr(
                            row,
                            "severity",
                            None,
                        ),
                        "status": getattr(
                            row,
                            "status",
                            None,
                        ),
                    },
                    provenance={
                        "table": "ncrs",
                        "record_id": row.id,
                        "query_scope": (
                            "database_ingestion"
                        ),
                    },
                )
            )

        return documents

    # =============================================================
    # 8D
    # =============================================================

    def _load_8d_reports(
        self,
        db: Session,
        *,
        limit: int,
    ) -> list[ManufacturingDocument]:

        rows = (
            db.query(models.EightDReport)
            .order_by(models.EightDReport.id)
            .limit(limit)
            .all()
        )

        documents: list[ManufacturingDocument] = []

        for row in rows:

            parts: list[str] = []

            self._append_field(
                parts,
                "Problem description",
                row,
                [
                    "d2_problem_description",
                    "description",
                    "problem",
                ],
            )

            self._append_field(
                parts,
                "Containment",
                row,
                [
                    "d3_containment_action",
                    "containment_action",
                ],
            )

            self._append_field(
                parts,
                "Root cause",
                row,
                [
                    "d4_root_cause",
                    "cause",
                ],
            )

            self._append_field(
                parts,
                "Corrective action",
                row,
                [
                    "d5_corrective_action",
                    "corrective_actions",
                ],
            )

            self._append_field(
                parts,
                "Preventive action",
                row,
                [
                    "d7_prevention",
                    "preventive_actions",
                ],
            )

            self._append_field(
                parts,
                "Corrective action implementation",
                row,
                [
                    "d6_implementation",
                    "investigation_findings",
                ],
            )

            self._append_field(
                parts,
                "Conclusion",
                row,
                [
                    "d8_closure",
                    "closure",
                ],
            )

            content = "\n".join(parts).strip()

            if not content:
                continue

            identifier = self._first_value(
                row,
                [
                    "report_number",
                    "eight_d_number",
                    "number",
                    "id",
                ],
            )

            documents.append(
                ManufacturingDocument(
                    document_id=f"8d:{identifier}",
                    source_type="8d",
                    source_id=str(identifier),
                    title=f"8D Report {identifier}",
                    content=content,
                    metadata={
                        "record_id": row.id,
                    },
                    provenance={
                        "table": "eight_d_reports",
                        "record_id": row.id,
                        "query_scope": (
                            "database_ingestion"
                        ),
                    },
                )
            )

        return documents

    # =============================================================
    # RCA
    # =============================================================

    def _load_rcas(
        self,
        db: Session,
        *,
        limit: int,
    ) -> list[ManufacturingDocument]:

        rows = (
            db.query(models.RCA)
            .order_by(models.RCA.id)
            .limit(limit)
            .all()
        )

        documents: list[ManufacturingDocument] = []

        for row in rows:

            parts: list[str] = []

            self._append_field(
                parts,
                "Root cause",
                row,
                [
                    "root_cause_description",
                    "cause",
                    "description",
                ],
            )

            self._append_field(
                parts,
                "Analysis",
                row,
                [
                    "contributing_factors",
                    "findings",
                ],
            )

            content = "\n".join(parts).strip()

            if not content:
                continue

            identifier = self._first_value(
                row,
                [
                    "rca_number",
                    "report_number",
                    "number",
                    "id",
                ],
            )

            documents.append(
                ManufacturingDocument(
                    document_id=f"rca:{identifier}",
                    source_type="rca",
                    source_id=str(identifier),
                    title=f"RCA {identifier}",
                    content=content,
                    metadata={
                        "record_id": row.id,
                    },
                    provenance={
                        "table": "rca",
                        "record_id": row.id,
                        "query_scope": (
                            "database_ingestion"
                        ),
                    },
                )
            )

        return documents

    # =============================================================
    # CAPA
    # =============================================================

    def _load_capas(
        self,
        db: Session,
        *,
        limit: int,
    ) -> list[ManufacturingDocument]:

        rows = (
            db.query(models.CAPA)
            .order_by(models.CAPA.id)
            .limit(limit)
            .all()
        )

        documents: list[ManufacturingDocument] = []

        for row in rows:

            parts: list[str] = []

            self._append_field(
                parts,
                "Corrective action",
                row,
                [
                    "corrective_action",
                    "corrective_actions",
                    "description",
                ],
            )

            self._append_field(
                parts,
                "Preventive action",
                row,
                [
                    "preventive_action",
                    "preventive_actions",
                ],
            )

            self._append_field(
                parts,
                "Action status",
                row,
                ["status"],
            )

            content = "\n".join(parts).strip()

            if not content:
                continue

            identifier = self._first_value(
                row,
                [
                    "capa_number",
                    "report_number",
                    "number",
                    "id",
                ],
            )

            documents.append(
                ManufacturingDocument(
                    document_id=f"capa:{identifier}",
                    source_type="capa",
                    source_id=str(identifier),
                    title=f"CAPA {identifier}",
                    content=content,
                    metadata={
                        "record_id": row.id,
                    },
                    provenance={
                        "table": "capa",
                        "record_id": row.id,
                        "query_scope": (
                            "database_ingestion"
                        ),
                    },
                )
            )

        return documents

    # =============================================================
    # INSPECTIONS
    # =============================================================

    def _load_inspections(
        self,
        db: Session,
        *,
        limit: int,
    ) -> list[ManufacturingDocument]:

        rows = (
            db.query(models.Inspection)
            .order_by(models.Inspection.id)
            .limit(limit)
            .all()
        )

        documents: list[ManufacturingDocument] = []

        for row in rows:

            parts: list[str] = []

            self._append_all_available_fields(
                parts,
                row,
                [
                    "inspection_number",
                    "inspection_type",
                    "result",
                    "status",
                    "description",
                    "measurement",
                    "value",
                    "specification",
                    "lower_limit",
                    "upper_limit",
                    "remarks",
                ],
            )

            content = "\n".join(parts).strip()

            if not content:
                continue

            identifier = self._first_value(
                row,
                [
                    "inspection_number",
                    "number",
                    "id",
                ],
            )

            documents.append(
                ManufacturingDocument(
                    document_id=f"inspection:{identifier}",
                    source_type="inspection",
                    source_id=str(identifier),
                    title=f"Inspection {identifier}",
                    content=content,
                    metadata={
                        "record_id": row.id,
                    },
                    provenance={
                        "table": "inspections",
                        "record_id": row.id,
                        "query_scope": (
                            "database_ingestion"
                        ),
                    },
                )
            )

        return documents

    # =============================================================
    # PROCESS MEASUREMENTS
    # =============================================================

    def _load_process_measurements(
        self,
        db: Session,
        *,
        limit: int,
    ) -> list[ManufacturingDocument]:

        rows = (
            db.query(models.ProcessMeasurement)
            .order_by(models.ProcessMeasurement.id)
            .limit(limit)
            .all()
        )

        documents: list[ManufacturingDocument] = []

        for row in rows:

            parts: list[str] = []

            self._append_all_available_fields(
                parts,
                row,
              [
                    "parameter_name",
                    "nominal_value",
                    "actual_value",
                    "unit",
                    "lsl",
                    "usl",
                    "in_spec",
                    "measured_at",
                ]
            )

            content = "\n".join(parts).strip()

            if not content:
                continue

            identifier = self._first_value(
                row,
                [
                    "measurement_number",
                    "number",
                    "id",
                ],
            )

            documents.append(
                ManufacturingDocument(
                    document_id=(
                        f"process_measurement:"
                        f"{identifier}"
                    ),
                    source_type="process_measurement",
                    source_id=str(identifier),
                    title=(
                        f"Process Measurement "
                        f"{identifier}"
                    ),
                    content=content,
                    metadata={
                        "record_id": row.id,
                    },
                    provenance={
                        "table": "process_measurements",
                        "record_id": row.id,
                        "query_scope": (
                            "database_ingestion"
                        ),
                    },
                )
            )

        return documents

    # =============================================================
    # MANUFACTURING ORDERS
    # =============================================================

    def _load_manufacturing_orders(
        self,
        db: Session,
        *,
        limit: int,
    ) -> list[ManufacturingDocument]:

        rows = (
            db.query(models.ManufacturingOrder)
            .order_by(models.ManufacturingOrder.id)
            .limit(limit)
            .all()
        )

        documents: list[ManufacturingDocument] = []

        for row in rows:

            parts: list[str] = []

            self._append_all_available_fields(
                parts,
                row,
                [
                    "order_number",
                    "status",
                    "quantity",
                    "planned_quantity",
                    "actual_quantity",
                    "start_date",
                    "end_date",
                    "description",
                ],
            )

            content = "\n".join(parts).strip()

            if not content:
                continue

            identifier = self._first_value(
                row,
                [
                    "order_number",
                    "number",
                    "id",
                ],
            )

            documents.append(
                ManufacturingDocument(
                    document_id=(
                        f"manufacturing_order:"
                        f"{identifier}"
                    ),
                    source_type="manufacturing_order",
                    source_id=str(identifier),
                    title=(
                        f"Manufacturing Order "
                        f"{identifier}"
                    ),
                    content=content,
                    metadata={
                        "record_id": row.id,
                    },
                    provenance={
                        "table": "manufacturing_orders",
                        "record_id": row.id,
                        "query_scope": (
                            "database_ingestion"
                        ),
                    },
                )
            )

        return documents

    # =============================================================
    # OPERATIONS
    # =============================================================

    def _load_operations(
        self,
        db: Session,
        *,
        limit: int,
    ) -> list[ManufacturingDocument]:

        rows = (
            db.query(models.Operation)
            .order_by(models.Operation.id)
            .limit(limit)
            .all()
        )

        documents: list[ManufacturingDocument] = []

        for row in rows:

            parts: list[str] = []

            self._append_all_available_fields(
                parts,
                row,
                [
                    "operation_number",
                    "operation_code",
                    "name",
                    "description",
                    "work_center",
                    "status",
                ],
            )

            content = "\n".join(parts).strip()

            if not content:
                continue

            identifier = self._first_value(
                row,
                [
                    "operation_number",
                    "operation_code",
                    "number",
                    "id",
                ],
            )

            documents.append(
                ManufacturingDocument(
                    document_id=f"operation:{identifier}",
                    source_type="operation",
                    source_id=str(identifier),
                    title=f"Operation {identifier}",
                    content=content,
                    metadata={
                        "record_id": row.id,
                    },
                    provenance={
                        "table": "operations",
                        "record_id": row.id,
                        "query_scope": (
                            "database_ingestion"
                        ),
                    },
                )
            )

        return documents

    # =============================================================
    # HELPERS
    # =============================================================

    @staticmethod
    def _first_value(
        row,
        field_names: list[str],
    ):

        for field_name in field_names:

            if not hasattr(row, field_name):
                continue

            value = getattr(
                row,
                field_name,
            )

            if value is not None:
                return value

        return None

    @staticmethod
    def _append_field(
        output: list[str],
        label: str,
        row,
        field_names: list[str],
    ) -> None:

        value = (
            ManufacturingDatabaseIngestion
            ._first_value(
                row,
                field_names,
            )
        )

        if value is None:
            return

        text = str(value).strip()

        if text:
            output.append(
                f"{label}: {text}"
            )

    @staticmethod
    def _append_all_available_fields(
        output: list[str],
        row,
        field_names: list[str],
    ) -> None:

        for field_name in field_names:

            if not hasattr(row, field_name):
                continue

            value = getattr(
                row,
                field_name,
            )

            if value is None:
                continue

            text = str(value).strip()

            if not text:
                continue

            label = field_name.replace(
                "_",
                " ",
            ).title()

            output.append(
                f"{label}: {text}"
            )