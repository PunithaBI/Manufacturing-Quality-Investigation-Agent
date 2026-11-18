# Hugging Face Embedding Model Comparison — Findings

## 1. Experiment scope

- Index used: `data/vector_index_candidate`
- Candidate corpus: 1,226 chunks
- Query count: 1
- Top K: 10
- Methods compared: 5
- Excluded method: `e5-base-v2` (failed to load)
- Evaluation status: Exploratory; labels are provisional

Query:
"Find historical cases similar to a dimensional defect found during final inspection, including root-cause findings and corrective actions."

No production index was used or modified as part of this comparison.

## 2. Exploratory metrics

| Method | Recall@10 | Precision@10 | MRR | nDCG@10 | Relevant hits |
|---|---:|---:|---:|---:|---:|
| keyword_tfidf_baseline | 0.059 | 0.200 | 1.000 | 0.393 | 2 |
| all-MiniLM-L6-v2 | 0.059 | 0.200 | 1.000 | 0.393 | 2 |
| all-mpnet-base-v2 | 0.294 | 1.000 | 1.000 | 0.627 | 10 |
| bge-small-en-v1.5 | 0.088 | 0.300 | 1.000 | 0.463 | 3 |
| bge-base-en-v1.5 | 0.147 | 0.500 | 1.000 | 0.466 | 5 |

The reported Recall@10 denominator is 34 provisionally judged relevant chunks. These labels are not validated corpus-wide ground truth.

## 3. Top-10 source coverage

Counts below classify retrieved chunks by source type, not by relevance.

| Method | 8D | NCR | RCA | CAPA | Other |
|---|---:|---:|---:|---:|---:|
| keyword_tfidf_baseline | 10 | 0 | 0 | 0 | 0 |
| all-MiniLM-L6-v2 | 6 | 0 | 0 | 0 | 4 |
| all-mpnet-base-v2 | 2 | 8 | 0 | 0 | 0 |
| bge-small-en-v1.5 | 10 | 0 | 0 | 0 | 0 |
| bge-base-en-v1.5 | 6 | 3 | 0 | 0 | 1 |

All methods retrieved the two dimensional-defect 8D cases at ranks 1 and 2. MPNet retrieved eight additional NCR chunks describing dimensional non-conformance. None of the five methods retrieved a direct RCA or CAPA chunk in the top 10.

## 4. Interpretation

- `all-mpnet-base-v2` is the provisional leader for this query based on the exploratory metrics and observed NCR coverage.
- This does not establish MPNet as the best model overall.
- MRR is 1.000 for every method because each method's first result was judged relevant; it does not distinguish the methods in this experiment.
- The top-10 results contain different source types. Source-type coverage alone does not prove technical relevance.
- The query requests root-cause findings and corrective actions, but no method retrieved direct RCA or CAPA chunks in its top 10.
- The database contains relationships linking 8D records to NCR, RCA and CAPA records. Relationship-based evidence retrieval should be evaluated as a separate experiment after the embedding comparison is documented.
- Data consistency also requires attention: the narrative for 8D-20260017 says "Pending RCA", while a linked RCA row contains a root-cause finding. Correct linkage does not prove that a root-cause conclusion is technically valid.

## 5. Limitations

1. Only one query was evaluated.
2. Relevance labels are provisional.
3. The 34 relevant chunks are curated judgments, not validated corpus-wide ground truth.
4. These results do not establish performance across other defect types, queries or retrieval tasks.
5. Similarity scores from different embedding models must not be compared directly as if they shared a common scale.
6. No conclusion about end-to-end hybrid retrieval performance can be drawn from this experiment alone.

## 6. Conclusion

For the single query tested, `all-mpnet-base-v2` is the provisional leader among the five successful methods. The result is promising but insufficient to declare a validated overall winner.

The next phase, after documenting this comparison, is to evaluate relationship-based retrieval of linked RCA and CAPA evidence separately. Preserve the current candidate index and do not change the production index during the model comparison.
