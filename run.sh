#!/usr/bin/env bash
# B1 version-aware RAG over Kafka runbooks — one entry point.
#
#   ./run.sh setup              create .venv (Python 3.12) and install packages
#   ./run.sh ingest             load 16 runbooks + version metadata into Chroma
#   ./run.sh check              data checks + verify metadata inside Chroma
#   ./run.sh eval               21 golden cases, filter OFF vs ON -> local_results/
#   ./run.sh ask "question"     answer with version-aware retrieval (needs .env)
#   ./run.sh ask-off "question" same, filter OFF, to compare
#   ./run.sh inspect ["q"]      look inside Chroma: chunks + filter OFF vs ON
#   ./run.sh demo               ingest + check + eval (no API key needed)
set -euo pipefail
cd "$(dirname "$0")"

export RAG_CORPUS=simple_rag/corpus/kafka RAG_COLLECTION=kafka
export RAG_TRACE="${RAG_TRACE:-0}" MAI_TRACE="${MAI_TRACE:-0}" MAI_CLASSIFY="${MAI_CLASSIFY:-0}"
PY=.venv/bin/python

need_venv() { [ -x "$PY" ] || { echo "No .venv yet — run: ./run.sh setup"; exit 1; }; }

case "${1:-help}" in
  setup)
    PINS=()
    if [ "$(uname -s)-$(uname -m)" = "Darwin-x86_64" ]; then
      PINS=("torch==2.2.2" "numpy<2" "transformers<5" "sentence-transformers<6")   # last wheels for Intel Macs
    fi
    if command -v uv >/dev/null; then
      uv venv -q --python 3.12 .venv
      uv pip install -q --python "$PY" -r requirements.txt "${PINS[@]}"
    else
      python3.12 -m venv .venv
      "$PY" -m pip install -q -r requirements.txt "${PINS[@]}"
    fi
    "$PY" -c "import torch, chromadb, sentence_transformers; print('setup OK · torch', torch.__version__)"
    ;;
  ingest)   need_venv; "$PY" simple_rag/rag.py ingest --formats md ;;
  check)    need_venv; "$PY" simple_rag/b1_check.py --no-trap --chroma ;;
  eval)     need_venv; "$PY" simple_rag/b1_eval.py --out local_results
            echo; cat local_results/ablation_summary.md | sed -n '1,14p' ;;
  ask)      need_venv; shift; [ -f .env ] || { echo "ask needs .env with OPENAI_API_KEY (see README)"; exit 1; }
            "$PY" simple_rag/rag.py ask --version-aware "$@" ;;
  ask-off)  need_venv; shift; [ -f .env ] || { echo "ask needs .env with OPENAI_API_KEY (see README)"; exit 1; }
            "$PY" simple_rag/rag.py ask "$@" ;;
  inspect)  need_venv; shift; "$PY" simple_rag/b1_inspect_chroma.py "$@" ;;
  demo)     "$0" ingest && "$0" check && "$0" eval ;;
  *)        sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//' ;;
esac
