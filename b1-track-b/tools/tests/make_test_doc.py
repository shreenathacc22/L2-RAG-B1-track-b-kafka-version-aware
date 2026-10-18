"""Write the test-plan Markdown from test_cases.py (the same source the runner executes).

    python3 make_test_doc.py > test_plan.md
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_cases import CASES, CLEANUP  # noqa: E402

PRE = {
    "A. Setup": "None. Start here.",
    "B. Data": "TC-02 and TC-03 done.",
    "C. Chroma": "TC-03 done. TC-08 to TC-10 also need TC-07 (ingest).",
    "D. Ablation": "TC-07 done (ingest). TC-13, TC-14 and TC-16 use the files written by TC-11 and TC-12.",
    "E. Answers (LLM)": "TC-07 done. TC-18 to TC-22 need TC-17 (.env) and internet access.",
    "F. Negative tests": "TC-03 done. Each test restores the data itself.",
    "G. Scenarios": "TC-07 done. Each scenario restores the published corpus at the end.",
    "H. Project branch": "TC-02 done. TC-30 also needs TC-03 (it reuses that Python environment).",
}
TIME = {"TC-03": "~1–2 min", "TC-30": "~4 min"}
KEY = {
    "TC-01": "versions of git, uv, Python", "TC-02": "clone OK, run.sh present", "TC-03": "setup OK · torch 2.2.2",
    "TC-04": "PASS (16 runbooks, 8 docs, 21 cases)", "TC-05": "similarity 0.867–0.969; old wins 4/8",
    "TC-06": "sha1 850c67f2… / dea81e27…", "TC-07": "vectors stored 17", "TC-08": "9 vs 8 chunks · PASS",
    "TC-09": "chunks 17 · current 9 · superseded 8", "TC-10": "OFF: 2025 file #2; ON: 0 superseded",
    "TC-11": "48.8% · 0/9 · 7/7 · 0/3", "TC-12": "0.0% · 9/9 · 7/7 · 3/3", "TC-13": "fixed 12 · broken 0",
    "TC-14": "3 × True", "TC-15": "delta < 10 ms · PASS", "TC-16": "48.8% → 0.0% table",
    "TC-17": ".env present, ignored by git", "TC-18": "answer 85%, no 2025 file", "TC-19": "2025 file retrieved",
    "TC-20": "8085, never 8081", "TC-21": "streaming-platform-prod", "TC-22": "says not documented",
    "TC-23": "exit=1 … restored: PASS", "TC-24": "FAIL (4) … restored: PASS", "TC-25": "exit=1 · FAIL (18)",
    "TC-26": "swap serves 2025 file; restore fixes", "TC-27": "only disk-capacity-v4.md served",
    "TC-28": "freeze before code: True", "TC-29": "all zero", "TC-30": "7 × MATCH · Done",
}

out = []
w = out.append
w("# Test Scenarios: B1 Track B Version-Aware RAG\n")
w("| | |\n|---|---|")
w("| What this is | 30 copy-paste test cases that prove the B1 system works, from a clean clone of the public GitHub repo |")
w("| Repo | https://github.com/shreenathacc22/L2-RAG-B1-track-b-kafka-version-aware (branches `rag-deployment`, `track-b-kafka-version-aware`) |")
w("| Works in | macOS Terminal (zsh) or bash. Everything happens in `~/b1-test`, which is deleted at the end |")
w("| Time | About 8 minutes for all 30 (TC-30 alone takes about 4) |")
w("| Verified | 2026-10-18: all 30 PASS from a fresh GitHub clone (bash); shell-heavy cases re-verified in zsh |")
w("")
w("## 1. How to use this document\n")
w("1. Open **Terminal**.")
w("2. For each test case, copy the whole grey **Commands** block, paste it, and press Enter.")
w("3. Compare what you see with **Expected message**. Small differences in timings (ms, seconds) are normal.")
w("4. Tick **Pass** or **Fail** in the test record (section 4).")
w("5. Run the cases **in order**. Later cases use what earlier ones built (see **Pre-condition**).")
w("")
w("**Automatic alternative:** the same 30 cases run unattended with one command, which checks every expected message for you:")
w("```bash")
w("git clone -q -b track-b-kafka-version-aware https://github.com/shreenathacc22/L2-RAG-B1-track-b-kafka-version-aware.git /tmp/b1-tests-src")
w("python3 /tmp/b1-tests-src/b1-track-b/tools/tests/run_tests.py --shell zsh      # add --skip-llm if you have no .env")
w("```")
w("Expect the last line `30 PASS · 0 WARN · 0 FAIL · 0 SKIP`. LLM-worded answers are WARN, not FAIL, if the wording differs.")
w("")
w("## 2. Test matrix\n")
w("| ID | Area | Test | LLM / key | Time | Key expected result |")
w("|---|---|---|---|---|---|")
for c in CASES:
    key = KEY[c["id"]]
    w(f"| {c['id'].replace('-', '‑')} | {c['area'][3:]} | {c['title']} | {'yes' if c.get('llm') else '—'} | {TIME.get(c['id'], '< 1 min')} | {key} |")
w("")
w("## 3. Test cases\n")
area = None
for c in CASES:
    if c["area"] != area:
        area = c["area"]
        w(f"### {area}\n")
        w(f"*Pre-condition for this group:* {PRE[area]}\n")
    flags = []
    if c.get("llm"):
        flags.append("needs `.env` and internet")
    if c.get("soft"):
        flags.append("LLM wording varies: judge the meaning")
    if c.get("long"):
        flags.append(f"takes {TIME.get(c['id'], 'a while')}")
    w(f"#### {c['id']} · {c['title']}\n")
    w(f"**Purpose:** {c['purpose']}" + (f"  *({'; '.join(flags)})*" if flags else "") + "\n")
    w("**Commands** (copy all, paste, Enter):\n")
    w("```bash")
    w(c["commands"].rstrip())
    w("```\n")
    w(f"**Expected message:** {c['message']}\n")
    w(f"**Pass rule:** {c['pass_rule']}\n")
w("### Cleanup\n")
w("Run this when you're finished. It deletes the test folder, including the `.env` copy made in TC-17:\n")
w("```bash")
w(CLEANUP)
w("```\n")
w("## 4. Test record\n")
w("| ID | Test | Pass | Fail | Notes |")
w("|---|---|---|---|---|")
for c in CASES:
    w(f"| {c['id']} | {c['title']} | ☐ | ☐ | |")
w("")
w("Tested by: ____________________   Date: ____________   Result: ____ / 30 PASS\n")
w("## 5. If a test fails\n")
w("| Symptom | Likely cause | Fix |")
w("|---|---|---|")
w("| `No .venv yet — run: ./run.sh setup` | TC-03 not run, or it failed | Run TC-03 and read its last lines |")
w("| `collection ... is empty` / 0 chunks | TC-07 (ingest) not run | Run TC-07, then retry |")
w("| TC-11/12 numbers differ | Corpus or golden set changed | Run TC-06: the fingerprints must match; re-clone if not |")
w("| `ask needs .env` | TC-17 not done | Run TC-17 (or create `.env` with your own key) |")
w("| TC-18 to 22 hang or time out | No internet, or the LLM proxy is down | Retry later. TC-01 to 17 and 23 to 30 don't need the LLM |")
w("| TC-26 or TC-27 left the corpus modified | The block was interrupted | `cd ~/b1-test/b1-rag && git checkout -- simple_rag/corpus && rm -f simple_rag/corpus/kafka/disk-capacity-v4.md && ./run.sh ingest` |")
w("| `fatal: destination path ... already exists` | An earlier run left `~/b1-test` behind | Run the cleanup command, then start at TC-02 |")
print("\n".join(out))
