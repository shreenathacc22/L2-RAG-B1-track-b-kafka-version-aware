# L2-RAG-B1 Track B: Version-Aware Retrieval (Kafka runbooks)

**Problem.** Companies keep old and new versions of the same runbook. They read almost
identically, so a RAG system that ranks by similarity alone keeps handing outdated
thresholds, ports and on-call teams to the LLM.

**Fix.** Tag every chunk with version metadata (`doc_title`, `version`, `effective_date`,
`superseded`) and add one condition to the vector-store query, `where={"superseded": False}`,
so outdated chunks are excluded *before* ranking.

**Result** (21 frozen test cases, same corpus, model, chunking and top-k; only the filter changes):

| Metric | Filter OFF | Filter ON |
|---|---|---|
| **Superseded chunks retrieved** | **48.8%** (41/84) | **0.0%** (0/84) |
| Superseded cases passed | 0/9 | 9/9 |
| Exact-string cases passed | 7/7 | 7/7 |
| Multi-hop cases passed | 0/3 | 3/3 |
| Median retrieval latency | 50.2 ms | 51.1 ms |

Author: Shreenath Shetty · Modern AI Pro, Level 2, Track B (RAG Design), project B1.
Built on `simple_rag/` from the class labs.

## Branches

| Branch | What's on it | Start with |
|---|---|---|
| [`main`](../../tree/main) | This overview | — |
| [`track-b-kafka-version-aware`](../../tree/track-b-kafka-version-aware) | The full project: one commit per step (corpus → manifest → frozen golden set → BEFORE → metadata → filter → AFTER → report), results, docs and rebuild tools | `simple_rag/results/B1_REPORT.md`, `b1-track-b/` |
| [`rag-deployment`](../../tree/rag-deployment) | The runnable version-aware RAG: code, corpus, tests, `run.sh` | its `README.md` |

## Run it

```bash
git clone -b rag-deployment https://github.com/shreenathacc22/L2-RAG-B1-track-b-kafka-version-aware.git b1-rag
cd b1-rag && ./run.sh setup && ./run.sh demo
```

## Documents (on the project branch, `b1-track-b/docs/`)

- **SOP and runbook (PDF):** every step, how to test it (including inside Chroma), and every command
- **Claude Code CLI run guide (PDF):** build the project by prompting Claude Code, step by step
- **Flow deck (PPTX):** the problem, the flow, the results and the commands
- **Test scenarios (PDF):** 30 copy-paste test cases with expected messages; run all of them with `python3 b1-track-b/tools/tests/run_tests.py`

## Related

Track A of the same project (version metadata in front-matter):
https://github.com/shreenathacc22/L2-RAG-B1-version-aware-retrieval
