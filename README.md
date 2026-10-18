# Version-Aware RAG: outdated documents never reach the answer

**Problem.** Companies keep old and new versions of the same operations runbook. They read almost
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

## Live demo

**Open it: https://version-aware-rag.vercel.app**

A static web demo (folder `web/`, deployed on Vercel from this branch) runs the same retrieval **in the browser**. Type a
question and see filter OFF vs ON side by side, with all 21 test cases. The embedding model
(all-MiniLM-L6-v2, fp32) runs in the browser via transformers.js and returns the same top-4 as the
Python system for all 21 test questions (42/42, OFF and ON). There's no server and no API key; LLM answers
are only in the Python version (`rag-deployment`).

Run it locally: `cd web && python3 -m http.server 8000`, then open http://localhost:8000.

## Run it

```bash
git clone -b rag-deployment https://github.com/shreenathacc22/version-aware-rag.git b1-rag
cd b1-rag && ./run.sh setup && ./run.sh demo
```

## Documents (on the project branch, `b1-track-b/docs/`)

- **SOP and runbook (PDF):** every step, how to test it (including inside Chroma), and every command
- **Claude Code CLI run guide (PDF):** build the project by prompting Claude Code, step by step
- **Flow deck (PPTX):** the problem, the flow, the results and the commands
- **Test scenarios (PDF):** 31 copy-paste test cases with expected messages; run all of them with `python3 b1-track-b/tools/tests/run_tests.py`

## Related

Track A of the same project (version metadata in front-matter):
https://github.com/shreenathacc22/L2-RAG-B1-version-aware-retrieval
