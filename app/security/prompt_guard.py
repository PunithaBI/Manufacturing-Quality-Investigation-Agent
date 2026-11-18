from __future__ import annotations

import re


INJECTION_PATTERNS = [
    r"ignore\s+(all|any|previous|prior)\s+instructions",
    r"disregard\s+(all|any|previous|prior)\s+instructions",
    r"system\s+prompt",
    r"developer\s+message",
    r"reveal\s+(your|the)\s+(instructions|prompt)",
    r"show\s+(me\s+)?your\s+prompt",
    r"jailbreak",
    r"bypass\s+(security|authorization|validation)",
    r"execute\s+arbitrary\s+(sql|code|commands?)",
    r"drop\s+table",
]


def detect_prompt_injection(text: str) -> tuple[bool, list[str]]:
    if not isinstance(text, str):
        return False, ["Input must be a string."]

    normalized = text.strip().lower()

    if not normalized:
        return True, []

    matches: list[str] = []

    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, normalized):
            matches.append(pattern)

    return not matches, matches