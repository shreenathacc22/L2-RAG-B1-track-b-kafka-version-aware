#!/usr/bin/env bash
# Recreate B1 Track B, Steps 0–12, from nothing — no Claude needed.
#
#   bash recreate_track_b.sh [WORK_DIR]
#
# Works from the project folder (b1-tracking/track-b/tools/) or from a clone of the
# GitHub branch (b1-track-b/tools/): it finds its tools next to itself.
# WORK_DIR defaults to $BASE/track-b-rebuild (never touches the original track-b-kafka/).
# Optional environment variables:
#   BASE=...      project base     (default ~/Desktop/AI-Architect_L2_Aug_2026/project_10082026)
#   ENV_FILE=...  .env with the class proxy key, used by Step 2 only (default $BASE/.env)
#   VENV=...      reuse an existing Python venv instead of creating WORK_DIR/.venv
#   SKIP_STEP2=1  skip the unchanged-lab run (it needs the class proxy key and ~2 minutes)
#
# Every step prints what it checks. The script stops at the first failure (set -e).
# At the end it compares fingerprints with the original build: all must say MATCH.

set -euo pipefail

BASE="${BASE:-$HOME/Desktop/AI-Architect_L2_Aug_2026/project_10082026}"
WORK="${1:-$BASE/track-b-rebuild}"
TOOLS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-$BASE/.env}"
LOGS="$WORK.logs"
REPO_URL="https://github.com/balajivis/mai-practitioner-labs.git"
UPSTREAM_COMMIT="6b918c2"          # class repo commit Track B was built on
GIT_ID=(-c user.name="${GIT_NAME:-Shreenath Shetty}" -c user.email="${GIT_EMAIL:-191985630+shreenathacc22@users.noreply.github.com}")

step() { printf '\n\033[1m== %s\033[0m\n' "$*"; }
ok()   { printf '   OK   %s\n' "$*"; }
die()  { printf '   FAIL %s\n' "$*"; exit 1; }

[ -e "$WORK" ] && die "$WORK already exists — remove it or pass another folder"
mkdir -p "$LOGS"

# ── Step 0: get the code ─────────────────────────────────────────────────────
step "Step 0 · clone the class repo at $UPSTREAM_COMMIT, branch track-b, copy .env"
git clone -q "$REPO_URL" "$WORK"
cd "$WORK"
git checkout -q "$UPSTREAM_COMMIT"
git switch -q -c track-b
if [ -f "$ENV_FILE" ]; then cp "$ENV_FILE" .env && chmod 600 .env && ok ".env copied (never committed: it is in .gitignore)"; else echo "   note: no .env at $ENV_FILE — Step 2 'ask' needs one (or use SKIP_STEP2=1)"; fi
ok "repo at $(git log -1 --format='%h %s')"

# ── Python environment ───────────────────────────────────────────────────────
step "Python 3.12 environment"
if [ -n "${VENV:-}" ]; then
  PY="$VENV/bin/python"; ok "reusing $VENV"
else
  uv venv -q --python 3.12 .venv
  uv pip install -q --python .venv/bin/python -r requirements.txt \
     "torch==2.2.2" "numpy<2" "transformers<5" "sentence-transformers<6"
  PY="$WORK/.venv/bin/python"; ok "created $WORK/.venv"
fi
"$PY" -c "import torch, chromadb, sentence_transformers, openai; print('   OK   imports: torch', torch.__version__)"

# ── Step 2: the unchanged lab runs ───────────────────────────────────────────
if [ "${SKIP_STEP2:-0}" = "1" ]; then
  step "Step 2 · skipped (SKIP_STEP2=1)"
else
  step "Step 2 · run the unchanged lab: ingest, ask, eval"
  "$PY" simple_rag/rag.py ingest                        > "$LOGS/step02_ingest.log" 2>&1 && ok "ingest"
  "$PY" simple_rag/rag.py ask "how do I tow my car?"    > "$LOGS/step02_ask.log"    2>&1 && ok "ask"
  "$PY" simple_rag/rag.py eval                          > "$LOGS/step02_eval.log"   2>&1 && ok "eval"
  grep -E "retrieval [0-9]+/6" "$LOGS/step02_eval.log" | sed 's/^/   /' || true
  rm -f rag_traces.jsonl traces.jsonl
fi

# ── Steps 3–4: corpus, manifest, data checks ────────────────────────────────
step "Steps 3–4 · generate 16 runbooks + manifest.json, add b1_check.py"
"$PY" "$TOOLS/make_corpus.py" simple_rag/corpus/kafka
cp "$TOOLS/source/b1_check.py" simple_rag/b1_check.py
"$PY" simple_rag/b1_check.py > "$LOGS/step03-04_b1_check.log" 2>&1 || { cat "$LOGS/step03-04_b1_check.log"; die "b1_check"; }
grep -E "OK|old version outranks" "$LOGS/step03-04_b1_check.log" | sed 's/^ */   /'
git add simple_rag/corpus/kafka simple_rag/b1_check.py
git "${GIT_ID[@]}" commit -q -m "B1 Track B steps 3-4: versioned Kafka corpus, manifest and data checks"
ok "committed $(git log -1 --format=%h)"

# ── Step 5: golden set ───────────────────────────────────────────────────────
step "Step 5 · generate the 21 golden cases and check them"
"$PY" "$TOOLS/make_golden.py" simple_rag/golden_kafka.jsonl
"$PY" simple_rag/b1_check.py --no-trap > "$LOGS/step05_b1_check.log" 2>&1 || { cat "$LOGS/step05_b1_check.log"; die "b1_check"; }
sed -n '/Step 5/,$p' "$LOGS/step05_b1_check.log" | sed 's/^ */   /'

step "Negative tests · break the data on purpose; the checks must FAIL"
M=simple_rag/corpus/kafka/manifest.json; G=simple_rag/golden_kafka.jsonl
cp "$M" "$LOGS/manifest.bak"; cp "$G" "$LOGS/golden.bak"
"$PY" - "$M" <<'PY'
import json, sys; p = sys.argv[1]; m = json.load(open(p))
m["files"]["disk-capacity-2025.md"]["superseded"] = False          # two current files
m["files"]["topic-retention.md"]["version"] = "3"                   # wrong type
m["files"]["schema-registry.md"]["effective_date"] = "2026-3-20"    # bad date
json.dump(m, open(p, "w"), indent=2)
PY
if "$PY" simple_rag/b1_check.py --no-trap > "$LOGS/negative_manifest.log" 2>&1; then die "manifest negative test passed — checks are broken"; fi
ok "manifest negative test: $(tail -1 "$LOGS/negative_manifest.log")"
cp "$LOGS/manifest.bak" "$M"
"$PY" - "$G" <<'PY'
import json, sys; p = sys.argv[1]; rows = [json.loads(l) for l in open(p)]
rows[0]["expect"]["must_cite"] = [{"doc": "Kafka Broker Disk Capacity Runbook", "version": 2}]  # cites OLD
rows[2]["expect"]["must_not_contain"].append("3 days")                                       # bans the right answer
open(p, "w").write("".join(json.dumps(r) + "\n" for r in rows))
PY
if "$PY" simple_rag/b1_check.py --no-trap > "$LOGS/negative_golden.log" 2>&1; then die "golden negative test passed — checks are broken"; fi
ok "golden negative test: $(tail -1 "$LOGS/negative_golden.log")"
cp "$LOGS/golden.bak" "$G"
"$PY" simple_rag/b1_check.py --no-trap | tail -1 | grep -q PASS && ok "restored: PASS again"

# ── Step 6: freeze ───────────────────────────────────────────────────────────
step "Step 6 · freeze the golden set in its own commit"
git add "$G"
git "${GIT_ID[@]}" commit -q -m "Freeze B1 golden set before version-aware retrieval"
ok "committed $(git log -1 --format=%h) — only $(git show --stat --format= HEAD | tail -1 | xargs)"
[ "$(git log --format=%h -- simple_rag/rag.py | head -1)" = "$(git log --format=%h "$UPSTREAM_COMMIT" -- simple_rag/rag.py | head -1)" ] \
  && ok "rag.py untouched since upstream — the freeze comes before any B1 code"

# ── Step 7: evaluator + BEFORE run ───────────────────────────────────────────
step "Step 7 · rag.py corpus settings + b1_eval.py, ingest Kafka, BEFORE run (filter OFF)"
cp "$TOOLS/source/rag.py" simple_rag/rag.py           # adds RAG_CORPUS/RAG_COLLECTION; retrieval unchanged
cp "$TOOLS/source/b1_eval.py" simple_rag/b1_eval.py
export RAG_CORPUS=simple_rag/corpus/kafka RAG_COLLECTION=kafka RAG_TRACE=0
"$PY" simple_rag/rag.py ingest --formats md > "$LOGS/step07_ingest.log" 2>&1 \
  && ok "ingest: $(grep -o 'vectors stored *[0-9]*' "$LOGS/step07_ingest.log" | tr -s ' ')"
"$PY" simple_rag/b1_eval.py --off > "$LOGS/step07_eval_off.log" 2>&1 || { cat "$LOGS/step07_eval_off.log"; die "b1_eval --off"; }
grep -E "superseded chunks retrieved|(superseded_cases|exact_string|multi_hop) +[0-9]+/|median retrieval" "$LOGS/step07_eval_off.log" | sed 's/^ */   /'
RATE=$("$PY" -c "import json;print(json.load(open('simple_rag/results/baseline_filter_off.json'))['summary']['superseded_rate_pct'])")
[ "$RATE" = "48.8" ] && ok "BEFORE superseded rate $RATE% — same as the original run" || die "BEFORE rate $RATE%, expected 48.8%"
git add simple_rag/rag.py simple_rag/b1_eval.py simple_rag/results/baseline_filter_off.json
git "${GIT_ID[@]}" commit -q -m "B1 Track B step 7: evaluator and BEFORE baseline (filter OFF)"
ok "committed $(git log -1 --format=%h)"
[ "$(shasum simple_rag/rag.py | cut -c1-40)" = 5874d262eeadc8bc2e40948c62f2e540f633b559 ] && ok "rag.py (step 7) fingerprint MATCH"
cp simple_rag/results/baseline_filter_off.json "$LOGS/step07_baseline_filter_off.json"

# ── Step 8: version metadata into Chroma ─────────────────────────────────────
step "Step 8 · attach manifest metadata to every chunk, verify inside Chroma"
for f in rag.py b1_check.py b1_inspect_chroma.py; do cp "$TOOLS/source/step08/$f" "simple_rag/$f"; done
if "$PY" simple_rag/b1_check.py --no-trap --chroma > "$LOGS/step08_chroma_before_reingest.log" 2>&1; then
  die "--chroma passed on the Step 7 collection — it should not (no metadata yet)"; fi
ok "negative test: --chroma on the old collection -> $(tail -1 "$LOGS/step08_chroma_before_reingest.log")"
"$PY" simple_rag/rag.py ingest --formats md > "$LOGS/step08_ingest.log" 2>&1 && ok "re-ingested with metadata"
"$PY" simple_rag/b1_check.py --no-trap --chroma > "$LOGS/step08_b1_check_chroma.log" 2>&1 || { cat "$LOGS/step08_b1_check_chroma.log"; die "--chroma"; }
grep -E "chunks, every one|match manifest|runbooks are in|where=|splits the store" "$LOGS/step08_b1_check_chroma.log" | sed 's/^ */   /'
"$PY" simple_rag/b1_eval.py --off --out "$LOGS/step08_eval" > "$LOGS/step08_eval_off.log" 2>&1
"$PY" - "$LOGS/step07_baseline_filter_off.json" "$LOGS/step08_eval/baseline_filter_off.json" <<'PY' || die "OFF run changed after Step 8"
import json, sys
a, b = (json.load(open(p)) for p in sys.argv[1:])
key = lambda r: [(c["id"], c["pass"], [(h["file"], h["superseded"]) for h in c["retrieved"]]) for c in r["cases"]]
sys.exit(0 if key(a) == key(b) else 1)
PY
ok "filter OFF after Step 8 is identical to the Step 7 baseline (metadata alone changes nothing)"
"$PY" simple_rag/b1_inspect_chroma.py > "$LOGS/step08_inspect_chroma.log" 2>&1 && ok "b1_inspect_chroma.py ran (see $LOGS/step08_inspect_chroma.log)"
git add simple_rag/rag.py simple_rag/b1_check.py simple_rag/b1_inspect_chroma.py
git "${GIT_ID[@]}" commit -q -m "B1 Track B step 8: version metadata attached to every chunk in Chroma"
ok "committed $(git log -1 --format=%h)"
[ "$(shasum simple_rag/rag.py | cut -c1-40)" = a5587411c41c682c51e1c057f0a99de438dbe736 ] && ok "rag.py (step 8) fingerprint MATCH"

# ── Steps 9–10: the filter behind an OFF/ON switch ───────────────────────────
step "Steps 9–10 · where={superseded: False} in rag.retrieve(), switchable OFF/ON"
cp "$TOOLS/source/step10/rag.py" simple_rag/rag.py
"$PY" simple_rag/b1_eval.py --off --out "$LOGS/step10_eval" > "$LOGS/step10_eval_off.log" 2>&1
"$PY" - "$LOGS/step07_baseline_filter_off.json" "$LOGS/step10_eval/baseline_filter_off.json" <<'PY' || die "OFF changed after adding the filter"
import json, sys
a, b = (json.load(open(p)) for p in sys.argv[1:])
key = lambda r: [(c["id"], c["pass"], [(h["file"], h["superseded"]) for h in c["retrieved"]]) for c in r["cases"]]
sys.exit(0 if key(a) == key(b) else 1)
PY
ok "filter OFF is still identical to the Step 7 baseline (48.8%)"
"$PY" simple_rag/b1_eval.py --on --out "$LOGS/step10_eval" > "$LOGS/step10_eval_on_preview.log" 2>&1 || { cat "$LOGS/step10_eval_on_preview.log"; die "b1_eval --on"; }
grep -E "superseded chunks retrieved|(superseded_cases|exact_string|multi_hop) +[0-9]+/" "$LOGS/step10_eval_on_preview.log" | sed 's/^ */   /'
ON=$("$PY" -c "import json,sys;s=json.load(open(sys.argv[1]))['summary'];print(s['superseded_rate_pct'],s['exact_string']['passed'])" "$LOGS/step10_eval/version_filter_on.json")
[ "$ON" = "0.0 7" ] && ok "filter ON preview: 0.0% superseded, exact_string 7/7" || die "ON preview gave: $ON"
git add simple_rag/rag.py
git "${GIT_ID[@]}" commit -q -m "B1 Track B steps 9-10: query-time version filter behind an OFF/ON switch"
ok "committed $(git log -1 --format=%h)"

# ── Step 11: AFTER run ───────────────────────────────────────────────────────
step "Step 11 · AFTER run (filter ON) on the same frozen golden set"
"$PY" simple_rag/b1_eval.py --on > "$LOGS/step11_eval_on.log" 2>&1 || { cat "$LOGS/step11_eval_on.log"; die "b1_eval --on"; }
grep -E "superseded chunks retrieved|(superseded_cases|exact_string|multi_hop) +[0-9]+/" "$LOGS/step11_eval_on.log" | sed 's/^ */   /'
ON=$("$PY" -c "import json;s=json.load(open('simple_rag/results/version_filter_on.json'))['summary'];print(s['superseded_rate_pct'],s['superseded_cases']['passed'],s['exact_string']['passed'],s['multi_hop']['passed'])")
[ "$ON" = "0.0 9 7 3" ] && ok "AFTER: 0.0% superseded · 9/9 · 7/7 · 3/3 — same as the original" || die "AFTER gave: $ON"
git add simple_rag/results/version_filter_on.json
git "${GIT_ID[@]}" commit -q -m "B1 Track B step 11: AFTER run (filter ON) on the same frozen golden set"
ok "committed $(git log -1 --format=%h)"

# ── Step 12: ablation table, fair latency, report ────────────────────────────
step "Step 12 · fair latency, ablation table, report"
cp "$TOOLS/source/step12/b1_eval.py" simple_rag/b1_eval.py
"$PY" simple_rag/b1_eval.py --latency "${LATENCY_ROUNDS:-2}" > "$LOGS/step12_latency.log" 2>&1 \
  && ok "latency: $("$PY" -c "import json;d=json.load(open('simple_rag/results/latency.json'));print(f\"OFF {d['off']['median_ms']} ms, ON {d['on']['median_ms']} ms, delta {d['median_delta_ms']} ms\")")"
"$PY" simple_rag/b1_eval.py --table > "$LOGS/step12_table.log" 2>&1 && ok "results/ablation_summary.md written"
grep -E "^\| \*\*Superseded chunks|^\| Exact-string" simple_rag/results/ablation_summary.md | sed 's/^/   /'
cp "$TOOLS/source/step12/B1_REPORT.md" simple_rag/results/B1_REPORT.md
git add simple_rag/b1_eval.py simple_rag/results/
git "${GIT_ID[@]}" commit -q -m "B1 Track B step 12: ablation table, fair latency and report"
ok "committed $(git log -1 --format=%h)"

# ── Verify against the original build ────────────────────────────────────────
step "Verify · fingerprints must match the original Track B build"
check() { [ "$2" = "$3" ] && ok "$1 MATCH ($2)" || die "$1 DIFFERENT: got $2, expected $3"; }
check "corpus (16 .md)   " "$(cat simple_rag/corpus/kafka/*.md | shasum | cut -c1-40)" 1b9bb81564f052d37a2fdba1fe4f4d986b3a64bc
check "manifest.json     " "$(shasum "$M" | cut -c1-40)"                              dea81e27843ffee677863915fa998b1dfaf5ab9c
check "golden_kafka.jsonl" "$(shasum "$G" | cut -c1-40)"                              850c67f2eab21aa1a6afabd481e5c3efccb7e0ba
check "b1_check.py (st 8)" "$(shasum simple_rag/b1_check.py | cut -c1-40)"            4811e119fbbea14f97d5db84e327b653025069ae
check "rag.py (step 10)  " "$(shasum simple_rag/rag.py | cut -c1-40)"                 59dbe54f952b5dfef50c1e613479d5325729e955
check "b1_eval.py (st 12)" "$(shasum simple_rag/b1_eval.py | cut -c1-40)"             a815f0d85440ff8c8a367296808ac4d2e0240327
check "b1_inspect_chroma " "$(shasum simple_rag/b1_inspect_chroma.py | cut -c1-40)"    a2be529f0b16101dc714003b4b2d8bfd57b2ed1d

step "Done · Steps 0–12 recreated in $WORK  (logs: $LOGS)"
git log --oneline -9
