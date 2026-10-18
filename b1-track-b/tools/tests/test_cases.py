"""B1 Track B test plan: one source for the PDF and for the automated runner.

Each case: id, title, area, purpose, commands (copy-paste, zsh/bash), expect (regexes
that must appear in the output), expect_not (regexes that must NOT appear), message
(what the tester should see, in words), soft (LLM-dependent: warn instead of fail),
long (takes minutes), llm (needs .env and network).
"""

GH = "https://github.com/shreenathacc22/L2-RAG-B1-track-b-kafka-version-aware.git"
GO = """cd ~/b1-test/b1-rag
export RAG_CORPUS=simple_rag/corpus/kafka RAG_COLLECTION=kafka RAG_TRACE=0"""
REPO = "R=https://github.com/shreenathacc22/L2-RAG-B1-track-b-kafka-version-aware.git"
Q87 = "Broker 4's data volume just hit 87%. Should that have paged someone?"

CASES = [
# ── A. Setup ────────────────────────────────────────────────────────────────
dict(id="TC-01", area="A. Setup", title="Prerequisites are installed",
 purpose="git, uv and Python are available before anything else.",
 commands="""git --version
uv --version
python3 --version""",
 expect=[r"git version \d", r"uv \d"],
 message="Three version lines, e.g. `git version 2.x`, `uv 0.x`, `Python 3.x`.",
 pass_rule="All three commands print a version. If uv is missing, install it from docs.astral.sh/uv."),

dict(id="TC-02", area="A. Setup", title="Clone the deployment branch from GitHub",
 purpose="The public repo is reachable and the rag-deployment branch has the runnable package.",
 commands=f"""rm -rf ~/b1-test && mkdir -p ~/b1-test && cd ~/b1-test
{REPO}
git clone -b rag-deployment $R b1-rag
cd b1-rag && git log --oneline -1 && ls""",
 expect=[r"rag-deployment: runnable version-aware RAG package", r"run\.sh", r"simple_rag", r"requirements\.txt"],
 message="Last commit `... rag-deployment: runnable version-aware RAG package`; files include `README.md labs requirements.txt run.sh simple_rag`.",
 pass_rule="Clone succeeds without a login prompt and run.sh is present."),

dict(id="TC-03", area="A. Setup", title="Create the Python environment",
 purpose="run.sh builds a Python 3.12 venv with all packages (Intel-Mac pins applied automatically).",
 commands="""cd ~/b1-test/b1-rag && ./run.sh setup""",
 expect=[r"setup OK · torch \d"], long=True,
 message="`setup OK · torch 2.2.2` (on an Intel Mac; newer torch elsewhere). Takes about 1–2 minutes.",
 pass_rule="The line `setup OK` appears."),

# ── B. Data ─────────────────────────────────────────────────────────────────
dict(id="TC-04", area="B. Data", title="Corpus, manifest and golden set are consistent",
 purpose="The 16 runbooks, the version manifest and the 21 frozen test cases agree with each other.",
 commands=f"""{GO}
.venv/bin/python simple_rag/b1_check.py --no-trap""",
 expect=[r"OK +16 runbooks", r"8 docs, each with exactly 1 current file", r"all 64 conflict values found",
         r"21 cases, unique ids, exact_string 7, multi_hop 3, superseded 9, unanswerable 2", r"\nPASS"],
 message="Lines starting `OK` for corpus, manifest and golden set, ending with `PASS`.",
 pass_rule="Last line is `PASS`; no `FAIL` line."),

dict(id="TC-05", area="B. Data", title="The similarity trap is real",
 purpose="Old and current runbooks are near-duplicates, so similarity alone can't tell them apart.",
 commands=f"""{GO}
.venv/bin/python simple_rag/b1_check.py 2>/dev/null | grep -E "pair similarity|outranks|^PASS" """,
 expect=[r"pair similarity \(current vs old\): min 0\.867 +max 0\.969", r"old version outranks current for 4/8", r"PASS"],
 message="`pair similarity ... min 0.867 max 0.969`, `old version outranks current for 4/8 plain questions`, `PASS`.",
 pass_rule="Similarity ≥ 0.85 for every pair and the old version wins at least once."),

dict(id="TC-06", area="B. Data", title="Frozen files have the published fingerprints",
 purpose="The golden set and manifest are byte-identical to the frozen versions.",
 commands="""cd ~/b1-test/b1-rag
shasum simple_rag/golden_kafka.jsonl simple_rag/corpus/kafka/manifest.json""",
 expect=[r"850c67f2eab21aa1a6afabd481e5c3efccb7e0ba +simple_rag/golden_kafka\.jsonl", r"dea81e27843ffee677863915fa998b1dfaf5ab9c +simple_rag/corpus/kafka/manifest\.json"],
 message="`850c67f2eab21aa1a6afabd481e5c3efccb7e0ba  simple_rag/golden_kafka.jsonl` and `dea81e27843ffee677863915fa998b1dfaf5ab9c  .../manifest.json`.",
 pass_rule="Both fingerprints match exactly."),

# ── C. Chroma ───────────────────────────────────────────────────────────────
dict(id="TC-07", area="C. Chroma", title="Ingest the runbooks into Chroma",
 purpose="All 16 runbooks are chunked, embedded and stored with their version metadata.",
 commands="""cd ~/b1-test/b1-rag
./run.sh ingest 2>/dev/null | grep -E "md · |chunks produced|vectors stored" """,
 expect=[r"md · 16 files", r"chunks produced +17 +from 16 docs", r"vectors stored +17"],
 message="`md · 16 files`, `chunks produced 17 from 16 docs`, `vectors stored 17`.",
 pass_rule="17 vectors stored (one runbook is long enough to split into 2 chunks)."),

dict(id="TC-08", area="C. Chroma", title="Every chunk in Chroma carries its version",
 purpose="The metadata the filter needs is really inside the vector store.",
 commands="""cd ~/b1-test/b1-rag && ./run.sh check | tail -7""",
 expect=[r"17 chunks, every one carries doc_title, version, effective_date, superseded", r"every chunk's values match manifest\.json",
         r'where=\{"superseded": False\} -> 9 chunks from 8 files; where=\{"superseded": True\} -> 8 chunks from 8 files',
         r"splits the store cleanly: 8 current files vs 8 superseded files", r"\nPASS"],
 message="`17 chunks, every one carries ...`, `9 chunks from 8 files` / `8 chunks from 8 files`, `PASS`.",
 pass_rule="Last line `PASS`."),

dict(id="TC-09", area="C. Chroma", title="Raw Chroma query, no project scripts",
 purpose="Confirm the metadata directly with the chromadb library.",
 commands="""cd ~/b1-test/b1-rag && .venv/bin/python - <<'PY'
import chromadb
col = chromadb.PersistentClient(path="simple_rag/.chroma").get_collection("kafka")
cur = col.get(where={"superseded": False}, include=["metadatas"])
old = col.get(where={"superseded": True}, include=["metadatas"])
print("chunks:", col.count(), "| current:", len(cur["ids"]),
      "| superseded:", len(old["ids"]))
dated = all(m["path"].endswith(("-2024.md", "-2025.md"))
            for m in old["metadatas"])
print("every superseded file is an old -20xx version:", dated)
PY""",
 expect=[r"chunks: 17 \| current: 9 \| superseded: 8", r"every superseded file is an old -20xx version: True"],
 message="`chunks: 17 | current: 9 | superseded: 8` and `... old -20xx version: True`.",
 pass_rule="Counts match and the second line says True."),

dict(id="TC-10", area="C. Chroma", title="See the filter's effect inside Chroma",
 purpose="The same question with and without the filter: the stale 2025 runbook disappears.",
 commands="""cd ~/b1-test/b1-rag && ./run.sh inspect 2>/dev/null | sed -n '/question:/,$p'
N=$(./run.sh inspect 2>/dev/null | sed -n '/filter ON/,$p' | grep -c SUPERSEDED)
echo "SUPERSEDED rows with filter ON: $N" """,
 expect=[r"plain top-4 \(filter OFF\)", r"disk-capacity-2025\.md +SUPERSEDED", r"SUPERSEDED rows with filter ON: 0"],
 message="Filter OFF lists `disk-capacity-2025.md SUPERSEDED` at #2; filter ON lists only `current` files; last line `SUPERSEDED rows with filter ON: 0`.",
 pass_rule="OFF shows at least one SUPERSEDED row, ON shows none."),

# ── D. Ablation ─────────────────────────────────────────────────────────────
dict(id="TC-11", area="D. Ablation", title="BEFORE: filter OFF",
 purpose="Measure the original retriever on the 21 frozen cases.",
 commands=f"""{GO}
.venv/bin/python simple_rag/b1_eval.py --off --out local_results 2>/dev/null | tail -7""",
 expect=[r"superseded chunks retrieved +41/84 = 48\.8%", r"superseded_cases +0/9", r"exact_string +7/7", r"multi_hop +0/3"],
 message="`superseded chunks retrieved 41/84 = 48.8%`, `superseded_cases 0/9`, `exact_string 7/7`, `multi_hop 0/3`.",
 pass_rule="Exactly these four numbers (latency varies)."),

dict(id="TC-12", area="D. Ablation", title="AFTER: filter ON",
 purpose="The same 21 cases with the version filter on.",
 commands=f"""{GO}
.venv/bin/python simple_rag/b1_eval.py --on --out local_results 2>/dev/null | tail -7""",
 expect=[r"superseded chunks retrieved +0/84 = 0\.0%", r"superseded_cases +9/9", r"exact_string +7/7", r"multi_hop +3/3"],
 message="`superseded chunks retrieved 0/84 = 0.0%`, `superseded_cases 9/9`, `exact_string 7/7`, `multi_hop 3/3`.",
 pass_rule="0.0% superseded and exact_string still 7/7: **this is the B1 success condition.**"),

dict(id="TC-13", area="D. Ablation", title="Case by case: what the filter fixed and broke",
 purpose="No case gets worse with the filter on.",
 commands="""cd ~/b1-test/b1-rag && .venv/bin/python - <<'PY'
import json
off = json.load(open("local_results/baseline_filter_off.json"))["cases"]
on = json.load(open("local_results/version_filter_on.json"))["cases"]
w = lambda p: "-" if p is None else ("PASS" if p else "FAIL")
for a, b in zip(off, on):
    print(f"{a['id']}  {a['type']:<13} OFF {w(a['pass']):<4} -> ON {w(b['pass'])}")
pairs = list(zip(off, on))
fixed = sum(a["pass"] is False and b["pass"] is True for a, b in pairs)
broken = sum(a["pass"] is True and b["pass"] is False for a, b in pairs)
print("cases fixed by the filter:", fixed)
print("cases broken by the filter:", broken)
PY""",
 expect=[r"kafka-001  superseded +OFF FAIL -> ON PASS", r"kafka-010  exact_string +OFF PASS -> ON PASS", r"cases fixed by the filter: 12", r"cases broken by the filter: 0"],
 message="21 rows; superseded and multi_hop go `FAIL -> PASS`, exact_string stays `PASS -> PASS`; `cases fixed by the filter: 12`, `cases broken by the filter: 0`.",
 pass_rule="Fixed = 12, broken = 0."),

dict(id="TC-14", area="D. Ablation", title="Results are deterministic and match the committed ones",
 purpose="Re-running gives the same cases; your run equals the published results.",
 commands=f"""{GO}
.venv/bin/python simple_rag/b1_eval.py --off --out local_results2 >/dev/null 2>&1
.venv/bin/python - <<'PY'
import json
def key(f):
    cases = json.load(open(f))["cases"]
    return [(c["id"], c["pass"], [h["file"] for h in c["retrieved"]]) for c in cases]
off, on = "baseline_filter_off.json", "version_filter_on.json"
print("re-run identical:", key(f"local_results/{{off}}") == key(f"local_results2/{{off}}"))
print("OFF matches committed:", key(f"local_results/{{off}}") == key(f"simple_rag/results/{{off}}"))
print("ON matches committed:", key(f"local_results/{{on}}") == key(f"simple_rag/results/{{on}}"))
PY""",
 expect=[r"re-run identical: True", r"OFF matches committed: True", r"ON matches committed: True"],
 message="`re-run identical: True`, `OFF matches committed: True`, `ON matches committed: True`.",
 pass_rule="All three True."),

dict(id="TC-15", area="D. Ablation", title="The filter adds no meaningful latency",
 purpose="OFF and ON timed fairly (alternating, same process).",
 commands=f"""{GO}
.venv/bin/python simple_rag/b1_eval.py --latency 2 --out local_results >/dev/null 2>&1
.venv/bin/python - <<'PY'
import json
d = json.load(open("local_results/latency.json"))
off, on, delta = d["off"]["median_ms"], d["on"]["median_ms"], d["median_delta_ms"]
print("OFF", off, "ms | ON", on, "ms | delta", delta, "ms")
print("latency check:", "PASS" if abs(delta) < 10 else "FAIL")
PY""",
 expect=[r"OFF [\d.]+ ms \| ON [\d.]+ ms \| delta -?[\d.]+ ms", r"latency check: PASS"],
 message="`OFF ~50 ms | ON ~51 ms | delta ~1 ms` (machine-dependent) and `latency check: PASS`.",
 pass_rule="Difference under 10 ms."),

dict(id="TC-16", area="D. Ablation", title="Ablation summary table",
 purpose="One table with all metrics, OFF vs ON.",
 commands=f"""{GO}
.venv/bin/python simple_rag/b1_eval.py --table --out local_results 2>/dev/null | sed -n '7,13p'""",
 expect=[r"\| \*\*Superseded chunks retrieved\*\* \| \*\*48\.8%\*\* \(41/84\) \| \*\*0\.0%\*\* \(0/84\)", r"Exact-string cases passed \| 7/7 \(100%\) \| 7/7 \(100%\)"],
 message="Markdown table: superseded `48.8% (41/84)` → `0.0% (0/84)`, exact-string `7/7` → `7/7`, multi-hop `0/3` → `3/3`.",
 pass_rule="Table shows these values."),

# ── E. Answers (LLM) ────────────────────────────────────────────────────────
dict(id="TC-17", area="E. Answers (LLM)", title="Provide the API key (.env)", llm=True,
 purpose="ask needs an OpenAI-compatible key; it stays local and is never committed.",
 commands="""cd ~/b1-test/b1-rag
cp ~/Desktop/AI-Architect_L2_Aug_2026/project_10082026/.env .env && chmod 600 .env
grep -c "^OPENAI_API_KEY=" .env
git status --short .env; echo "git sees .env: $(git status --short .env | wc -l | tr -d ' ')" """,
 expect=[r"(?m)^1$", r"git sees \.env: 0"],
 message="`1` (one key line) and `git sees .env: 0` (gitignored). The key itself is never printed.",
 pass_rule="Key present, git ignores the file."),

dict(id="TC-18", area="E. Answers (LLM)", title="Stale-threshold question, filter ON", llm=True, soft=True,
 purpose="The 87% disk question: only current runbooks reach the LLM; the answer uses 85%.",
 commands=f"""cd ~/b1-test/b1-rag
Q="{Q87}"
./run.sh ask "$Q" 2>/dev/null | sed -n '/retrieved/,/sources offered/p'""",
 expect=[r"disk-capacity\s", r"85"], expect_not=[r"disk-capacity-2025"],
 message="Retrieved list has `disk-capacity` but **not** `disk-capacity-2025`; the answer says it pages because the threshold is **85%**.",
 pass_rule="No 2025 file retrieved; answer cites 85%."),

dict(id="TC-19", area="E. Answers (LLM)", title="Same question, filter OFF (compare)", llm=True,
 purpose="Show the problem: the outdated 90% runbook is in the context.",
 commands=f"""cd ~/b1-test/b1-rag
Q="{Q87}"
./run.sh ask-off "$Q" 2>/dev/null | sed -n '/retrieved/,/sources offered/p'""",
 expect=[r"disk-capacity-2025"],
 message="Retrieved list includes `disk-capacity-2025` (the old 90% rule) at #2. The answer may still be right; that's luck, not design.",
 pass_rule="`disk-capacity-2025` is retrieved."),

dict(id="TC-20", area="E. Answers (LLM)", title="Exact value question", llm=True, soft=True,
 purpose="An exact port number comes from the current runbook only.",
 commands="""cd ~/b1-test/b1-rag
Q="What port is the schema registry on?"
./run.sh ask "$Q" 2>/dev/null | sed -n '/generate/,/sources offered/p'""",
 expect=[r"8085"], expect_not=[r"8081"],
 message="Answer says port **8085**, never the old 8081.",
 pass_rule="8085 present, 8081 absent."),

dict(id="TC-21", area="E. Answers (LLM)", title="Renamed on-call service", llm=True, soft=True,
 purpose="A renamed PagerDuty service: the old name must not appear.",
 commands="""cd ~/b1-test/b1-rag
Q="Which PagerDuty service do I trigger for a production Kafka problem?"
./run.sh ask "$Q" 2>/dev/null | sed -n '/generate/,/sources offered/p'""",
 expect=[r"streaming-platform-prod"], expect_not=[r"kafka-ops"],
 message="Answer names **streaming-platform-prod**, never `kafka-ops`.",
 pass_rule="Current name only."),

dict(id="TC-22", area="E. Answers (LLM)", title="Unanswerable question", llm=True, soft=True,
 purpose="The corpus has no message-size limit; the system should say so, not invent one.",
 commands="""cd ~/b1-test/b1-rag
Q="What's the largest message size our brokers will accept?"
./run.sh ask "$Q" 2>/dev/null | sed -n '/generate/,/sources offered/p'""",
 expect=[r"(?i)(not|no |doesn|don't|cannot|isn't|unable)"],
 message="The answer says the runbooks don't specify it. It shouldn't give a number such as 1 MB.",
 pass_rule="Judge by reading: a refusal or \"not documented\" passes, an invented number fails."),

# ── F. Negative tests ───────────────────────────────────────────────────────
dict(id="TC-23", area="F. Negative tests", title="Broken manifest is caught",
 purpose="Mark an old file current, make a version a string, break a date: the checks must fail.",
 commands="""cd ~/b1-test/b1-rag && M=simple_rag/corpus/kafka/manifest.json && cp $M /tmp/b1-manifest.bak
.venv/bin/python - <<'PY'
import json; p = "simple_rag/corpus/kafka/manifest.json"; m = json.load(open(p))
m["files"]["disk-capacity-2025.md"]["superseded"] = False
m["files"]["topic-retention.md"]["version"] = "3"
m["files"]["schema-registry.md"]["effective_date"] = "2026-3-20"
json.dump(m, open(p, "w"), indent=2)
PY
.venv/bin/python simple_rag/b1_check.py --no-trap > /tmp/b1-out.txt; echo "exit=$?"
grep -E "FAIL" /tmp/b1-out.txt | head -4
cp /tmp/b1-manifest.bak $M
echo "restored: $(.venv/bin/python simple_rag/b1_check.py --no-trap | tail -1)" """,
 expect=[r"exit=1", r"is not int", r"2 current files, need exactly 1", r"is not YYYY-MM-DD", r"restored: PASS"],
 message="`exit=1`, FAIL lines naming each injected error, then `restored: PASS`.",
 pass_rule="Checks fail on bad data and pass again after restore."),

dict(id="TC-24", area="F. Negative tests", title="Broken golden set is caught",
 purpose="A case that cites the old file, and a banned string a correct answer contains.",
 commands="""cd ~/b1-test/b1-rag && G=simple_rag/golden_kafka.jsonl && cp $G /tmp/b1-golden.bak
.venv/bin/python - <<'PY'
import json; p = "simple_rag/golden_kafka.jsonl"; rows = [json.loads(l) for l in open(p)]
rows[0]["expect"]["must_cite"] = [{"doc": "Kafka Broker Disk Capacity Runbook", "version": 2}]
rows[2]["expect"]["must_not_contain"].append("3 days")
open(p, "w").write("".join(json.dumps(r) + "\\n" for r in rows))
PY
.venv/bin/python simple_rag/b1_check.py --no-trap > /tmp/b1-out.txt; echo "exit=$?"
tail -1 /tmp/b1-out.txt
cp /tmp/b1-golden.bak $G
echo "restored: $(.venv/bin/python simple_rag/b1_check.py --no-trap | tail -1)" """,
 expect=[r"exit=1", r"FAIL \(4\)", r"restored: PASS"],
 message="`exit=1`, `FAIL (4)`, then `restored: PASS`.",
 pass_rule="Fails with 4 findings, passes after restore."),

dict(id="TC-25", area="F. Negative tests", title="Chroma without metadata is caught",
 purpose="Ingest without the manifest (like the pre-Step-8 system): the Chroma check must fail.",
 commands="""cd ~/b1-test/b1-rag && export RAG_TRACE=0
mv simple_rag/corpus/kafka/manifest.json /tmp/b1-manifest.keep
export RAG_CORPUS=simple_rag/corpus/kafka RAG_COLLECTION=kafka_nometa
.venv/bin/python simple_rag/rag.py ingest --formats md >/dev/null 2>&1
mv /tmp/b1-manifest.keep simple_rag/corpus/kafka/manifest.json
.venv/bin/python simple_rag/b1_check.py --no-trap --chroma > /tmp/b1-out.txt 2>&1
echo "exit=$?"
grep -m1 "no \\['doc_title'" /tmp/b1-out.txt; tail -1 /tmp/b1-out.txt
.venv/bin/python - <<'PY'
import chromadb
chromadb.PersistentClient(path="simple_rag/.chroma").delete_collection("kafka_nometa")
print("test collection removed")
PY
export RAG_COLLECTION=kafka""",
 expect=[r"exit=1", r"no \['doc_title', 'version', 'effective_date', 'superseded'\] in Chroma metadata", r"FAIL \(\d+\)", r"test collection removed"],
 message="`exit=1`, `... no ['doc_title', 'version', 'effective_date', 'superseded'] in Chroma metadata ...`, `FAIL (18)`, `test collection removed`.",
 pass_rule="The check refuses a store without version metadata."),

# ── G. Scenarios ────────────────────────────────────────────────────────────
dict(id="TC-26", area="G. Scenarios", title="The filter trusts the metadata (wrong flag)",
 purpose="If someone flips the flags by mistake, the filter serves the wrong file. This proves the manifest must be maintained.",
 commands="""cd ~/b1-test/b1-rag
.venv/bin/python - <<'PY'
import json; p = "simple_rag/corpus/kafka/manifest.json"; m = json.load(open(p))
m["files"]["disk-capacity.md"]["superseded"] = True
m["files"]["disk-capacity-2025.md"]["superseded"] = False
json.dump(m, open(p, "w"), indent=2)
PY
./run.sh ingest >/dev/null 2>&1
echo "== flags swapped =="
./run.sh inspect 2>/dev/null | sed -n '/filter ON/,$p' | grep disk-capacity
git checkout -- simple_rag/corpus/kafka/manifest.json && ./run.sh ingest >/dev/null 2>&1
echo "== restored =="
./run.sh inspect 2>/dev/null | sed -n '/filter ON/,$p' | grep disk-capacity""",
 expect=[r"== flags swapped ==\s+#1 .*disk-capacity-2025\.md +current", r"== restored ==\s+#1 .*disk-capacity\.md +current"],
 message="After the swap, filter ON returns `disk-capacity-2025.md` as current. After the restore it returns `disk-capacity.md`.",
 pass_rule="The swap changes what's served, and the restore brings it back."),

dict(id="TC-27", area="G. Scenarios", title="Publish a new runbook version",
 purpose="The documented update procedure: add v4, mark v3 superseded, re-ingest. Only v4 is served.",
 commands="""cd ~/b1-test/b1-rag
.venv/bin/python - <<'PY'
import json, pathlib
k = pathlib.Path("simple_rag/corpus/kafka")
t = (k / "disk-capacity.md").read_text()
t = t.replace("Version 3 · Effective 2026-05-01", "Version 4 · Effective 2026-09-01")
(k / "disk-capacity-v4.md").write_text(t.replace("**85%**", "**80%**"))
m = json.load(open(k / "manifest.json"))
m["files"]["disk-capacity.md"]["superseded"] = True
m["files"]["disk-capacity-v4.md"] = {"doc": "Kafka Broker Disk Capacity Runbook",
    "version": 4, "effective_date": "2026-09-01", "superseded": False}
json.dump(m, open(k / "manifest.json", "w"), indent=2)
PY
./run.sh ingest >/dev/null 2>&1
echo "== v4 published =="
Q="At what disk usage does a Kafka broker page someone?"
./run.sh inspect "$Q" 2>/dev/null | sed -n '/filter ON/,$p' | grep disk-capacity
rm simple_rag/corpus/kafka/disk-capacity-v4.md
git checkout -- simple_rag/corpus/kafka/manifest.json
./run.sh ingest >/dev/null 2>&1 && echo "== restored to the published corpus ==" """,
 expect=[r"== v4 published ==\s+#1 .*disk-capacity-v4\.md +current", r"== restored to the published corpus =="],
 expect_not=[r"== v4 published ==\s+(#\d.*\n\s*)*#\d .*disk-capacity\.md "],
 message="Filter ON returns `disk-capacity-v4.md` (current) and no other disk-capacity file; then `== restored to the published corpus ==`.",
 pass_rule="Only v4 is served while it's current."),

# ── H. Project branch ───────────────────────────────────────────────────────
dict(id="TC-28", area="H. Project branch", title="The golden set was frozen before any code change",
 purpose="Git history proves the tests existed before the fix.",
 commands=f"""cd ~/b1-test
{REPO}
git clone -q -b track-b-kafka-version-aware $R b1-project && cd b1-project
git log --format='%h %ad %s' --date=short -- simple_rag/golden_kafka.jsonl
git log --format='%h %s' 6b918c2..HEAD -- simple_rag/rag.py | tail -1
git merge-base --is-ancestor 2cff45a 8c97952 \\
  && echo "freeze 2cff45a comes before the first rag.py change 8c97952: True" """,
 expect=[r"2cff45a \d{4}-\d\d-\d\d Freeze B1 golden set before version-aware retrieval", r"8c97952 B1 Track B step 7", r"comes before the first rag\.py change 8c97952: True"],
 message="One golden-set commit `2cff45a ... Freeze B1 golden set ...`; first rag.py change `8c97952 ... step 7`; `... True`.",
 pass_rule="The freeze commit is an ancestor of the first rag.py change."),

dict(id="TC-29", area="H. Project branch", title="No secrets or personal email in the public repo",
 purpose="The published code holds no API keys, .env files or personal email.",
 commands="""cd ~/b1-test/b1-project
S=$(git grep -IE 'sk-[A-Za-z0-9]{20,}|OPENAI_API_KEY=[A-Za-z0-9-]{12,}' | wc -l | tr -d ' ')
echo "secret-like strings: $S"
echo ".env files tracked: $(git ls-files | grep -cE '(^|/)\\.env$')"
echo "gmail in commit authors: $(git log --format='%ae %ce' | grep -c gmail)" """,
 expect=[r"secret-like strings: 0", r"\.env files tracked: 0", r"gmail in commit authors: 0"],
 message="`secret-like strings: 0`, `.env files tracked: 0`, `gmail in commit authors: 0`.",
 pass_rule="All zero."),

dict(id="TC-30", area="H. Project branch", title="Rebuild every step from scratch (optional, ~4 min)", long=True,
 purpose="One script replays Steps 0–12 from a fresh clone and compares fingerprints.",
 commands="""cd ~/b1-test/b1-project
export SKIP_STEP2=1 VENV=~/b1-test/b1-rag/.venv
bash b1-track-b/tools/recreate_track_b.sh ~/b1-test/rebuild 2>&1 \\
  | grep -E "MATCH|AFTER:|Done"
""",
 expect=[r"AFTER: 0\.0% superseded · 9/9 · 7/7 · 3/3", r"golden_kafka\.jsonl MATCH", r"rag\.py \(step 10\) +MATCH", r"Done · Steps 0–12 recreated"],
 message="`AFTER: 0.0% superseded · 9/9 · 7/7 · 3/3`, seven `... MATCH` lines, `Done · Steps 0–12 recreated`.",
 pass_rule="Every fingerprint says MATCH."),
]

CLEANUP = """rm -rf ~/b1-test /tmp/b1-manifest.bak /tmp/b1-golden.bak /tmp/b1-out.txt"""
