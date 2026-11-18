from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from typing import Any


BASE_URL = "http://localhost:8000"


class SmokeTestFailure(Exception):
    """Raised when a production smoke test fails."""


def get_json(
    path: str,
    *,
    expected_status: int = 200,
) -> dict[str, Any]:

    url = f"{BASE_URL}{path}"

    try:
        with urllib.request.urlopen(
            url,
            timeout=10,
        ) as response:

            status = response.status
            body = response.read().decode(
                "utf-8"
            )

    except urllib.error.HTTPError as exc:

        body = exc.read().decode(
            "utf-8",
            errors="replace",
        )

        raise SmokeTestFailure(
            f"{path}: HTTP {exc.code} - {body}"
        ) from exc

    except urllib.error.URLError as exc:

        raise SmokeTestFailure(
            f"{path}: connection failed - {exc.reason}"
        ) from exc

    except Exception as exc:

        raise SmokeTestFailure(
            f"{path}: request failed - {exc}"
        ) from exc

    if status != expected_status:

        raise SmokeTestFailure(
            f"{path}: expected HTTP "
            f"{expected_status}, got {status}"
        )

    try:
        return json.loads(body)

    except json.JSONDecodeError as exc:

        raise SmokeTestFailure(
            f"{path}: response is not valid JSON"
        ) from exc


def test_health() -> None:

    result = get_json("/health")

    if result.get("status") != "healthy":

        raise SmokeTestFailure(
            f"/health returned unexpected result: "
            f"{result}"
        )

    print("PASS  /health")


def test_readiness() -> None:

    result = get_json("/readiness")

    if result.get("status") != "ready":

        raise SmokeTestFailure(
            f"/readiness is not ready: {result}"
        )

    checks = result.get(
        "checks",
        {},
    )

    if checks.get("database") != "ready":

        raise SmokeTestFailure(
            "Database readiness check failed: "
            f"{checks}"
        )

    print("PASS  /readiness")
    print(
        f"      database={checks.get('database')}"
    )


def test_database_info() -> None:

    result = get_json(
        "/database/info"
    )

    if result.get("status") != "connected":

        raise SmokeTestFailure(
            f"/database/info is not connected: "
            f"{result}"
        )

    tables = result.get(
        "tables",
        [],
    )

    required_tables = {
        "investigations",
        "investigation_trace_events",
        "investigation_audit_records",
    }

    missing = (
        required_tables
        - set(tables)
    )

    if missing:

        raise SmokeTestFailure(
            "Required investigation tables "
            f"are missing: {sorted(missing)}"
        )

    print("PASS  /database/info")

    print(
        f"      tables={len(tables)}"
    )


def test_docs() -> None:

    url = f"{BASE_URL}/docs"

    try:

        with urllib.request.urlopen(
            url,
            timeout=10,
        ) as response:

            if response.status != 200:

                raise SmokeTestFailure(
                    f"/docs returned HTTP "
                    f"{response.status}"
                )

    except Exception as exc:

        if isinstance(
            exc,
            SmokeTestFailure,
        ):
            raise

        raise SmokeTestFailure(
            f"/docs request failed: {exc}"
        ) from exc

    print("PASS  /docs")


def main() -> int:

    print(
        "========================================"
    )
    print(
        "MQI PRODUCTION SMOKE TEST"
    )
    print(
        "========================================"
    )
    print()

    tests = [
        test_health,
        test_readiness,
        test_database_info,
        test_docs,
    ]

    failures: list[str] = []

    for test in tests:

        try:

            test()

        except SmokeTestFailure as exc:

            print(
                f"FAIL  {test.__name__}: {exc}"
            )

            failures.append(
                str(exc)
            )

    print()

    if failures:

        print(
            "========================================"
        )
        print(
            "SMOKE TEST FAILED"
        )
        print(
            "========================================"
        )

        for failure in failures:
            print(
                f"- {failure}"
            )

        return 1

    print(
        "========================================"
    )
    print(
        "SMOKE TEST PASS"
    )
    print(
        "========================================"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())