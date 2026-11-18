from __future__ import annotations

import json
import sys
from pathlib import Path

from .evaluator import InvestigationEvaluator
from .regression import (
    compare_with_baseline,
    load_baseline,
    save_baseline,
)


ROOT = Path(__file__).resolve().parent
REPORT_FILE = ROOT / "reports" / "latest_report.json"


def main() -> int:

    evaluator = InvestigationEvaluator()

    print()
    print("=" * 60)
    print("MANUFACTURING QUALITY INVESTIGATION EVALUATION")
    print("=" * 60)
    print()

    report = evaluator.run()

    REPORT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    baseline = load_baseline()

    if baseline is None:
        print("No baseline found.")
        print("Creating initial regression baseline.")

        save_baseline(report)

        regression = {
            "regression_pass": True,
            "baseline_created": True,
            "baseline_passed": report["evaluation"]["passed"],
            "current_passed": report["evaluation"]["passed"],
            "new_regressions": [],
        }

    else:
        regression = compare_with_baseline(
            current=report,
            baseline=baseline,
        )

    final_report = {
        **report,
        "regression": regression,
    }

    with REPORT_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            final_report,
            file,
            indent=2,
        )

    evaluation = report["evaluation"]

    print(
        f"Cases : {evaluation['total_cases']}"
    )
    print(
        f"Passed: {evaluation['passed']}"
    )
    print(
        f"Failed: {evaluation['failed']}"
    )
    print(
        f"Rate  : {evaluation['pass_rate']:.2%}"
    )

    print()

    if regression["regression_pass"]:
        print("REGRESSION: PASS")
    else:
        print("REGRESSION: FAIL")

        for item in regression["new_regressions"]:
            print(f"  - {item}")

    print()
    print(
        f"Report: {REPORT_FILE}"
    )
    print()

    if evaluation["failed"] > 0:
        return 1

    if not regression["regression_pass"]:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())