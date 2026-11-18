from __future__ import annotations

import json
import math
import re
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parents[2]
CORPUS_FILE = ROOT / "data" / "vector_index" / "chunks.json"
EXPERIMENT_ROOT = ROOT / "data" / "embedding_experiments" / "single_query_comparison"
REPORT_FILE = ROOT / "evaluation" / "embedding_model_comparison" / "single_query_comparison.json"

QUERY = (
    "Find historical cases similar to a dimensional defect found during final "
    "inspection, including root-cause findings and corrective actions."
)
TOP_K = 10
EXPECTED_CORPUS_COUNT = 1188

MODELS: dict[str, dict[str, str]] = {
    "all-MiniLM-L6-v2": {
        "model_name": "sentence-transformers/all-MiniLM-L6-v2",
        "query_prefix": "",
        "passage_prefix": "",
    },
    "all-mpnet-base-v2": {
        "model_name": "sentence-transformers/all-mpnet-base-v2",
        "query_prefix": "",
        "passage_prefix": "",
    },
    "bge-small-en-v1.5": {
        "model_name": "BAAI/bge-small-en-v1.5",
        "query_prefix": "Represent this sentence for searching relevant passages: ",
        "passage_prefix": "",
    },
    "bge-base-en-v1.5": {
        "model_name": "BAAI/bge-base-en-v1.5",
        "query_prefix": "Represent this sentence for searching relevant passages: ",
        "passage_prefix": "",
    },
    "e5-base-v2": {
        "model_name": "intfloat/e5-base-v2",
        "query_prefix": "query: ",
        "passage_prefix": "passage: ",
    },
}


def load_corpus() -> list[dict[str, Any]]:
    if not CORPUS_FILE.exists():
        raise FileNotFoundError(f"Corpus file not found: {CORPUS_FILE}")
    with CORPUS_FILE.open("r", encoding="utf-8") as handle:
        corpus = json.load(handle)
    if not isinstance(corpus, list) or not corpus:
        raise ValueError("Corpus JSON must contain a non-empty list of chunks.")
    for position, chunk in enumerate(corpus):
        missing = [key for key in ("chunk_id", "source_id", "content") if not chunk.get(key)]
        if missing:
            raise ValueError(
                f"Chunk at position {position} is missing required field(s): {', '.join(missing)}"
            )
    return corpus


def embedding_text(chunk: dict[str, Any]) -> str:
    metadata = chunk.get("metadata") or {}
    values = (
        chunk.get("source_type", ""),
        chunk.get("title", ""),
        metadata.get("section", ""),
        chunk.get("content", ""),
    )
    return "\n".join(str(value) for value in values if value is not None and str(value).strip())


def trace_record(chunk: dict[str, Any], rank: int, score: float, score_type: str) -> dict[str, Any]:
    return {
        "rank": rank,
        "score": round(float(score), 8),
        "score_type": score_type,
        "chunk_id": chunk.get("chunk_id"),
        "source_id": chunk.get("source_id"),
        "source_type": chunk.get("source_type"),
        "document_id": chunk.get("document_id"),
        "title": chunk.get("title"),
        "content": chunk.get("content"),
        "metadata": chunk.get("metadata", {}),
        "provenance": chunk.get("provenance", {}),
    }


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def run_tfidf_baseline(corpus: list[dict[str, Any]]) -> dict[str, Any]:
    build_started = time.perf_counter()
    tokenized_docs = [tokenize(embedding_text(chunk)) for chunk in corpus]
    document_frequency: Counter[str] = Counter()
    for tokens in tokenized_docs:
        document_frequency.update(set(tokens))

    count_docs = len(corpus)
    idf = {
        token: math.log((count_docs + 1) / (frequency + 1)) + 1.0
        for token, frequency in document_frequency.items()
    }
    vectors: list[dict[str, float]] = []
    norms: list[float] = []
    for tokens in tokenized_docs:
        counts = Counter(tokens)
        vector = {
            token: (1.0 + math.log(count)) * idf[token]
            for token, count in counts.items()
            if token in idf
        }
        vectors.append(vector)
        norms.append(math.sqrt(sum(value * value for value in vector.values())))
    index_build_seconds = time.perf_counter() - build_started

    query_started = time.perf_counter()
    counts = Counter(tokenize(QUERY))
    query_vector = {
        token: (1.0 + math.log(count)) * idf[token]
        for token, count in counts.items()
        if token in idf
    }
    query_norm = math.sqrt(sum(value * value for value in query_vector.values()))
    scores: list[float] = []
    for vector, doc_norm in zip(vectors, norms):
        if query_norm == 0.0 or doc_norm == 0.0:
            scores.append(0.0)
            continue
        dot = sum(weight * vector.get(token, 0.0) for token, weight in query_vector.items())
        scores.append(dot / (query_norm * doc_norm))
    ranked = sorted(range(len(scores)), key=lambda index: (-scores[index], index))[:TOP_K]
    query_latency_seconds = time.perf_counter() - query_started

    return {
        "method": "keyword_tfidf_baseline",
        "status": "success",
        "score_type": "tfidf_cosine_similarity",
        "index_build_seconds": round(index_build_seconds, 6),
        "query_latency_seconds": round(query_latency_seconds, 6),
        "embedding_dimension": None,
        "top_results": [
            trace_record(corpus[index], rank, scores[index], "tfidf_cosine_similarity")
            for rank, index in enumerate(ranked, start=1)
        ],
    }


def save_candidate_index(model_key: str, vectors: np.ndarray, corpus: list[dict[str, Any]]) -> Path:
    # Candidate artifacts go under a separate directory, never data/vector_index.
    model_dir = EXPERIMENT_ROOT / model_key
    model_dir.mkdir(parents=True, exist_ok=True)
    np.save(model_dir / "vectors.npy", vectors)
    manifest = {
        "model_key": model_key,
        "corpus_file": str(CORPUS_FILE.relative_to(ROOT)),
        "chunk_count": len(corpus),
        "embedding_dimension": int(vectors.shape[1]),
        "items": [
            {
                "position": position,
                "chunk_id": chunk.get("chunk_id"),
                "source_id": chunk.get("source_id"),
                "source_type": chunk.get("source_type"),
                "document_id": chunk.get("document_id"),
                "title": chunk.get("title"),
                "content": chunk.get("content"),
                "metadata": chunk.get("metadata", {}),
                "provenance": chunk.get("provenance", {}),
            }
            for position, chunk in enumerate(corpus)
        ],
    }
    with (model_dir / "index_manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, ensure_ascii=False)
    return model_dir


def run_embedding_model(model_key: str, config: dict[str, str], corpus: list[dict[str, Any]]) -> dict[str, Any]:
    try:
        model_load_started = time.perf_counter()
        model = SentenceTransformer(config["model_name"])
        model_load_seconds = time.perf_counter() - model_load_started

        passages = [config["passage_prefix"] + embedding_text(chunk) for chunk in corpus]
        index_started = time.perf_counter()
        vectors = model.encode(
            passages,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=True,
            batch_size=32,
        )
        vectors = np.asarray(vectors, dtype=np.float32)
        index_build_seconds = time.perf_counter() - index_started
        candidate_path = save_candidate_index(model_key, vectors, corpus)

        query_started = time.perf_counter()
        query_vector = model.encode(
            config["query_prefix"] + QUERY,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        scores = np.asarray(vectors @ np.asarray(query_vector, dtype=np.float32))
        ranked = np.argsort(-scores, kind="stable")[:TOP_K]
        query_latency_seconds = time.perf_counter() - query_started

        return {
            "method": model_key,
            "status": "success",
            "model_name": config["model_name"],
            "score_type": "cosine_similarity",
            "model_load_seconds": round(model_load_seconds, 6),
            "index_build_seconds": round(index_build_seconds, 6),
            "query_latency_seconds": round(query_latency_seconds, 6),
            "embedding_dimension": int(vectors.shape[1]),
            "candidate_index_path": str(candidate_path.relative_to(ROOT)),
            "top_results": [
                trace_record(corpus[int(index)], rank, float(scores[int(index)]), "cosine_similarity")
                for rank, index in enumerate(ranked, start=1)
            ],
        }
    except Exception as exc:
        return {
            "method": model_key,
            "status": "failed",
            "model_name": config["model_name"],
            "error_type": type(exc).__name__,
            "error": str(exc),
            "top_results": [],
        }


def main() -> None:
    overall_started = time.perf_counter()
    corpus = load_corpus()
    if len(corpus) != EXPECTED_CORPUS_COUNT:
        print(f"WARNING: expected {EXPECTED_CORPUS_COUNT} chunks, loaded {len(corpus)}; using current corpus.")

    print(f"Loaded {len(corpus)} chunks.\nQuery: {QUERY}")
    results = [run_tfidf_baseline(corpus)]
    print("Completed keyword TF-IDF baseline.")

    for model_key, config in MODELS.items():
        print(f"\nRunning {model_key}...")
        result = run_embedding_model(model_key, config, corpus)
        results.append(result)
        if result["status"] == "failed":
            print(f"FAILED: {model_key}: {result.get('error', 'unknown error')}")
        else:
            print(f"Completed {model_key}.")

    report = {
        "experiment": "single_query_retrieval_comparison",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "query": QUERY,
        "top_k": TOP_K,
        "corpus": {"path": str(CORPUS_FILE.relative_to(ROOT)), "chunk_count": len(corpus)},
        "methods": results,
        "evaluation_notes": {
            "accuracy_metrics_calculated": False,
            "reason": "No validated relevant-source labels are available; Recall@K, MRR, and nDCG are intentionally omitted.",
            "baseline": "Keyword baseline uses local TF-IDF cosine similarity; it is not BM25 and uses no embedding model.",
            "score_warning": "Scores are method-specific and are not calibrated to a common scale. Compare returned evidence, not raw scores across methods.",
            "production_index_modified": False,
            "candidate_indexes_path": str(EXPERIMENT_ROOT.relative_to(ROOT)),
            "evidence_review_required": "Inspect result text and provenance to assess whether a result contains useful root-cause findings or corrective actions; rank alone does not establish relevance.",
        },
        "total_runtime_seconds": round(time.perf_counter() - overall_started, 6),
    }
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with REPORT_FILE.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)

    print("\n=== COMPACT RESULTS ===")
    for result in results:
        if result.get("status") != "success":
            print(f"{result['method']}: FAILED")
            continue
        top_sources = [item.get("source_id", "?") for item in result["top_results"][:3]]
        print(
            f"{result['method']}: query={result.get('query_latency_seconds', 0):.3f}s, "
            f"index_build={result.get('index_build_seconds', 0):.3f}s, top3_sources={top_sources}"
        )
    print(f"\nJSON report: {REPORT_FILE}")
    print(f"Candidate indexes: {EXPERIMENT_ROOT}")
    print("Production index modified: NO")


if __name__ == "__main__":
    main()
