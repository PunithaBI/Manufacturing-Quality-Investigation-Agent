from __future__ import annotations

from .models import (
    AgentStatus,
    EvidencePackage,
    RCAAnalysis,
    ReviewResult,
    TraceabilityResult,
)


class InvestigationReviewer:
    """
    Validates the investigation package before HUMAN REVIEW.

    The reviewer does not approve the investigation itself.
    It determines whether the package is sufficiently complete
    and traceable to be presented to a human reviewer.
    """

    def run(
        self,
        traceability: TraceabilityResult,
        evidence: EvidencePackage,
        rca: RCAAnalysis,
    ) -> ReviewResult:

        checks: dict[str, bool] = {}
        issues: list[str] = []
        warnings: list[str] = []

        # ------------------------------------------------------
        # 1. Traceability check
        # ------------------------------------------------------

        traceability_ok = (
            traceability.status
            in (
                AgentStatus.SUCCESS,
                AgentStatus.PARTIAL,
            )
            and bool(traceability.ncr_number)
        )

        checks["traceability_available"] = traceability_ok

        if not traceability_ok:
            issues.append(
                "Traceability information is unavailable or invalid."
            )

        # ------------------------------------------------------
        # 2. Evidence check
        # ------------------------------------------------------

        evidence_available = bool(
            evidence.evidence
        )

        checks["evidence_available"] = evidence_available

        if not evidence_available:
            issues.append(
                "No investigation evidence was retrieved."
            )

        # ------------------------------------------------------
        # 3. Evidence provenance check
        # ------------------------------------------------------

        provenance_ok = self._has_provenance(
            evidence
        )

        checks["evidence_provenance"] = provenance_ok

        if not provenance_ok:
            issues.append(
                "One or more evidence items do not contain "
                "sufficient provenance."
            )

        # ------------------------------------------------------
        # 4. RCA check
        # ------------------------------------------------------

        rca_available = (
            rca.status
            in (
                AgentStatus.SUCCESS,
                AgentStatus.PARTIAL,
            )
            and bool(
                rca.problem_statement
            )
        )

        checks["rca_available"] = rca_available

        if not rca_available:
            issues.append(
                "RCA analysis is unavailable or invalid."
            )

        # ------------------------------------------------------
        # 5. Confirmed root-cause guard
        # ------------------------------------------------------

        if rca.status == AgentStatus.PARTIAL:
            warnings.append(
                "RCA is preliminary. No confirmed root cause "
                "should be treated as established."
            )

        # ------------------------------------------------------
        # Final decision
        # ------------------------------------------------------

        approved_for_hitl = (
            not issues
        )

        if approved_for_hitl:
            status = AgentStatus.SUCCESS

            reviewer_summary = (
                "Investigation package passed automated "
                "review checks and is ready for HUMAN REVIEW."
            )

        else:
            status = AgentStatus.BLOCKED

            reviewer_summary = (
                "Investigation package did not pass automated "
                "review checks and requires correction before "
                "HUMAN REVIEW."
            )

        return ReviewResult(
            status=status,
            approved_for_hitl=approved_for_hitl,
            checks=checks,
            issues=issues,
            warnings=warnings,
            reviewer_summary=reviewer_summary,
        )

    @staticmethod
    def _has_provenance(
        evidence: EvidencePackage,
    ) -> bool:

        if not evidence.evidence:
            return False

        for item in evidence.evidence:

            # EvidencePackage.evidence is intentionally
            # serialized as dictionaries.
            provenance = item.get(
                "provenance"
            )

            if not provenance:
                return False

            if not provenance.get(
                "table"
            ):
                return False

            if not provenance.get(
                "record_id"
            ):
                return False

        return True