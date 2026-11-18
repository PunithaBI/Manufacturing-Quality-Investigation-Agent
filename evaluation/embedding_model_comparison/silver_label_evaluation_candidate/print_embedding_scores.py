
import json
from pathlib import Path

p = Path("silver_evaluation_report.json")
data = json.loads(p.read_text(encoding="utf-8"))

print("Model                 | P@5     | R@10    | MRR     | NDCG@10  | Runtime")
print("-" * 85)

for m in data["methods"]:
    a = m.get("macro_average", {})
    print(
        f'{m.get("method", "?"):22} | '
        f'{a.get("precision_at_5", "N/A")!s:7} | '
        f'{a.get("recall_at_10", "N/A")!s:7} | '
        f'{a.get("mrr", "N/A")!s:7} | '
        f'{a.get("ndcg_at_10_graded", "N/A")!s:8} | '
        f'{m.get("runtime_seconds", "N/A")}'
    )
