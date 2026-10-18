# B1 Version-Aware RAG: deployment package

A small retrieval-augmented generation (RAG) system over Kafka operations runbooks that
**never serves a superseded runbook**. Every chunk in the vector store carries version
metadata (`doc_title`, `version`, `effective_date`, `superseded`). The retriever adds one
condition, `where={"superseded": False}`, so outdated documents are excluded *before*
similarity ranking.

| Measured on 21 frozen test cases | Filter OFF | Filter ON |
|---|---|---|
| Superseded chunks retrieved | 48.8% | **0.0%** |
| Superseded cases passed | 0/9 | **9/9** |
| Exact-string cases passed | 7/7 | **7/7** |
| Multi-hop cases passed | 0/3 | **3/3** |
| Median retrieval latency | 50.2 ms | 51.1 ms |

Author: Shreenath Shetty · Modern AI Pro Level 2, Track B, project B1.
This branch holds only what the system needs to run. The full project history, step-by-step
docs (SOP PDF, run guide PDF, slide deck) and rebuild tools are on branch
[`track-b-kafka-version-aware`](../../tree/track-b-kafka-version-aware).

## Quick start

Needs Python 3.12 (installed automatically if you have [uv](https://docs.astral.sh/uv/)).

```bash
git clone -b rag-deployment https://github.com/shreenathacc22/L2-RAG-B1-track-b-kafka-version-aware.git b1-rag
cd b1-rag
./run.sh setup      # .venv + packages (first run downloads the ~90 MB embedder)
./run.sh demo       # ingest -> checks -> OFF vs ON evaluation, no API key needed
```

Expected end of `demo`:
```
| **Superseded chunks retrieved** | **48.8%** (41/84) | **0.0%** (0/84) | 0% |
| Exact-string cases passed | 7/7 (100%) | 7/7 (100%) | stay flat |
```

## Ask questions (needs an LLM key)

`ask` sends the retrieved runbooks to an OpenAI-compatible chat endpoint. Create a file
named `.env` in this folder. It's gitignored and never committed:

```
OPENAI_API_KEY=<your key>
OPENAI_BASE_URL=<your OpenAI-compatible endpoint URL>
```

```bash
./run.sh ask "Broker 4's data volume just hit 87%. Should that have paged someone?"
./run.sh ask-off "Broker 4's data volume just hit 87%. Should that have paged someone?"   # compare
```

## Commands

| Command | What it does |
|---|---|
| `./run.sh setup` | Create `.venv` (Python 3.12) and install `requirements.txt`; adds Intel-Mac pins automatically |
| `./run.sh ingest` | Chunk and embed the 16 runbooks; store vectors and version metadata in `simple_rag/.chroma/` |
| `./run.sh check` | Data checks plus metadata checks inside Chroma: ends with `PASS` |
| `./run.sh eval` | Run the 21 golden cases with the filter OFF and ON; writes `local_results/` |
| `./run.sh inspect ["question"]` | List stored chunks with their version, and run one question with the filter OFF vs ON |
| `./run.sh ask "…"` / `ask-off "…"` | Answer a question, filter ON / OFF |
| `./run.sh demo` | `ingest` + `check` + `eval` |

## How it works

```
INGEST  corpus/kafka/*.md + manifest.json -> load -> attach metadata -> chunk -> embed (MiniLM) -> Chroma
QUERY   question -> embed -> [ where={"superseded": False} ] -> top-4 by similarity -> LLM answer with citations
```

| Path | Role |
|---|---|
| `simple_rag/rag.py` | Pipeline. `retrieve(query, k=4, version_aware=False)` holds the filter |
| `simple_rag/corpus/kafka/` | 8 runbook subjects × current and old version, plus `manifest.json` (the version metadata) |
| `simple_rag/golden_kafka.jsonl` | 21 frozen test cases |
| `simple_rag/b1_eval.py` | Retrieval-only evaluator (no LLM): superseded rate, per-type pass rates, latency |
| `simple_rag/b1_check.py` | Data and Chroma metadata checks |
| `simple_rag/b1_inspect_chroma.py` | Read-only look inside the vector store |
| `simple_rag/results/` | The committed BEFORE / AFTER results and the B1 report |
| `labs/_kit.py` | LLM client used by `ask` |

## Updating the knowledge base

To publish a new version of a runbook:
1. Add the file.
2. In `manifest.json`, give it the same `doc` with a higher `version` and `superseded: false`.
3. Set the previous file to `superseded: true`.
4. Run `./run.sh ingest && ./run.sh check`.

The old file stays in the store but can no longer be retrieved.
