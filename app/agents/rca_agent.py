from __future__ import annotations

from app.llm_provider import (
    GeminiProvider,
    LLMProviderError,
    LLMProviderUnavailable,
    LLMRouter,
    MistralProvider,
)

from .models import (
    AgentStatus,
    EvidencePackage,
    RCAAnalysis,
    TraceabilityResult,
)


class RCAAnalystAgent:
    """
    Performs preliminary evidence-based root-cause analysis.

    Inputs:
        - traceability from the Product/Traceability Agent
        - evidence from the Evidence Retrieval Agent

    The agent prepares controlled evidence context and delegates
    analytical reasoning to the configured LLM router.

    The agent does not claim a confirmed root cause without
    sufficient supporting evidence.
    """

    def __init__(
        self,
        llm_router: LLMRouter | None = None,
    ) -> None:

        self.llm_router = llm_router or LLMRouter(
            [
                MistralProvider(),
                GeminiProvider(),
            ]
        )

    def run(
        self,
        traceability: TraceabilityResult,
        evidence: EvidencePackage,
    ) -> RCAAnalysis:

        problem_statement = self._build_problem_statement(
            traceability
        )

        supporting_evidence = self._extract_supporting_evidence(
            evidence
        )

        evidence_gaps = list(
            evidence.evidence_gaps
        )

        # ------------------------------------------------------
        # Evidence availability guard
        # ------------------------------------------------------

        if not supporting_evidence:

            evidence_gaps.append(
                "No usable evidence content was available "
                "for preliminary RCA."
            )

            return RCAAnalysis(
                status=AgentStatus.PARTIAL,
                problem_statement=problem_statement,
                potential_causes=[],
                supporting_evidence=[],
                contradictory_evidence=[],
                evidence_gaps=evidence_gaps,
                recommended_next_steps=[
                    "Retrieve additional NCR, inspection, "
                    "process, traceability, and historical "
                    "failure evidence.",
                    "Verify affected product and component "
                    "relationships.",
                ],
                conclusion=(
                    "No root cause can be established from "
                    "the currently available evidence."
                ),
            )

        # ------------------------------------------------------
        # LLM RCA analysis
        # ------------------------------------------------------

        try:

            rca = self.llm_router.analyze(
                problem_statement=problem_statement,
                evidence=[
                    {
                        "source_type": item.get(
                            "source_type",
                            "unknown",
                        ),
                        "source_id": item.get(
                            "source_id",
                            "unknown",
                        ),
                        "summary": item.get(
                            "summary",
                            "",
                        ),
                        "content": item.get(
                            "content",
                            "",
                        ),
                        "title": item.get(
                            "title",
                            "",
                        ),
                        "key_facts": item.get(
                            "key_facts",
                            [],
                        ),
                        "provenance": item.get(
                            "provenance",
                            {},
                        ),
                    }
                    for item in evidence.evidence
                ],
                evidence_gaps=evidence_gaps,
            )

        except (
            LLMProviderUnavailable,
            LLMProviderError,
        ) as exc:

            # --------------------------------------------------
            # Safe fallback.
            #
            # Do not manufacture an RCA when the model is
            # unavailable or returns an invalid result.
            # --------------------------------------------------

            evidence_gaps.append(
                f"LLM RCA analysis unavailable: {exc}"
            )

            return RCAAnalysis(
                status=AgentStatus.PARTIAL,
                problem_statement=problem_statement,
                potential_causes=[
                    {
                        "cause": (
                            "Insufficient evidence to establish "
                            "a confirmed root cause."
                        ),
                        "confidence": "LOW",
                        "basis": (
                            "LLM RCA analysis was unavailable. "
                            "Retrieved evidence requires "
                            "engineering review and correlation."
                        ),
                    }
                ],
                supporting_evidence=supporting_evidence,
                contradictory_evidence=[],
                evidence_gaps=evidence_gaps,
                recommended_next_steps=[
                    "Review retrieved evidence with a "
                    "quality or manufacturing engineer.",
                    "Retry RCA analysis when an approved "
                    "LLM provider is available.",
                    "Correlate process measurements and "
                    "inspection results with the affected "
                    "serial unit or manufacturing order.",
                    "Compare the current failure with "
                    "historical NCR and 8D patterns.",
                ],
                conclusion=(
                    "Preliminary evidence has been assembled, "
                    "but automated RCA analysis was unavailable. "
                    "No confirmed root cause is established. "
                    "Human engineering review is required."
                ),
            )

        # ------------------------------------------------------
        # Preserve retrieval evidence independently from LLM
        # ------------------------------------------------------

        rca.supporting_evidence = supporting_evidence

        # Preserve upstream retrieval gaps without duplicates.
        rca.evidence_gaps = list(
            dict.fromkeys(
                evidence_gaps
                + rca.evidence_gaps
            )
        )

        # ------------------------------------------------------
        # Safety normalization
        # ------------------------------------------------------

        if rca.status == AgentStatus.SUCCESS:
            rca.status = AgentStatus.PARTIAL

        if not rca.conclusion:
            rca.conclusion = (
                "Preliminary RCA generated from retrieved evidence. "
                "No confirmed root cause is established without "
                "human engineering review."
            )

        if not rca.recommended_next_steps:
            rca.recommended_next_steps = [
                "Review the RCA with a quality or manufacturing engineer.",
                "Validate the proposed causes against process and "
                "inspection evidence.",
                "Compare the current failure with historical NCR "
                "and 8D patterns.",
            ]

        return rca

    @staticmethod
    def _build_problem_statement(
        traceability: TraceabilityResult,
    ) -> str:

        problem_statement = (
            f"Investigation of NCR {traceability.ncr_number}"
        )

        if traceability.product:

            product_number = (
                traceability.product.get("product_number")
                or traceability.product.get("product_id")
                or traceability.product.get("product_code")
                or "unknown"
            )

            problem_statement += (
                f" | Product: {product_number}"
            )

        if traceability.component:

            component_number = (
                traceability.component.get("component_number")
                or traceability.component.get("component_id")
                or traceability.component.get("component_code")
                or "unknown"
            )

            problem_statement += (
                f" | Component: {component_number}"
            )

        return problem_statement

    @staticmethod
    def _extract_supporting_evidence(
        evidence: EvidencePackage,
    ) -> list[str]:

        supporting_evidence: list[str] = []

        for item in evidence.evidence:

            source_type = item.get(
                "source_type",
                "unknown",
            )

            source_id = item.get(
                "source_id",
                "unknown",
            )

            content = (
                item.get("summary")
                or item.get("content")
                or item.get("title")
                or " ".join(
                    item.get(
                        "key_facts",
                        [],
                    )
                )
                or ""
            )

            if content.strip():

                supporting_evidence.append(
                    f"{source_type}:{source_id} - "
                    f"{content[:500]}"
                )

        return supporting_evidence