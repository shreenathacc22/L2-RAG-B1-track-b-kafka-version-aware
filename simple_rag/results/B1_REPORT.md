# B1: Version-Aware Retrieval (Track B, Kafka runbooks)

**Modern AI Pro · Level 2 · Track B · RAG Design**
Author: Shreenath Shetty (individual project) · Branch `track-b` of `mai-practitioner-labs` (base `6b918c2`)

**Objective:** stop superseded documents from winning retrieval on semantic similarity alone,
by adding version metadata and filtering at query time.

**Success condition:** superseded retrieved chunks drop to 0% while `exact_string` stays flat,
on the same frozen golden set before and after.

## Result

| Metric | Filter OFF (before) | Filter ON (after) | Target |
|---|---|---|---|
| **Superseded chunks retrieved** | **48.8%** (41/84) | **0.0%** (0/84) | 0% ✅ |
| Superseded cases passed | 0/9 | 9/9 | improve ✅ |
| Exact-string cases passed | 7/7 | 7/7 | stay flat ✅ |
| Multi-hop cases passed | 0/3 | 3/3 | improve ✅ |
| Median retrieval latency (105 interleaved calls each) | 50.2 ms | 51.1 ms | small change ✅ (+0.9 ms) |

**Conclusion.** With similarity alone, almost half of what the retriever handed the LLM
(48.8%) came from superseded runbooks, and every version-sensitive question retrieved the old
twin. Adding version metadata to each chunk and one query-time condition,
`where={"superseded": False}`, cut that to 0% and fixed all 9 superseded and 3 multi-hop
cases. Exact-string retrieval stayed at 7/7 and latency moved by under 1 ms, so the stage
removes stale documents without hurting normal retrieval.

## What was built

| Piece | Where | Step |
|---|---|---|
| 8 Kafka runbook subjects × current and old version (fictional company "Halcyon") | `simple_rag/corpus/kafka/*.md` | 3 |
| Version metadata (`doc`, `version`, `effective_date`, `superseded`), kept outside the text | `simple_rag/corpus/kafka/manifest.json` | 4 |
| 21 golden cases: 9 superseded, 7 exact_string, 3 multi_hop, 2 unanswerable | `simple_rag/golden_kafka.jsonl` | 5 |
| Golden set frozen in its own commit before any `rag.py` change | `2cff45a` | 6 |
| Evaluator (retrieval only, deterministic) and BEFORE run | `simple_rag/b1_eval.py`, `results/baseline_filter_off.json` | 7 |
| Manifest fields attached to every chunk in Chroma | `rag.py` `b1_metadata()` | 8 |
| `retrieve(version_aware=...)`: ON adds the where-clause, OFF is the original query | `rag.py` | 9–10 |
| AFTER run on the same frozen cases | `results/version_filter_on.json` | 11 |
| Ablation table, fair latency, this report | `results/ablation_summary.md`, `results/latency.json` | 12 |

Data checks: `b1_check.py` (corpus, manifest, golden set and, with `--chroma`, the stored
metadata), each proven with a negative test. `b1_inspect_chroma.py` shows the filter's effect
directly in the database.

## Evidence that it is a real ablation

- **One variable.** Embedder (`all-MiniLM-L6-v2`), chunking (180 words), k = 4, prompt, corpus
  and golden set are identical in both runs. Only the `where` clause differs.
- **Frozen first.** The golden set (sha1 `850c67f2…`) was committed in `2cff45a`, before the
  first B1 change to `rag.py` (`8c97952`). Both result files record the same sha1.
- **OFF is the original.** After metadata (Step 8) and after the filter code (Steps 9–10),
  the OFF run was re-checked and was identical to the Step 7 baseline: all 21 cases, same files,
  same ranks.
- **Nothing deleted.** All 8 superseded runbooks stay in the collection for the AFTER run. The
  filter excludes them; it doesn't remove them.
- **Reproducible.** `b1-tracking/track-b/tools/recreate_track_b.sh` rebuilds Steps 0–12 from a
  fresh clone and checks file fingerprints and both results.

## Failures, limits and honest notes

1. **No failing scored cases with the filter ON.** The 2 unanswerable cases (`kafka-020`,
   `kafka-021`) aren't scored on retrieval. They need an answer-level judge, which this
   project doesn't run.
2. **Answer level was spot-checked only.** For "Broker 4 hit 87%", the LLM answered correctly
   (85%) in *both* modes, because the current runbook ranked #1. With the filter OFF, the 90%
   rule was still #2 in its context. B1 is measured on retrieval because a correct answer on
   stale context is luck.
3. **Small, synthetic corpus.** There are 16 short runbooks (17 chunks), written to be
   near-duplicates (pair similarity 0.867–0.969). Real corpora have more noise, longer
   documents and partial overlaps between versions.
4. **`superseded` is maintained by hand** in `manifest.json`. If someone forgets to flip it,
   the filter trusts the wrong file. A real system would derive it from `doc` + `version`, or
   from a document-management system.
5. **Latency.** Single-run medians (143.8 ms OFF, 154.6 ms ON) were dominated by machine
   warm-up. The fair interleaved measurement (105 calls each) gives 50.2 vs 51.1 ms. The ON p90
   (55.6 ms) is lower than OFF's (153.4 ms), which is noise from the OFF call running first in
   each pair, not a speed-up. Cost: no LLM calls are needed for the evaluation, so $0.
6. **"As of date" questions** (what was the rule in 2025?) are deliberately out of scope. The
   filter always serves the current version. `effective_date` is stored so this can be added
   later.

## Code on GitHub

Public repo: https://github.com/shreenathacc22/L2-RAG-B1-track-b-kafka-version-aware

| Branch | Contents |
|---|---|
| `main` | Overview and links |
| `track-b-kafka-version-aware` | This project: one commit per step, results, docs and rebuild tools (`b1-track-b/`) |
| `rag-deployment` | The runnable version-aware RAG (`run.sh`, README) |

Track A (front-matter version): https://github.com/shreenathacc22/L2-RAG-B1-version-aware-retrieval

## Reproduce

```bash
B=~/Desktop/AI-Architect_L2_Aug_2026/project_10082026
VENV=$B/mai-practitioner-labs/.venv bash $B/b1-tracking/track-b/tools/recreate_track_b.sh
```
Or by hand, from `track-b-kafka/`:
```bash
export RAG_CORPUS=simple_rag/corpus/kafka RAG_COLLECTION=kafka
python simple_rag/rag.py ingest --formats md
python simple_rag/b1_check.py --no-trap --chroma     # PASS
python simple_rag/b1_eval.py --off                   # 48.8%
python simple_rag/b1_eval.py --on                    # 0.0%
python simple_rag/b1_eval.py --latency 5             # fair timing
python simple_rag/b1_eval.py --table                 # results/ablation_summary.md
```

## Submission checklist (from the B1 guide)

| Requirement | Status |
|---|---|
| Latest repository pulled; PROJECTS.md reviewed | ✅ base `6b918c2` |
| Existing simple_rag runs before modification | ✅ ingest / ask / eval (retrieval 2/6, the lab's start) |
| Own versioned corpus | ✅ 16 Kafka runbooks, not Meridian or Aventro |
| At least 15 golden cases | ✅ 21 |
| Golden set committed before retrieval changes | ✅ `2cff45a` before `8c97952` |
| Baseline (filter OFF) captured | ✅ `results/baseline_filter_off.json` |
| version / effective_date / superseded in vector-store metadata | ✅ checked in Chroma (`b1_check.py --chroma`) |
| Query-time metadata filter | ✅ `where={"superseded": False}` |
| Filter switchable OFF / ON | ✅ `version_aware`, `--version-aware` |
| AFTER run on exactly the same cases | ✅ same golden sha1 |
| Superseded retrieval rate calculated | ✅ 48.8% → 0.0% |
| Superseded retrieval rate 0% | ✅ |
| Exact-string flat | ✅ 7/7 → 7/7 |
| Failures and latency/cost included | ✅ above |
| Before/after table and short conclusion | ✅ above |
