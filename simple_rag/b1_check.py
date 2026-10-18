"""B1 data checks for the Kafka versioned corpus. Run before every commit.

    python simple_rag/b1_check.py            # every check whose inputs exist
    python simple_rag/b1_check.py --no-trap  # skip the embedding measurement (fast)
    python simple_rag/b1_check.py --no-trap --chroma   # also inspect the vector store (after ingest)

Checks grow with the project; a check whose file does not exist yet is reported
as "not yet" instead of failing, so this one command works at every step.

    Step 3  corpus     8 subjects x (current, old); no "superseded" banner in any file;
                       the similarity trap — how often the OLD runbook outranks the
                       current one for a plain question, using rag.py's own embedder
    Step 4  manifest   every file has exactly doc/version/effective_date/superseded with
                       the right types; one current file per doc; current is newest;
                       version and date agree with the file's header line; every
                       conflict value is really in its file
    Step 5  golden     >=15 well-formed cases with unique ids; every must_cite is a
                       current file and every must_not_cite a superseded one; every
                       must_not_contain string is in the old file and NOT in the
                       current one; every exact_string value is really in its cited
                       file; questions are paraphrased, not copied from the runbooks
    Step 8  --chroma   reads the stored chunks straight from Chroma: every chunk carries
                       doc_title/version/effective_date/superseded with the right types and
                       the manifest's values, all 16 files are present, and Chroma's own
                       where-filter splits the chunks into 8 current and 8 superseded files

Exit code 0 = every check that ran passed.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CORPUS = HERE / "corpus" / "kafka"
MANIFEST = CORPUS / "manifest.json"
GOLDEN = HERE / "golden_kafka.jsonl"
TYPES = {"superseded", "exact_string", "multi_hop", "unanswerable"}
FIELDS = {"doc": str, "version": int, "effective_date": str, "superseded": bool}

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


# ── Step 4: manifest ─────────────────────────────────────────────────────────

def check_manifest() -> None:
    print("\n[Step 4] manifest  ·", MANIFEST.relative_to(HERE.parent))
    n_before = len(failures)
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    files = m.get("files", {})

    on_disk = {p.name for p in CORPUS.glob("*.md")}
    if set(files) == on_disk:
        ok(f"manifest lists exactly the {len(on_disk)} runbooks on disk")
    else:
        fail(f"manifest/disk mismatch: only in manifest {sorted(set(files) - on_disk)}, "
             f"only on disk {sorted(on_disk - set(files))}")

    valid: dict[str, dict] = {}   # entries that passed the type checks
    for name, meta in files.items():
        if set(meta) != set(FIELDS):
            fail(f"{name}: fields {sorted(meta)} != {sorted(FIELDS)}")
            continue
        bad = False
        for k, t in FIELDS.items():
            # bool is a subclass of int in Python — reject True as a version number
            if not isinstance(meta[k], t) or (t is int and isinstance(meta[k], bool)):
                fail(f"{name}: {k}={meta[k]!r} is not {t.__name__}")
                bad = True
        try:
            dt.date.fromisoformat(meta["effective_date"])
        except (TypeError, ValueError):
            fail(f"{name}: effective_date {meta['effective_date']!r} is not YYYY-MM-DD")
            bad = True
        if bad:
            continue          # later checks compare values; skip what is malformed
        valid[name] = meta
        if name in on_disk:
            h = HEADER.search((CORPUS / name).read_text(encoding="utf-8"))
            if h and (int(h[1]), h[2]) != (meta["version"], meta["effective_date"]):
                fail(f"{name}: header says v{h[1]} {h[2]}, manifest says "
                     f"v{meta['version']} {meta['effective_date']}")
    if len(failures) == n_before:
        ok("every entry has exactly 4 fields with the right types; versions and dates match the files")

    n_before = len(failures)
    by_doc: dict[str, list[tuple[str, dict]]] = {}
    for name, meta in valid.items():
        by_doc.setdefault(meta["doc"], []).append((name, meta))
    for doc, members in by_doc.items():
        current = [(n, x) for n, x in members if x["superseded"] is False]
        if len(current) != 1:
            fail(f"{doc!r}: {len(current)} current files, need exactly 1")
            continue
        cname, cmeta = current[0]
        for n, x in members:
            if n != cname and not (x["version"] < cmeta["version"]
                                   and x["effective_date"] < cmeta["effective_date"]):
                fail(f"{doc!r}: old {n} is not older than current {cname}")
    if len(failures) == n_before:
        n_cur = sum(1 for x in valid.values() if x["superseded"] is False)
        ok(f"{len(by_doc)} docs, each with exactly 1 current file that has the highest "
           f"version and latest date ({n_cur} current, {len(valid) - n_cur} superseded)")

    n_before = len(failures)
    conflicts = m.get("conflicts", {})
    if set(conflicts) != set(by_doc):
        fail(f"conflicts keys {sorted(conflicts)} != docs {sorted(by_doc)}")
    distinct = total = 0
    for doc, rows in conflicts.items():
        members = dict(by_doc.get(doc, []))
        cur = next((n for n, x in members.items() if not x["superseded"]), None)
        old = next((n for n, x in members.items() if x["superseded"]), None)
        if not (cur and old):
            continue
        ctext = (CORPUS / cur).read_text(encoding="utf-8")
        otext = (CORPUS / old).read_text(encoding="utf-8")
        for r in rows:
            total += 1
            if r["old"] not in otext:
                fail(f"{doc}: old value {r['old']!r} ({r['field']}) not found in {old}")
            if r["current"] not in ctext:
                fail(f"{doc}: current value {r['current']!r} ({r['field']}) not found in {cur}")
            distinct += r["old"] not in ctext
    if len(failures) == n_before:
        ok(f"all {total} conflict values found in their files")
        info(f"{distinct}/{total} old values never appear in the current file — "
             "usable as must_not_contain in Step 5")


# ── Step 5: golden set ───────────────────────────────────────────────────────

def _longest_shared_run(a: str, b: str) -> int:
    """Longest run of consecutive words that appears in both texts."""
    aw, bw = re.findall(r"\w+", a.lower()), " ".join(re.findall(r"\w+", b.lower()))
    best = 0
    for i in range(len(aw)):
        for j in range(i + best + 1, len(aw) + 1):
            if " ".join(aw[i:j]) in bw:
                best = j - i
            else:
                break
    return best


def check_golden() -> None:
    print("\n[Step 5] golden set  ·", GOLDEN.relative_to(HERE.parent))
    n_before = len(failures)
    files = json.loads(MANIFEST.read_text(encoding="utf-8"))["files"]
    by_key = {(m["doc"], m["version"]): (n, m) for n, m in files.items()}
    text = {n: (CORPUS / n).read_text(encoding="utf-8") for n in files}

    cases = []
    for i, line in enumerate(GOLDEN.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try:
                cases.append(json.loads(line))
            except json.JSONDecodeError as e:
                fail(f"line {i}: not valid JSON ({e})")
    ids = [c.get("id") for c in cases]
    counts = {t: sum(c.get("type") == t for c in cases) for t in sorted(TYPES)}
    if len(cases) >= 15 and len(set(ids)) == len(ids) and counts["superseded"] and counts["exact_string"]:
        ok(f"{len(cases)} cases, unique ids, " + ", ".join(f"{t} {n}" for t, n in counts.items()))
    else:
        fail(f"need >=15 cases with unique ids incl. superseded and exact_string; got {len(cases)}, {counts}")

    for c in cases:
        cid, e, t = c.get("id"), c.get("expect", {}), c.get("type")
        if t not in TYPES or not c.get("question") or "behavior" not in e:
            fail(f"{cid}: missing type/question/expect.behavior")
            continue
        cited, banned = [], []
        for ref in e.get("must_cite", []):
            hit = by_key.get((ref.get("doc"), ref.get("version")))
            if not hit or hit[1]["superseded"]:
                fail(f"{cid}: must_cite {ref} is not a current file in the manifest")
            else:
                cited.append(hit[0])
        for ref in e.get("must_not_cite", []):
            hit = by_key.get((ref.get("doc"), ref.get("version")))
            if not hit or not hit[1]["superseded"]:
                fail(f"{cid}: must_not_cite {ref} is not a superseded file in the manifest")
            else:
                banned.append(hit[0])

        if t == "unanswerable":
            if e["must_cite"] or e["behavior"] != "refuse":
                fail(f"{cid}: unanswerable cases need no must_cite and behavior 'refuse'")
        elif not cited:
            fail(f"{cid}: answerable case has no must_cite")
        if t in ("superseded", "multi_hop") and not banned:
            fail(f"{cid}: {t} case must name the old version in must_not_cite")
        if t == "multi_hop" and len(cited) < 2:
            fail(f"{cid}: multi_hop needs two documents in must_cite")

        for s_ in e.get("must_not_contain", []):
            if not any(s_ in text[b] for b in banned):
                fail(f"{cid}: must_not_contain {s_!r} is not in any must_not_cite file")
            if any(s_ in text[n] for n in cited):
                fail(f"{cid}: must_not_contain {s_!r} also appears in a current file — "
                     "a correct answer could trip it")
        if t == "exact_string":
            for f_ in e.get("facts", []):
                if not any(f_ in text[n] for n in cited):
                    fail(f"{cid}: exact value {f_!r} is not verbatim in {cited}")

        run = max((_longest_shared_run(c["question"], text[n]) for n in cited), default=0)
        if run >= 7:
            fail(f"{cid}: question copies {run} consecutive words from the runbook — paraphrase it")
    if len(failures) == n_before:
        ok("every must_cite is current, every must_not_cite is superseded")
        ok("every must_not_contain is in the old file only; every exact value is verbatim in its file")
        ok("unanswerable cases cite nothing and expect a refusal; multi_hop cases cite 2 docs")
        ok("no question copies 7+ consecutive words from the runbook it targets")
        covered = {by_key[(r["doc"], r["version"])][0] for c in cases
                   for r in c["expect"].get("must_cite", [])}
        info(f"current runbooks covered by must_cite: {len(covered)}/"
             f"{sum(not m['superseded'] for m in files.values())}")


# ── Step 8: metadata inside Chroma ───────────────────────────────────────────

CHROMA_TYPES = {"doc_title": str, "version": int, "effective_date": str, "superseded": bool}


def check_chroma() -> None:
    os.environ.setdefault("RAG_TRACE", "0")
    sys.path.insert(0, str(HERE))
    import rag  # noqa: E402
    rag.COLLECTION = os.environ.get("RAG_COLLECTION", "kafka")
    print(f"\n[Step 8] Chroma  ·  {rag.CHROMA_DIR.relative_to(HERE.parent)} · collection '{rag.COLLECTION}'")
    n_before = len(failures)
    col = rag.collection()
    got = col.get(include=["metadatas"])
    ids, metas = got["ids"], got["metadatas"]
    if not ids:
        fail("collection is empty — run: RAG_CORPUS=simple_rag/corpus/kafka RAG_COLLECTION=kafka "
             "python simple_rag/rag.py ingest --formats md")
        return
    files = json.loads(MANIFEST.read_text(encoding="utf-8"))["files"]

    print(f"        {'chunk id':<38} {'version':>7}  {'effective':<10}  superseded")
    for cid, m in sorted(zip(ids, metas)):
        print(f"        {cid:<38} {str(m.get('version')):>7}  {str(m.get('effective_date')):<10}  "
              f"{m.get('superseded')}")
        name = Path(m["path"]).name
        missing = [k for k in CHROMA_TYPES if k not in m]
        if missing:
            fail(f"{cid}: no {missing} in Chroma metadata — was it ingested before Step 8?")
            continue
        for k, t in CHROMA_TYPES.items():
            if not isinstance(m[k], t) or (t is int and isinstance(m[k], bool)):
                fail(f"{cid}: {k}={m[k]!r} is {type(m[k]).__name__}, expected {t.__name__}")
        want = files.get(name)
        if want is None:
            fail(f"{cid}: {name} is not in manifest.json")
        elif (m["doc_title"], m["version"], m["effective_date"], m["superseded"]) != \
                (want["doc"], want["version"], want["effective_date"], want["superseded"]):
            fail(f"{cid}: Chroma metadata differs from manifest.json for {name}")
    if len(failures) == n_before:
        ok(f"{len(ids)} chunks, every one carries doc_title, version, effective_date, superseded "
           "with the right types")
        ok("every chunk's values match manifest.json for its file")

    stored = {Path(m["path"]).name for m in metas}
    if stored == set(files):
        ok(f"all {len(files)} runbooks are in the collection")
    else:
        fail(f"files missing from Chroma: {sorted(set(files) - stored)}")

    # The exact condition Step 9 will add to the query, tried here on its own.
    cur = col.get(where={"superseded": False}, include=["metadatas"])
    old = col.get(where={"superseded": True}, include=["metadatas"])
    cur_files = {Path(m["path"]).name for m in cur["metadatas"]}
    old_files = {Path(m["path"]).name for m in old["metadatas"]}
    info(f'where={{"superseded": False}} -> {len(cur["ids"])} chunks from {len(cur_files)} files; '
         f'where={{"superseded": True}} -> {len(old["ids"])} chunks from {len(old_files)} files')
    if (all(not files[f]["superseded"] for f in cur_files) and all(files[f]["superseded"] for f in old_files)
            and len(cur["ids"]) + len(old["ids"]) == len(ids) and len(cur_files) == len(old_files) == 8):
        ok("Chroma's where-filter splits the store cleanly: 8 current files vs 8 superseded files")
    else:
        fail("Chroma's where-filter does not split current and superseded cleanly")


def main() -> int:
    print("B1 data checks · Track B")
    if CORPUS.exists():
        check_corpus()
        if "--no-trap" not in sys.argv:
            check_trap()
    else:
        info("corpus/kafka/ not yet (Step 3)")
    if MANIFEST.exists():
        check_manifest()
    else:
        info("manifest.json — not yet (Step 4)")
    if GOLDEN.exists() and MANIFEST.exists():
        check_golden()
    else:
        info("golden_kafka.jsonl — not yet (Step 5)")
    if "--chroma" in sys.argv:
        check_chroma()
    print(f"\n{'PASS' if not failures else f'FAIL ({len(failures)})'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
