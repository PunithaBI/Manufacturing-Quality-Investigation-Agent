
import json
from pathlib import Path

REPORT = Path("silver_evaluation_report.json")

def describe(value, depth=0, max_depth=3):
    """Print structure and metric names without dumping the full report."""
    indent = "  " * depth

    if isinstance(value, dict):
        print(f"{indent}Object with {len(value)} keys:")
        for key, item in list(value.items())[:35]:
            if depth >= max_depth:
                print(f"{indent}  {key}: <nested content omitted>")
            elif isinstance(item, dict):
                print(f"{indent}  {key}:")
                describe(item, depth + 2, max_depth)
            elif isinstance(item, list):
                print(f"{indent}  {key}: list ({len(item)} items)")
                if item and depth < max_depth:
                    describe(item[0], depth + 2, max_depth)
            elif isinstance(item, (str, int, float, bool)) or item is None:
                text = repr(item)
                print(f"{indent}  {key}: {text[:180]}")
            else:
                print(f"{indent}  {key}: {type(item).__name__}")
        if len(value) > 35:
            print(f"{indent}  ... {len(value) - 35} more keys")
    elif isinstance(value, list):
        print(f"{indent}List with {len(value)} items")
        if value:
            describe(value[0], depth + 1, max_depth)
    else:
        print(f"{indent}{type(value).__name__}: {str(value)[:180]}")

def main():
    if not REPORT.exists():
        print("REPORT NOT FOUND")
        print("Current working directory:", Path.cwd())
        print("Expected report path:", REPORT.resolve())
        print("Run this script from your project root.")
        return

    try:
        data = json.loads(REPORT.read_text(encoding="utf-8"))
    except Exception as exc:
        print("Could not read JSON:", repr(exc))
        return

    print("=== REPORT STRUCTURE ===")
    describe(data)

    print("\n=== MODEL/METHOD SUMMARY ===")
    methods = data.get("methods", []) if isinstance(data, dict) else []

    if isinstance(methods, dict):
        methods = [
            {"name": name, **details}
            if isinstance(details, dict)
            else {"name": name, "result": details}
            for name, details in methods.items()
        ]

    if not isinstance(methods, list) or not methods:
        print("No methods list found. Check the report structure above.")
        return

    for method in methods:
        if not isinstance(method, dict):
            print("Unexpected method entry:", type(method).__name__)
            continue

        print("\nMethod:", method.get(
            "name",
            method.get("method", method.get("model", "<name field not found>"))
        ))
        print("Available fields:", list(method.keys()))

        for key in (
            "metrics", "aggregate_metrics", "summary",
            "per_case", "case_results", "query_results",
            "results_by_case", "results"
        ):
            if key in method:
                value = method[key]
                if isinstance(value, dict):
                    print(f"  {key} keys:", list(value.keys())[:40])
                    if key in ("metrics", "aggregate_metrics", "summary"):
                        print("  ", key, "values:", {
                            k: v for k, v in list(value.items())[:25]
                            if isinstance(v, (int, float, str, bool))
                            or v is None
                        })
                elif isinstance(value, list):
                    print(f"  {key}: {len(value)} entries")
                    if value and isinstance(value[0], dict):
                        print("  First entry fields:", list(value[0].keys()))
                        print("  First entry sample:", {
                            k: v for k, v in list(value[0].items())[:12]
                            if isinstance(v, (int, float, str, bool))
                            or v is None
                        })
                else:
                    print(f"  {key}:", repr(value)[:200])

if __name__ == "__main__":
    main()
