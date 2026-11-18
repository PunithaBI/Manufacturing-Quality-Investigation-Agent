from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from app.agents.models import RCAAnalysis


load_dotenv()


class LLMProviderError(Exception):
    """Base error for LLM provider failures."""


class LLMProviderUnavailable(LLMProviderError):
    """Provider cannot currently serve the request."""


class LLMProvider(ABC):
    """
    Common contract for all LLM providers.

    The rest of the application depends on this contract,
    not on a specific provider.
    """

    name: str

    @abstractmethod
    def analyze(
        self,
        *,
        problem_statement: str,
        evidence: list[dict[str, Any]],
        evidence_gaps: list[str],
    ) -> RCAAnalysis:
        """Produce a validated RCAAnalysis from controlled evidence."""
        raise NotImplementedError


def _build_prompt(
    *,
    problem_statement: str,
    evidence: list[dict[str, Any]],
    evidence_gaps: list[str],
) -> str:
    """
    Build the controlled RCA prompt.

    The LLM receives investigation evidence only.
    It does not receive database access or tool access.
    """

    return f"""
You are a manufacturing quality investigation analyst.

Your task is to analyze the supplied investigation evidence and
produce an evidence-grounded preliminary RCA.

IMPORTANT RULES:
- Use only the supplied evidence.
- Do not invent facts.
- Do not claim a root cause unless supported by evidence.
- Clearly distinguish potential causes from confirmed facts.
- If evidence is insufficient, say so.
- Do not redesign the product.
- Do not claim that a physical product improvement has already occurred.
- Recommendations must be suitable for HUMAN_REVIEW.
- Return ONLY valid JSON.
- Do not use Markdown code fences.

Required JSON structure:

{{
  "status": "PARTIAL",
  "problem_statement": "...",
  "potential_causes": [
    {{
      "cause": "...",
      "confidence": "LOW",
      "basis": "..."
    }}
  ],
  "supporting_evidence": [],
  "contradictory_evidence": [],
  "evidence_gaps": [],
  "recommended_next_steps": [],
  "conclusion": "..."
}}

For every item in "potential_causes":
- It MUST be a JSON object, never a plain string.
- "cause" must describe a potential cause or hypothesis.
- "confidence" must be one of: "LOW", "MEDIUM", "HIGH".
- "basis" must explain why the supplied evidence supports, weakly supports,
  or does not yet confirm the potential cause.
- Do not present an unverified potential cause as a confirmed root cause.
- If evidence is insufficient, use LOW confidence and clearly state that
  engineering verification is required.

INVESTIGATION PROBLEM:
{problem_statement}

SUPPLIED EVIDENCE:
{json.dumps(evidence, ensure_ascii=False, default=str)}

KNOWN EVIDENCE GAPS:
{json.dumps(evidence_gaps, ensure_ascii=False)}
""".strip()


def _parse_rca_response(content: str) -> RCAAnalysis:
    """Parse and validate provider output as RCAAnalysis."""

    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise LLMProviderError(
            "LLM returned invalid JSON."
        ) from exc

    try:
        return RCAAnalysis.model_validate(payload)
    except Exception as exc:
        raise LLMProviderError(
            "LLM returned JSON that does not match RCAAnalysis."
        ) from exc


class MistralProvider(LLMProvider):
    """Mistral provider using the OpenAI-compatible API."""

    name = "mistral"

    def __init__(self) -> None:
        api_key = os.getenv("MISTRAL_API_KEY", "")
        base_url = os.getenv(
            "MISTRAL_BASE_URL",
            "https://api.mistral.ai/v1",
        )
        model = os.getenv(
            "MISTRAL_MODEL",
            "mistral-small-latest",
        )

        if not api_key:
            raise LLMProviderUnavailable(
                "MISTRAL_API_KEY is not configured."
            )

        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        self.model = model

    def analyze(
        self,
        *,
        problem_statement: str,
        evidence: list[dict[str, Any]],
        evidence_gaps: list[str],
    ) -> RCAAnalysis:

        prompt = _build_prompt(
            problem_statement=problem_statement,
            evidence=evidence,
            evidence_gaps=evidence_gaps,
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )
        except Exception as exc:
            raise LLMProviderUnavailable(
                f"Mistral request failed: {exc}"
            ) from exc

        content = response.choices[0].message.content

        if not content:
            raise LLMProviderError(
                "Mistral returned an empty response."
            )

        return _parse_rca_response(content)


class GeminiProvider(LLMProvider):
    """Google Gemini provider using the OpenAI-compatible API."""

    name = "gemini"

    def __init__(self) -> None:
        api_key = os.getenv("GEMINI_API_KEY", "")
        base_url = os.getenv(
            "GEMINI_BASE_URL",
            "https://generativelanguage.googleapis.com/v1beta/openai/",
        )
        model = os.getenv(
            "GEMINI_MODEL",
            "gemini-3.8-flash",
        )

        if not api_key:
            raise LLMProviderUnavailable(
                "GEMINI_API_KEY is not configured."
            )

        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        self.model = model

    def analyze(
        self,
        *,
        problem_statement: str,
        evidence: list[dict[str, Any]],
        evidence_gaps: list[str],
    ) -> RCAAnalysis:

        prompt = _build_prompt(
            problem_statement=problem_statement,
            evidence=evidence,
            evidence_gaps=evidence_gaps,
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )
        except Exception as exc:
            raise LLMProviderUnavailable(
                f"Gemini request failed: {exc}"
            ) from exc

        content = response.choices[0].message.content

        if not content:
            raise LLMProviderError(
                "Gemini returned an empty response."
            )

        return _parse_rca_response(content)


class LLMRouter:
    """
    Selects an available LLM provider and falls back to the next
    provider when a provider is unavailable.
    """

    def __init__(self, providers: list[LLMProvider]) -> None:
        if not providers:
            raise ValueError(
                "At least one LLM provider is required."
            )

        self.providers = providers

    def analyze(
        self,
        *,
        problem_statement: str,
        evidence: list[dict[str, Any]],
        evidence_gaps: list[str],
    ) -> RCAAnalysis:

        errors: list[str] = []

        for provider in self.providers:
            try:
                return provider.analyze(
                    problem_statement=problem_statement,
                    evidence=evidence,
                    evidence_gaps=evidence_gaps,
                )

            except LLMProviderUnavailable as exc:
                errors.append(
                    f"{provider.name}: unavailable - {exc}"
                )
                continue

            except LLMProviderError as exc:
                errors.append(
                    f"{provider.name}: provider error - {exc}"
                )
                continue

        raise LLMProviderUnavailable(
            "No configured LLM provider could complete the request. "
            + " | ".join(errors)
        )