"""B1 evaluator: run the frozen golden set through retrieval and score it.

    export RAG_CORPUS=simple_rag/corpus/kafka RAG_COLLECTION=kafka
    python simple_rag/rag.py ingest --formats md     # once, before evaluating
    python simple_rag/b1_eval.py --off               # BEFORE: filter OFF  (Step 7)
    python simple_rag/b1_eval.py --on                # AFTER:  filter ON   (Step 11)
    python simple_rag/b1_eval.py                     # both, plus the ablation table
    python simple_rag/b1_eval.py --latency 5         # fair latency: OFF/ON alternated, 5 rounds (Step 12)
    python simple_rag/b1_eval.py --table             # ablation_summary.md from the SAVED results (Step 12)

Retrieval only: no LLM, no API key, deterministic. Which retrieved chunks are
superseded is looked up in corpus/kafka/manifest.json by file name, so this
works on the unchanged retriever too, before any metadata reaches Chroma.

Scores (per the B1 guide):
    superseded rate   superseded chunks retrieved / all chunks retrieved   (headline, target 0%)
    superseded cases  every must_cite file retrieved AND no must_not_cite file retrieved
    multi_hop cases   same rule, two documents
    exact_string      every expected value appears verbatim in the retrieved text (must stay flat)
    latency           median ms per retrieve() call, after one warm-up query
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import inspect
import io
import json
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path

os.environ.setdefault("RAG_CORPUS", "simple_rag/corpus/kafka")
os.environ.setdefault("RAG_COLLECTION", "kafka")
os.environ.setdefault("RAG_TRACE", "0")          # this script is the measurement

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rag  # noqa: E402

GOLDEN = HERE / "golden_kafka.jsonl"
MANIFEST = HERE / "corpus" / "kafka" / "manifest.json"
RESULTS = HERE / "results"
K = 4
FILES = {"off": "baseline_filter_off.json", "on": "version_filter_on.json"}


def retrieve(q: str, version_aware: bool) -> tuple[list[dict], float]:
    """rag.retrieve prints a live table; keep the numbers, drop the printing."""
    kwargs = {"version_aware": True} if version_aware else {}
    with contextlib.redirect_stdout(io.StringIO()):
        t0 = time.perf_counter()
        hits = rag.retrieve(q, k=K, **kwargs)
        ms = (time.perf_counter() - t0) * 1000
    return hits, ms


def run(mode: str) -> dict:
    on = mode == "on"
    if on and "version_aware" not in inspect.signature(rag.retrieve).parameters:
        sys.exit("filter ON is not built yet: rag.retrieve() has no version_aware flag (Steps 9-10).")
    files = json.loads(MANIFEST.read_text(encoding="utf-8"))["files"]
    by_key = {(m["doc"], m["version"]): n for n, m in files.items()}
    cases = [json.loads(l) for l in GOLDEN.read_text(encoding="utf-8").splitlines() if l.strip()]
    if rag.collection().count() == 0:
        sys.exit(f"collection '{rag.COLLECTION}' is empty — run: python simple_rag/rag.py ingest --formats md")

    retrieve("warm-up query", on)                 # pay model/index load before timing
    rows, lat, total, stale = [], [], 0, 0
    for c in cases:
        hits, ms = retrieve(c["question"], on)
        lat.append(ms)
        got = [Path(h["path"]).name for h in hits]
        sup = [files[g]["superseded"] for g in got]
        total += len(got)
        stale += sum(sup)
        e = c["expect"]
        need = [by_key[(r["doc"], r["version"])] for r in e["must_cite"]]
        banned = [by_key[(r["doc"], r["version"])] for r in e["must_not_cite"]]
        text = "\n".join(h["text"] for h in hits)
        reasons = []
        if c["type"] in ("superseded", "multi_hop"):
            reasons += [f"missing {n}" for n in need if n not in got]
            reasons += [f"retrieved superseded {n}" for n in banned if n in got]
        elif c["type"] == "exact_string":
            reasons += [f"value not in context: {f!r}" for f in e["facts"] if f not in text]
        rows.append({"id": c["id"], "type": c["type"], "question": c["question"],
                     "pass": None if c["type"] == "unanswerable" else not reasons,
                     "reasons": reasons, "ms": round(ms, 1),
                     "retrieved": [{"rank": h["rank"], "file": g, "superseded": s,
                                    "similarity": h["similarity"]}
                                   for h, g, s in zip(hits, got, sup)]})

    def score(t):
        r = [x for x in rows if x["type"] == t]
        return {"passed": sum(x["pass"] for x in r), "cases": len(r)}

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=HERE,
                            capture_output=True, text=True).stdout.strip()
    return {
        "mode": mode, "version_aware": on, "k": K, "collection": rag.COLLECTION,
        "corpus": os.environ["RAG_CORPUS"], "embed_model": rag.EMBED_MODEL,
        "golden_sha1": hashlib.sha1(GOLDEN.read_bytes()).hexdigest(), "git_commit": commit,
        "summary": {
            "superseded_chunks": stale, "total_chunks": total,
            "superseded_rate_pct": round(100 * stale / total, 1) if total else 0.0,
            "superseded_cases": score("superseded"), "exact_string": score("exact_string"),
            "multi_hop": score("multi_hop"),
            "median_retrieval_ms": round(statistics.median(lat), 1),
        },
        "cases": rows,
    }


def show(r: dict) -> None:
    s = r["summary"]
    print(f"\nB1 eval · filter {r['mode'].upper()} · k={r['k']} · collection={r['collection']} "
          f"· golden sha1 {r['golden_sha1'][:8]} · commit {r['git_commit']}")
    for c in r["cases"]:
        mark = "  -  " if c["pass"] is None else ("PASS " if c["pass"] else "FAIL ")
        files = ", ".join(f"{h['file']}{'*' if h['superseded'] else ''}" for h in c["retrieved"])
        print(f"  {mark} {c['id']}  {c['type']:<13} {files}")
        for why in c["reasons"]:
            print(f"          {why}")
    print("  (* = superseded file)\n")
    print(f"  superseded chunks retrieved  {s['superseded_chunks']}/{s['total_chunks']} = "
          f"{s['superseded_rate_pct']}%")
    for t in ("superseded_cases", "exact_string", "multi_hop"):
        print(f"  {t:<28} {s[t]['passed']}/{s[t]['cases']}")
    print(f"  median retrieval latency     {s['median_retrieval_ms']} ms")


def latency(rounds: int) -> dict:
    """Fair timing: every question runs OFF then ON back to back, `rounds` times, in one
    process, so warm caches and machine load hit both modes equally."""
    cases = [json.loads(l) for l in GOLDEN.read_text(encoding="utf-8").splitlines() if l.strip()]
    retrieve("warm-up query", False)
    retrieve("warm-up query", True)
    ms = {"off": [], "on": []}
    for _ in range(rounds):
        for c in cases:
            for mode in ("off", "on"):
                ms[mode].append(retrieve(c["question"], mode == "on")[1])
    q = lambda xs, p: round(sorted(xs)[min(len(xs) - 1, int(p * len(xs)))], 1)
    out = {"rounds": rounds, "calls_per_mode": len(ms["off"]),
           **{m: {"median_ms": round(statistics.median(v), 1), "p90_ms": q(v, 0.9)} for m, v in ms.items()}}
    out["median_delta_ms"] = round(out["on"]["median_ms"] - out["off"]["median_ms"], 1)
    return out


def table(off: dict, on: dict, lat: dict | None = None) -> str:
    a, b = off["summary"], on["summary"]
    pct = lambda d: f"{d['passed']}/{d['cases']} ({round(100 * d['passed'] / d['cases'])}%)"
    lines = [
        "# B1 Track B: ablation summary", "",
        f"Corpus `{off['corpus']}` · collection `{off['collection']}` · k={off['k']} · "
        f"embedder `{off['embed_model']}` · golden sha1 `{off['golden_sha1'][:12]}`", "",
        "Only one thing changes between the runs: `where={\"superseded\": False}` on the Chroma query.", "",
        "| Metric | Filter OFF | Filter ON | Target |", "|---|---|---|---|",
        f"| **Superseded chunks retrieved** | **{a['superseded_rate_pct']}%** ({a['superseded_chunks']}/{a['total_chunks']}) "
        f"| **{b['superseded_rate_pct']}%** ({b['superseded_chunks']}/{b['total_chunks']}) | 0% |",
        f"| Superseded cases passed | {pct(a['superseded_cases'])} | {pct(b['superseded_cases'])} | improve |",
        f"| Exact-string cases passed | {pct(a['exact_string'])} | {pct(b['exact_string'])} | stay flat |",
        f"| Multi-hop cases passed | {pct(a['multi_hop'])} | {pct(b['multi_hop'])} | improve |",
        (f"| Median retrieval latency (fair, {lat['calls_per_mode']} calls each, interleaved) | "
         f"{lat['off']['median_ms']} ms | {lat['on']['median_ms']} ms | small change |" if lat else
         f"| Median retrieval latency (single runs) | {a['median_retrieval_ms']} ms | {b['median_retrieval_ms']} ms | small change |"),
        "", f"Runs: OFF at commit `{off['git_commit']}`, ON at commit `{on['git_commit']}`; "
            f"same golden sha1 in both: **{off['golden_sha1'] == on['golden_sha1']}**.",
        "", "## Case by case", "",
        "| Case | Type | OFF | ON | Superseded files retrieved OFF -> ON |", "|---|---|---|---|---|",
    ]
    word = lambda x: "-" if x["pass"] is None else ("PASS" if x["pass"] else "FAIL")
    for x, y in zip(off["cases"], on["cases"]):
        so = sum(h["superseded"] for h in x["retrieved"]); sn = sum(h["superseded"] for h in y["retrieved"])
        lines.append(f"| {x['id']} | {x['type']} | {word(x)} | {word(y)} | {so} -> {sn} |")
    still = [y["id"] for y in on["cases"] if y["pass"] is False]
    lines += ["", f"Failing cases with the filter ON: **{', '.join(still) if still else 'none'}**. "
              "Unanswerable cases (kafka-020, kafka-021) are not scored on retrieval; they need an answer-level judge."]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description="B1 evaluator (retrieval only)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--off", action="store_true", help="filter OFF only (BEFORE)")
    g.add_argument("--on", action="store_true", help="filter ON only (AFTER)")
    g.add_argument("--table", action="store_true", help="write ablation_summary.md from saved results")
    g.add_argument("--latency", type=int, metavar="N", help="fair OFF/ON latency, N interleaved rounds")
    ap.add_argument("--out", type=Path, default=RESULTS, help="results folder")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    if a.latency:
        lat = latency(a.latency)
        (a.out / "latency.json").write_text(json.dumps(lat, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(lat, indent=2)); print(f"  wrote {a.out / 'latency.json'}")
        return
    if a.table:
        off, on = (json.loads((a.out / FILES[m]).read_text(encoding="utf-8")) for m in ("off", "on"))
        lat_f = a.out / "latency.json"
        lat = json.loads(lat_f.read_text(encoding="utf-8")) if lat_f.exists() else None
        (a.out / "ablation_summary.md").write_text(table(off, on, lat), encoding="utf-8")
        print(table(off, on, lat)); print(f"  wrote {a.out / 'ablation_summary.md'}")
        return
    modes = ["off"] if a.off else ["on"] if a.on else ["off", "on"]
    a.out.mkdir(parents=True, exist_ok=True)
    done = {}
    for m in modes:
        done[m] = run(m)
        show(done[m])
        (a.out / FILES[m]).write_text(json.dumps(done[m], indent=2) + "\n", encoding="utf-8")
        print(f"  wrote {a.out / FILES[m]}")
    if len(done) == 2:
        (a.out / "ablation_summary.md").write_text(table(done["off"], done["on"]), encoding="utf-8")
        print(f"  wrote {a.out / 'ablation_summary.md'}")


if __name__ == "__main__":
    main()
