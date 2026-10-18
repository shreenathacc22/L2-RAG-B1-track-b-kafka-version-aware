# B1 Track B: documents and rebuild tools

Version-aware retrieval for a Kafka runbook corpus, built on `simple_rag/` of the
Modern AI Pro Level 2 labs. The project code and results live in `simple_rag/`; this
folder holds the documentation and the tools that rebuild every step.

**Live demo:** https://l2-rag-b1-track-b-kafka-version-awa.vercel.app (runs in the browser; source in `web/` and on branch `main`)

**Result:** superseded chunks retrieved **48.8% → 0.0%**, exact-string retrieval **7/7 → 7/7**,
multi-hop **0/3 → 3/3**, latency **+0.9 ms**. See `simple_rag/results/B1_REPORT.md`.

| Path | What it is |
|---|---|
| `docs/B1_TrackB_Kafka_Version-Aware-Retrieval_SOP_v8_2026-10-18.pdf` | SOP and runbook: every step, test and command (Appendix A) |
| `docs/B1_TrackB_Kafka_Claude-CLI_Run-Guide_v6_2026-10-18.pdf` | How to build it step by step with the Claude Code CLI |
| `docs/B1_TrackB_Kafka_Version-Aware-Retrieval_Flow_Deck_v8_2026-10-18.pptx` | Slide deck: the flow, the results, all commands |
| `docs/B1_TrackB_Kafka_Test-Scenarios_v2_2026-10-18.pdf` | **31 copy-paste test cases** with expected messages and pass rules |
| `SOP.md` | Markdown source of the SOP |
| `tools/recreate_track_b.sh` | Rebuilds Steps 0–12 from a fresh clone and checks fingerprints |
| `tools/make_corpus.py`, `tools/make_golden.py` | Regenerate the 16 runbooks + manifest and the 21 golden cases, byte for byte |
| `tools/source/` | The B1 source files as committed at each step |
| `tools/docs/` | Scripts that rebuild the PDFs and the deck |
| `tools/tests/` | The test plan source (`test_cases.py`), the PDF generator and `run_tests.py`, which runs all 31 cases |

**Run all 31 tests** (from the root of this branch):
```bash
python3 b1-track-b/tools/tests/run_tests.py --shell zsh      # add --skip-llm without an API key
```

**Rebuild everything** (from the root of this branch):
```bash
SKIP_STEP2=1 bash b1-track-b/tools/recreate_track_b.sh ../track-b-rebuild
```
`SKIP_STEP2=1` skips the class-lab run that needs an LLM key. Every B1 step runs offline.

Branches of this repo: `main` (overview), `track-b-kafka-version-aware` (this project),
`rag-deployment` (the runnable package).
