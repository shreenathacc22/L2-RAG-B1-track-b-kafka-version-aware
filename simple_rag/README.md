# simple_rag — a small RAG system you can watch running

A companion to `labs/lab_3.py`, over a different corpus and with a different point.
Lab 3 teaches **retrieval quality** (hybrid search, golden sets, ablations). This
teaches **pipeline observability**: every stage prints what it measured and appends
a JSON record, so when an answer comes back wrong you can tell *which stage lost the
fact* instead of guessing.

Stack, deliberately boring: **Chroma** on disk · **all-MiniLM-L6-v2** running locally
(384 dims, 22M params, Apache-2.0, no API key) · the class LLM proxy for the answer only.

## Run it

```bash
python simple_rag/fetch_corpus.py                 # once — 50 .md + 50 .pdf, ~2 MB
python simple_rag/rag.py ingest                   # load → chunk → embed → store
python simple_rag/rag.py ask "How do I change a tyre on an Aventro?"
python simple_rag/rag.py ask                      # interactive
python simple_rag/rag.py inspect                  # read the stage traces back
```

`ingest` is idempotent — it rebuilds the collection from scratch each time (`--append`
to keep it). Only the final answer costs an API call; everything before it is local.

## The corpus

[Aventro Motors](https://github.com/udayallu/RAG-Multi-Corpus/tree/main/datasets/Aventro%20Motors)
— 50 owner-facing documents for a fictional car brand: model pages, how-tos,
service centres, warranty, FAQs. Published as **both** `.md` and `.pdf`, same 50 titles.

Both formats are parsed, because the comparison is a lesson. Only one is indexed:
the same title in two formats means duplicated chunks competing for the same top-k
slot, and the lossier copy can outrank the clean one. `load` keeps whichever format
extracted more text — on this corpus that is markdown, all 50 times, by an average of
**17%**. Use `--no-dedupe` to index both and watch retrieval get worse.

## The five stages, and what each one measures

| Stage | What it does | The number that catches a real bug |
|---|---|---|
| **load** | `.md` read, `.pdf` via pypdf | **extraction yield** (chars per KB on disk). A scanned or image-only PDF yields near zero and raises nothing — it just becomes invisible to search. Files under 200 chars get flagged. |
| **chunk** | paragraph packing, ~180 words, 1-paragraph overlap, doc title + heading prepended | the **distribution**, not the average — a histogram plus min/median/p90/max. 200 healthy chunks and 3 empty ones average out fine; the *minimum* is what tells you something broke. |
| **embed** | MiniLM, batches of 64, normalized | **mean pairwise cosine** on a sample. A collapsed embedder returns near-identical vectors for everything, so every query retrieves the same three chunks forever — and nothing errors. Healthy here: ~0.34. Near 1.0 is the alarm. |
| **store** | Chroma `PersistentClient`, cosine space | vector count and bytes on disk. Embeddings are computed *outside* Chroma and passed in, so the timing stays ours to measure. |
| **retrieve → generate** | top-k, then a grounded answer with `[n]` citations | **similarity of the top hit** and **which sources got cited**. These two split the only two suspects apart: the right chunk never arrived (retrieval), or it arrived and was ignored (generation). |

Two habits are baked into the timing code, both worth stealing: the embedding model
is **warmed before the clock starts** (folding a one-time 20s load into throughput
libels the embedder — it reads 7 chunks/s instead of the true 46), and citation
markers are parsed **structurally** (`\[(\d+)\]`), never by scanning for digits.

## The trace file

`rag_traces.jsonl` in the repo root — append-only JSON Lines, one object per event,
git-ignored. Same shape and reasoning as `labs/_kit.py → trace()`: crash-safe,
`tail -f`-able, and readable with jq/pandas/DuckDB when `inspect` isn't enough.

```bash
python simple_rag/rag.py inspect              # last run
python simple_rag/rag.py inspect --all-runs   # compare runs — did that change help?
jq 'select(.kind=="load" and .chars < 1000)' rag_traces.jsonl   # thin extractions
jq 'select(.stage=="chunk")' rag_traces.jsonl                   # the chunk summary
```

Turn it off with `RAG_TRACE=0`; move it with `RAG_TRACE_FILE=/path/to.jsonl`.
The LLM answer call is *also* traced, separately, to `traces.jsonl` by the class kit
— tokens, latency, the exact messages sent. `python labs/traces.py` reads that one.

## The golden set

Six frozen cases in `golden.jsonl`, following `golden/SCHEMA.md` — two happy path,
two unanswerable, two misleading.

```bash
python simple_rag/rag.py eval                    # all six
python simple_rag/rag.py eval --case av-003 -v   # one case, with the answer printed
```

| id | bucket | type | what it catches |
|---|---|---|---|
| `av-001` | happy path | `exact_string` | 12-row price table where three rows differ only by trim label |
| `av-002` | happy path | `multi_hop` | feature list and price table are different chunks of one doc |
| `av-003` | unanswerable | `unanswerable` | Glory's `505 litres` sits in a near-identical doc; Storm has no boot figure. Misattribution, not invention — how RAG actually hallucinates |
| `av-004` | unanswerable | `unanswerable` | "ground clearance" appears **nowhere** in the corpus. Honesty when nothing is retrievable |
| `av-005` | misleading | `conflicting_sources` | pricing doc says all models come in Sterling Silver; the Storm page lists five colours without it. Neither is marked stale |
| `av-006` | misleading | `false_premise` | the ZX row literally contains "360º Camera", so the top chunk *appears* to confirm a false premise unless the trim column is read |

**Two scores, never averaged** — that rule from your schema earned its keep immediately:

- **retrieval** — `must_cite` / `must_not_cite`, plain set membership. Deterministic, free.
- **answer** — facts, behavior, forbidden. One LLM judge call. `must_not_contain` is
  checked by exact string match *before* the judge runs — structural, so no false positives.

`must_cite` is **chunk-level**, pinned by heading:

```json
"must_cite": [{"doc": "Aventro Storm SUV", "heading": "Highlighted Features by Variant"}]
```

Heading rather than chunk id, because a heading survives re-chunking and an id does not.
Doc-level assertions go decorative the moment chunking splits — a 10-chunk doc passes if
any one chunk shows up, so the suite reports "retrieval PASS, answer FAIL" while the chunk
holding the fact never arrived. That is a retrieval bug wearing a generation bug's label.

## Knobs worth turning

```bash
python simple_rag/rag.py ingest --min-words 0        # keep degenerate chunks, see the damage
python simple_rag/rag.py ingest --chunk-words 400    # watch the histogram shift right
python simple_rag/rag.py ingest --overlap 0          # boundary facts stop surviving
python simple_rag/rag.py ingest --formats pdf        # index the lossy copy instead
python simple_rag/rag.py ingest --no-dedupe          # both formats, duplicated chunks
python simple_rag/rag.py ask -k 8 "..."              # more context, more noise
```

Each of these changes the printed numbers immediately. Whether it changed the system
for the *better* is a different question, and this file cannot answer it — that needs
a golden set and a judge. Lab 3, stages 4 and 5.

## Files

```
fetch_corpus.py   downloads the corpus (stdlib only, idempotent)
observe.py        the tracer: stage() / event() / the print helpers  (~120 lines)
rag.py            the pipeline: load · chunk · embed · store · retrieve · answer
.chroma/          the persistent vector DB (git-ignored, rebuilt by ingest)
```
