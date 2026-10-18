# B1 Track B: ablation summary

Corpus `simple_rag/corpus/kafka` · collection `kafka` · k=4 · embedder `sentence-transformers/all-MiniLM-L6-v2` · golden sha1 `850c67f2eab2`

Only one thing changes between the runs: `where={"superseded": False}` on the Chroma query.

| Metric | Filter OFF | Filter ON | Target |
|---|---|---|---|
| **Superseded chunks retrieved** | **48.8%** (41/84) | **0.0%** (0/84) | 0% |
| Superseded cases passed | 0/9 (0%) | 9/9 (100%) | improve |
| Exact-string cases passed | 7/7 (100%) | 7/7 (100%) | stay flat |
| Multi-hop cases passed | 0/3 (0%) | 3/3 (100%) | improve |
| Median retrieval latency (fair, 105 calls each, interleaved) | 50.2 ms | 51.1 ms | small change |

Runs: OFF at commit `db846c1`, ON at commit `c2ce3a2`; same golden sha1 in both: **True**.

## Case by case

| Case | Type | OFF | ON | Superseded files retrieved OFF -> ON |
|---|---|---|---|---|
| kafka-001 | superseded | FAIL | PASS | 2 -> 0 |
| kafka-002 | superseded | FAIL | PASS | 1 -> 0 |
| kafka-003 | superseded | FAIL | PASS | 2 -> 0 |
| kafka-004 | superseded | FAIL | PASS | 2 -> 0 |
| kafka-005 | superseded | FAIL | PASS | 2 -> 0 |
| kafka-006 | superseded | FAIL | PASS | 2 -> 0 |
| kafka-007 | superseded | FAIL | PASS | 2 -> 0 |
| kafka-008 | superseded | FAIL | PASS | 2 -> 0 |
| kafka-009 | superseded | FAIL | PASS | 2 -> 0 |
| kafka-010 | exact_string | PASS | PASS | 2 -> 0 |
| kafka-011 | exact_string | PASS | PASS | 2 -> 0 |
| kafka-012 | exact_string | PASS | PASS | 1 -> 0 |
| kafka-013 | exact_string | PASS | PASS | 2 -> 0 |
| kafka-014 | exact_string | PASS | PASS | 2 -> 0 |
| kafka-015 | exact_string | PASS | PASS | 3 -> 0 |
| kafka-016 | exact_string | PASS | PASS | 2 -> 0 |
| kafka-017 | multi_hop | FAIL | PASS | 2 -> 0 |
| kafka-018 | multi_hop | FAIL | PASS | 2 -> 0 |
| kafka-019 | multi_hop | FAIL | PASS | 2 -> 0 |
| kafka-020 | unanswerable | - | - | 2 -> 0 |
| kafka-021 | unanswerable | - | - | 2 -> 0 |

Failing cases with the filter ON: **none**. Unanswerable cases (kafka-020, kafka-021) are not scored on retrieval; they need an answer-level judge.
