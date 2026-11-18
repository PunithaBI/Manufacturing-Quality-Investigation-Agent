from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BASELINE_FILE = ROOT / "baseline" / "baseline.json"


def save_baseline(report: dict) -> None:
    BASELINE_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with BASELINE_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            report,
            file,
            indent=2,
        )


def load_baseline() -> dict | None:
    if not BASELINE_FILE.exists():
        return None

    with BASELINE_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def compare_with_baseline(
    current: dict,
    baseline: dict,
) -> dict:

    current_cases = {
        case["case_id"]: case
        for case in current.get("cases", [])
    }

    baseline_cases = {
        case["case_id"]: case
        for case in baseline.get("cases", [])
    }

    regressions: list[str] = []

    for case_id, baseline_case in baseline_cases.items():

        current_case = current_cases.get(case_id)

        if current_case is None:
            regressions.append(
                f"{case_id}: case missing from current evaluation"
            )
            continue

        if baseline_case["passed"] and not current_case["passed"]:
            regressions.append(
                f"{case_id}: previously passing case now fails"
            )

    baseline_passed = baseline.get(
        "evaluation",
        {},
    ).get(
        "passed",
        0,
    )

    current_passed = current.get(
        "evaluation",
        {},
    ).get(
        "passed",
        0,
    )

    return {
        "regression_pass": not regressions,
        "baseline_passed": baseline_passed,
        "current_passed": current_passed,
        "new_regressions": regressions,
    }