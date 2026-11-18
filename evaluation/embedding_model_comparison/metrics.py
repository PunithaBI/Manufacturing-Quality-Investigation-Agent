from __future__ import annotations

import math


def recall_at_k(
    retrieved_ids: list[str],
    relevant_ids: set[str],
    k: int,
) -> float:
    if not relevant_ids:
        return 0.0

    retrieved = retrieved_ids[:k]

    hits = sum(
        1
        for item in retrieved
        if item in relevant_ids
    )

    return hits / len(relevant_ids)


def reciprocal_rank(
    retrieved_ids: list[str],
    relevant_ids: set[str],
) -> float:
    for rank, item in enumerate(
        retrieved_ids,
        start=1,
    ):
        if item in relevant_ids:
            return 1.0 / rank

    return 0.0


def dcg_at_k(
    retrieved_ids: list[str],
    relevant_ids: set[str],
    k: int,
) -> float:
    score = 0.0

    for rank, item in enumerate(
        retrieved_ids[:k],
        start=1,
    ):
        if item in relevant_ids:
            score += 1.0 / math.log2(rank + 1)

    return score


def ndcg_at_k(
    retrieved_ids: list[str],
    relevant_ids: set[str],
    k: int,
) -> float:
    if not relevant_ids:
        return 0.0

    actual_dcg = dcg_at_k(
        retrieved_ids,
        relevant_ids,
        k,
    )

    ideal_count = min(
        len(relevant_ids),
        k,
    )

    ideal_dcg = sum(
        1.0 / math.log2(rank + 1)
        for rank in range(1, ideal_count + 1)
    )

    if ideal_dcg == 0:
        return 0.0

    return actual_dcg / ideal_dcg


def calculate_metrics(
    retrieved_ids: list[str],
    relevant_ids: set[str],
) -> dict[str, float]:

    return {
        "recall_at_5": round(
            recall_at_k(
                retrieved_ids,
                relevant_ids,
                5,
            ),
            4,
        ),
        "recall_at_10": round(
            recall_at_k(
                retrieved_ids,
                relevant_ids,
                10,
            ),
            4,
        ),
        "mrr": round(
            reciprocal_rank(
                retrieved_ids,
                relevant_ids,
            ),
            4,
        ),
        "ndcg_at_10": round(
            ndcg_at_k(
                retrieved_ids,
                relevant_ids,
                10,
            ),
            4,
        ),
    }