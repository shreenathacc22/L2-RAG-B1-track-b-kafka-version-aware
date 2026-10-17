"""B1 data checks for the Kafka versioned corpus. Run before every commit.

    python simple_rag/b1_check.py            # every check whose inputs exist
    python simple_rag/b1_check.py --no-trap  # skip the embedding measurement (fast)

Checks grow with the project; a check whose file does not exist yet is reported
as "not yet" instead of failing, so this one command works at every step.

    Step 3  corpus     8 subjects x (current, old); no "superseded" banner in any file;
                       the similarity trap — how often the OLD runbook outranks the
                       current one for a plain question, using rag.py's own embedder
    Step 4  manifest   (added in Step 4)
    Step 5  golden     (added in Step 5)

Exit code 0 = every check that ran passed.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CORPUS = HERE / "corpus" / "kafka"

OLD_NAME = re.compile(r"^(?P<subject>.+)-(?P<year>20\d\d)\.md$")
HEADER = re.compile(r"^Version (\d+) · Effective (\d{4}-\d{2}-\d{2}) · Owner: .+$", re.M)
# An old runbook must read as if it were live — status lives in metadata only.
BANNER = re.compile(r"\b(superseded|obsolete|deprecated|no longer (valid|current))\b", re.I)

# One plain question per subject, worded like an engineer would ask. These are NOT
# golden cases — they only measure whether the corpus is a realistic trap.
TRAP_QUESTIONS = {
    "consumer-lag-alerting": "At what consumer lag do we page the on-call?",
    "topic-retention": "What is the default retention for a new Kafka topic?",
    "broker-rolling-restart": "How long do I wait between brokers during a rolling restart?",
    "listeners-and-auth": "Which port and protocol do Kafka clients connect on?",
    "topic-creation-standards": "How many partitions should a new topic have?",
    "disk-capacity": "At what disk usage does a Kafka broker page someone?",
    "schema-registry": "What port is the schema registry on?",
    "oncall-escalation": "How quickly must the primary on-call acknowledge a Kafka page?",
}

failures: list[str] = []


def ok(msg: str) -> None:
    print(f"  OK    {msg}")


def fail(msg: str) -> None:
    print(f"  FAIL  {msg}")
    failures.append(msg)


def info(msg: str) -> None:
    print(f"        {msg}")


# ── Step 3: corpus ───────────────────────────────────────────────────────────

def pairs() -> dict[str, tuple[Path, Path]]:
    """subject -> (current file, old file)."""
    out = {}
    for p in sorted(CORPUS.glob("*.md")):
        m = OLD_NAME.match(p.name)
        if m:
            out[m["subject"]] = (CORPUS / f"{m['subject']}.md", p)
    return out


def check_corpus() -> None:
    print("\n[Step 3] corpus  ·", CORPUS.relative_to(HERE.parent))
    files = sorted(CORPUS.glob("*.md"))
    if len(files) == 16:
        ok("16 runbooks")
    else:
        fail(f"expected 16 runbooks, found {len(files)}")

    ps = pairs()
    if len(ps) == 8 and all(c.exists() for c, _ in ps.values()):
        ok("8 subjects, each with a current <subject>.md and an old <subject>-<year>.md")
    else:
        fail(f"pairs incomplete: {sorted(ps)}")

    for p in files:
        text = p.read_text(encoding="utf-8")
        if not HEADER.search(text):
            fail(f"{p.name}: missing 'Version N · Effective YYYY-MM-DD · Owner: ...' line")
        if BANNER.search(text):
            fail(f"{p.name}: contains a status word ({BANNER.search(text)[0]!r}) — "
                 "old runbooks must not announce they are old")
        if text.startswith("---"):
            fail(f"{p.name}: has front-matter — Track B keeps metadata in manifest.json")
    if not failures:
        ok("every file has a Version/Effective header, no status banner, no front-matter")

    for subject, (cur, old) in ps.items():
        vc = int(HEADER.search(cur.read_text(encoding="utf-8"))[1])
        vo = int(HEADER.search(old.read_text(encoding="utf-8"))[1])
        if vc <= vo:
            fail(f"{subject}: current version {vc} is not higher than old {vo}")
    ok("current version number > old version number in every pair")


def check_trap() -> None:
    """Embed every runbook with rag.py's model and see which version wins."""
    print("\n[Step 3] similarity trap  ·  embedder = rag.EMBED_MODEL")
    os.environ.setdefault("RAG_TRACE", "0")
    sys.path.insert(0, str(HERE))
    import rag  # noqa: E402 — same model, same normalisation as ingest

    files = sorted(CORPUS.glob("*.md"))
    vecs = rag.embed([p.read_text(encoding="utf-8") for p in files], label="b1_check")
    by_name = dict(zip((p.name for p in files), vecs))
    dot = lambda a, b: sum(x * y for x, y in zip(a, b))  # vectors are normalised

    sims = []
    for subject, (cur, old) in pairs().items():
        sims.append((subject, dot(by_name[cur.name], by_name[old.name])))
    lo = min(s for _, s in sims)
    info(f"pair similarity (current vs old): min {lo:.3f}  max {max(s for _, s in sims):.3f}")
    if lo >= 0.85:
        ok("every pair is near-duplicate (>= 0.85) — similarity alone cannot tell them apart")
    else:
        fail(f"a pair is too different to be a realistic trap: {min(sims, key=lambda t: t[1])}")

    old_wins = 0
    for subject, q in TRAP_QUESTIONS.items():
        cur, old = pairs()[subject]
        qv = rag.embed([q], label="b1_check_q")[0]
        ranked = sorted(by_name, key=lambda n: -dot(qv, by_name[n]))
        r_cur, r_old = ranked.index(cur.name) + 1, ranked.index(old.name) + 1
        winner = "OLD" if r_old < r_cur else "current"
        old_wins += winner == "OLD"
        info(f"{subject:<26} current #{r_cur:<2} old #{r_old:<2} -> {winner} ranks higher")
    info(f"old version outranks current for {old_wins}/8 plain questions")
    if old_wins:
        ok("the trap is real — the baseline should retrieve superseded chunks")
    else:
        fail("old never outranks current; the BEFORE run may show 0% and prove nothing")


def main() -> int:
    print("B1 data checks · Track B")
    if CORPUS.exists():
        check_corpus()
        if "--no-trap" not in sys.argv:
            check_trap()
    else:
        info("corpus/kafka/ not yet (Step 3)")
    info("manifest.json — not yet (Step 4)")
    info("golden_kafka.jsonl — not yet (Step 5)")
    print(f"\n{'PASS' if not failures else f'FAIL ({len(failures)})'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
