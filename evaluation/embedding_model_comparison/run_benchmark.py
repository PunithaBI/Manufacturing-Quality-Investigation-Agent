from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

from .metrics import calculate_metrics


ROOT = Path(__file__).resolve().parents[2]

CORPUS_FILE = (
    ROOT
    / "data"
    / "vector_index"
    / "chunks.json"
)

EXPERIMENT_ROOT = (
    ROOT
    / "data"
    / "embedding_experiments"
)

BENCHMARK_FILE = (
    ROOT
    / "evaluation"
    / "embedding_model_comparison"
    / "benchmark_cases.json"
)


MODELS = {
    "all-MiniLM-L6-v2": {
        "model_name": (
            "sentence-transformers/"
            "all-MiniLM-L6-v2"
        ),
        "query_prefix": "",
        "passage_prefix": "",
    },
    "all-mpnet-base-v2": {
        "model_name": (
            "sentence-transformers/"
            "all-mpnet-base-v2"
        ),
        "query_prefix": "",
        "passage_prefix": "",
    },
    "bge-small-en-v1.5": {
        "model_name": (
            "BAAI/bge-small-en-v1.5"
        ),
        "query_prefix": (
            "Represent this sentence for "
            "searching relevant passages: "
        ),
        "passage_prefix": "",
    },
    "bge-base-en-v1.5": {
        "model_name": (
            "BAAI/bge-base-en-v1.5"
        ),
        "query_prefix": (
            "Represent this sentence for "
            "searching relevant passages: "
        ),
        "passage_prefix": "",
    },
    "e5-base-v2": {
        "model_name": (
            "intfloat/e5-base-v2"
        ),
        "query_prefix": "query: ",
        "passage_prefix": "passage: ",
    },
}


TOP_K = 10


def load_corpus() -> list[dict]:
    with CORPUS_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        chunks = json.load(file)

    if not isinstance(chunks, list):
        raise ValueError(
            "chunks.json must contain a list."
        )

    print(
        f"Corpus chunks: {len(chunks)}"
    )

    return chunks


def load_benchmark() -> dict:
    with BENCHMARK_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def validate_benchmark(
    benchmark: dict,
    chunks: list[dict],
) -> None:

    cases = benchmark.get("cases", [])

    if not cases:
        raise ValueError(
            "No benchmark cases found."
        )

    corpus_ids = {
        chunk["chunk_id"]
        for chunk in chunks
    }

    source_ids = {
        chunk["source_id"]
        for chunk in chunks
    }

    for case in cases:

        relevant_ids = set(
            case.get(
                "relevant_source_ids",
                [],
            )
        )

        if not relevant_ids:
            raise ValueError(
                f"{case['case_id']} has no "
                "ground-truth relevant_source_ids. "
                "Human labeling is required before "
                "the benchmark can run."
            )

        missing = (
            relevant_ids
            - source_ids
            - corpus_ids
        )

        if missing:
            raise ValueError(
                f"{case['case_id']} contains IDs "
                f"not found in the corpus: "
                f"{sorted(missing)}"
            )


def embedding_text(chunk: dict) -> str:
    metadata = chunk.get(
        "metadata",
        {},
    )

    return "\n".join(
        [
            f"Source type: "
            f"{chunk.get('source_type', '')}",
            f"Title: "
            f"{chunk.get('title', '')}",
            f"Section: "
            f"{metadata.get('section', '')}",
            chunk.get(
                "content",
                "",
            ),
        ]
    )


def build_index(
    model_name: str,
    model_config: dict,
    chunks: list[dict],
) -> tuple[
    SentenceTransformer,
    np.ndarray,
    float,
]:

    print()
    print(
        f"Loading model: {model_name}"
    )

    model = SentenceTransformer(
        model_config["model_name"]
    )

    texts = [
        (
            model_config["passage_prefix"]
            + embedding_text(chunk)
        )
        for chunk in chunks
    ]

    started = time.perf_counter()

    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=True,
    )

    elapsed_ms = (
        time.perf_counter()
        - started
    ) * 1000

    embeddings = np.asarray(
        embeddings,
        dtype=np.float32,
    )

    model_directory = (
        EXPERIMENT_ROOT
        / model_name
    )

    model_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    np.save(
        model_directory / "vectors.npy",
        embeddings,
    )

    with (
        model_directory
        / "chunks.json"
    ).open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            chunks,
            file,
            indent=2,
            ensure_ascii=False,
        )

    metadata = {
        "model_name": model_config[
            "model_name"
        ],
        "embedding_dimension": int(
            embeddings.shape[1]
        ),
        "chunk_count": len(chunks),
        "index_build_time_ms": round(
            elapsed_ms,
            2,
        ),
    }

    with (
        model_directory
        / "model_metadata.json"
    ).open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            metadata,
            file,
            indent=2,
        )

    return (
        model,
        embeddings,
        elapsed_ms,
    )


def search(
    model: SentenceTransformer,
    embeddings: np.ndarray,
    model_config: dict,
    query: str,
    chunks: list[dict],
) -> tuple[list[str], float]:

    model_query = (
        model_config["query_prefix"]
        + query
    )

    started = time.perf_counter()

    query_vector = model.encode(
        model_query,
        normalize_embeddings=True,
    )

    query_vector = np.asarray(
        query_vector,
        dtype=np.float32,
    )

    scores = embeddings @ query_vector

    top_indices = np.argsort(
        scores
    )[::-1][:TOP_K]

    latency_ms = (
        time.perf_counter()
        - started
    ) * 1000

    retrieved_ids = [
        chunks[index]["source_id"]
        for index in top_indices
    ]

    return (
        retrieved_ids,
        latency_ms,
    )


def main() -> None:

    print(
        "EMBEDDING MODEL COMPARISON"
    )
    print(
        "Production vector index will NOT "
        "be modified."
    )

    chunks = load_corpus()

    benchmark = load_benchmark()

    expected_count = benchmark.get(
        "corpus",
        {},
    ).get(
        "expected_chunk_count"
    )

    if (
        expected_count is not None
        and len(chunks) != expected_count
    ):
        raise ValueError(
            "Corpus size changed. "
            f"Expected {expected_count}, "
            f"found {len(chunks)}."
        )

    validate_benchmark(
        benchmark,
        chunks,
    )

    all_results = []

    for model_name, model_config in MODELS.items():

        model, embeddings, build_time = (
            build_index(
                model_name,
                model_config,
                chunks,
            )
        )

        case_results = []

        for case in benchmark["cases"]:

            retrieved_ids, latency_ms = search(
                model=model,
                embeddings=embeddings,
                model_config=model_config,
                query=case["query"],
                chunks=chunks,
            )

            metrics = calculate_metrics(
                retrieved_ids=retrieved_ids,
                relevant_ids=set(
                    case[
                        "relevant_source_ids"
                    ]
                ),
            )

            case_results.append(
                {
                    "case_id": case[
                        "case_id"
                    ],
                    "query": case[
                        "query"
                    ],
                    "retrieved": retrieved_ids,
                    "ground_truth": case[
                        "relevant_source_ids"
                    ],
                    "query_latency_ms": round(
                        latency_ms,
                        2,
                    ),
                    "metrics": metrics,
                }
            )

        average_metrics = {
            metric: round(
                sum(
                    result["metrics"][metric]
                    for result in case_results
                )
                / len(case_results),
                4,
            )
            for metric in [
                "recall_at_5",
                "recall_at_10",
                "mrr",
                "ndcg_at_10",
            ]
        }

        average_latency = round(
            sum(
                result[
                    "query_latency_ms"
                ]
                for result in case_results
            )
            / len(case_results),
            2,
        )

        result = {
            "model": model_name,
            "model_name": model_config[
                "model_name"
            ],
            "embedding_dimension": int(
                embeddings.shape[1]
            ),
            "index_build_time_ms": round(
                build_time,
                2,
            ),
            "average_query_latency_ms": (
                average_latency
            ),
            "average_metrics": (
                average_metrics
            ),
            "cases": case_results,
        }

        all_results.append(result)

        print()
        print(
            f"MODEL: {model_name}"
        )
        print(
            f"Recall@5: "
            f"{average_metrics['recall_at_5']}"
        )
        print(
            f"Recall@10: "
            f"{average_metrics['recall_at_10']}"
        )
        print(
            f"MRR: "
            f"{average_metrics['mrr']}"
        )
        print(
            f"nDCG@10: "
            f"{average_metrics['ndcg_at_10']}"
        )
        print(
            f"Query latency: "
            f"{average_latency} ms"
        )

    output_file = (
        ROOT
        / "evaluation"
        / "embedding_model_comparison"
        / "benchmark_results.json"
    )

    with output_file.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            {
                "corpus_chunks": len(chunks),
                "models": all_results,
            },
            file,
            indent=2,
        )

    print()
    print(
        "BENCHMARK COMPLETE"
    )
    print(
        f"Results: {output_file}"
    )


if __name__ == "__main__":
    main()