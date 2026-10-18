"""Run every B1 Track B test case exactly as printed in the test plan, and check the messages.

    python3 run_tests.py                     # all cases, in ~/b1-test (deleted and recreated)
    python3 run_tests.py --root /tmp/b1test  # use another folder instead of ~/b1-test
    python3 run_tests.py --skip-llm          # skip the cases that call the LLM (no .env needed)
    python3 run_tests.py --skip-long         # skip the 4-minute full rebuild (TC-30)
    python3 run_tests.py --only TC-11,TC-12  # run selected cases (needs the earlier setup done)
    python3 run_tests.py --shell zsh         # run the commands in zsh (the macOS default shell)

Exit code 0 = every hard check passed. LLM-dependent checks are reported as WARN, not FAIL.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_cases import CASES, CLEANUP  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.expanduser("~/b1-test"))
    ap.add_argument("--skip-llm", action="store_true")
    ap.add_argument("--skip-long", action="store_true")
    ap.add_argument("--only", default="")
    ap.add_argument("--log", default="")
    ap.add_argument("--shell", default="bash", choices=["bash", "zsh"], help="shell to run the commands in")
    a = ap.parse_args()
    only = {x.strip() for x in a.only.split(",") if x.strip()}
    root = os.path.abspath(os.path.expanduser(a.root))
    log = open(a.log, "w") if a.log else None
    results = []
    for c in CASES:
        if only and c["id"] not in only:
            continue
        if (a.skip_llm and c.get("llm")) or (a.skip_long and c.get("long") and c["id"] == "TC-30"):
            results.append((c["id"], "SKIP", c["title"], 0.0, []))
            continue
        cmd = c["commands"].replace("~/b1-test", root)
        t0 = time.time()
        p = subprocess.run([a.shell, "-c", cmd], capture_output=True, text=True, timeout=1200)
        out = p.stdout + p.stderr
        dt = time.time() - t0
        problems = [f"missing: {rx}" for rx in c.get("expect", []) if not re.search(rx, out)]
        problems += [f"must not appear: {rx}" for rx in c.get("expect_not", []) if re.search(rx, out)]
        status = "PASS" if not problems else ("WARN" if c.get("soft") else "FAIL")
        results.append((c["id"], status, c["title"], dt, problems))
        print(f"{status:<4}  {c['id']}  {c['title']}  ({dt:.0f}s)")
        for pr in problems:
            print(f"        {pr}")
        if log:
            log.write(f"\n===== {c['id']} {status} ({dt:.0f}s) =====\n$ {cmd}\n{out}\n")
    n = {s: sum(r[1] == s for r in results) for s in ("PASS", "WARN", "FAIL", "SKIP")}
    print(f"\n{n['PASS']} PASS · {n['WARN']} WARN · {n['FAIL']} FAIL · {n['SKIP']} SKIP")
    print(f"cleanup when done:  {CLEANUP.replace('~/b1-test', root)}")
    return 1 if n["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
