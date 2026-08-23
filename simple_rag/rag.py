"""A small, honest RAG system over the Aventro Motors corpus — one file, five stages.

Modern AI Pro · Level 2 · AI Practitioner · companion to labs/lab_3.py

    python simple_rag/fetch_corpus.py         # once — pulls 50 .md + 50 .pdf
    python simple_rag/rag.py ingest           # load → chunk → embed → store
    python simple_rag/rag.py ask "How do I change a tyre on an Aventro?"
    python simple_rag/rag.py ask              # interactive
    python simple_rag/rag.py inspect          # read back the stage traces

What's different from lab_3.py, and why:

    lab_3.py          this file
    ────────────────  ─────────────────────────────────────────────────────
    lists in RAM      Chroma, on disk — ingest once, query forever
    hosted embeddings all-MiniLM-L6-v2 running locally — free, offline, 22M params
    .md only          .md AND .pdf, with the extraction gap measured, not assumed
    the meter         a trace record per stage AND per item (see observe.py)

Every stage prints what it observed and appends JSON to rag_traces.jsonl. That is
the point of the file as much as the retrieval is: when an answer comes back
wrong, the trace tells you WHICH stage lost the fact.
"""

from __future__ import annotations

import argparse
import re
import statistics
import sys
import time
from pathlib import Path

from observe import RUN_ID, TRACE_FILE, event, histogram, kv, say, spread, stage, table

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "labs"))          # reuse the class kit's LLM client
CORPUS = ROOT / "corpus" / "aventro"
CHROMA_DIR = Path(__file__).resolve().parent / ".chroma"
COLLECTION = "aventro"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"   # 384-dim, ~90MB, Apache-2.0


# ══ Stage 1 · LOAD ═══════════════════════════════════════════════════════════
# Getting bytes off disk and into text is where corpora quietly break: a scanned
# PDF extracts to nothing, a decorative one extracts to ligature soup. Neither
# raises. So we measure every file and let the numbers say which format to trust.

def read_md(path: Path) -> tuple[str, dict]:
    return path.read_text(encoding="utf-8", errors="replace"), {}


def read_pdf(path: Path) -> tuple[str, dict]:
    from pypdf import PdfReader   # lazy: importing pypdf costs ~200ms
    reader = PdfReader(str(path))
    pages = [(p.extract_text() or "") for p in reader.pages]
    return "\n\n".join(pages), {"pages": len(pages),
                                "empty_pages": sum(1 for p in pages if not p.strip())}


READERS = {".md": read_md, ".pdf": read_pdf}


def load(formats: list[str], dedupe: bool) -> list[dict]:
    """Read every file in every requested format. Returns docs, newest decision last.

    dedupe=True means: this corpus publishes the SAME 50 titles as both .md and
    .pdf. Indexing both would double every chunk and let a lossy PDF extraction
    outrank its own clean markdown twin. So we parse both — the measurement is
    the lesson — and index one."""
    with stage("load", formats=formats, dedupe=dedupe) as obs:
        docs: list[dict] = []
        for fmt in formats:
            folder = CORPUS / fmt
            if not folder.exists():
                say(f"  [red]missing {folder}[/red] — run simple_rag/fetch_corpus.py")
                sys.exit(1)
            for path in sorted(folder.glob(f"*.{fmt}")):
                t0 = time.perf_counter()
                try:
                    text, extra = READERS[f".{fmt}"](path)
                    err = None
                except Exception as e:  # noqa: BLE001 — one bad file ≠ dead pipeline
                    text, extra, err = "", {}, f"{type(e).__name__}: {e}"
                ms = round((time.perf_counter() - t0) * 1000, 1)
                doc = {"stem": path.stem, "fmt": fmt, "path": str(path.relative_to(ROOT)),
                       "text": text, "chars": len(text), "words": len(text.split()),
                       "bytes": path.stat().st_size, "ms": ms, "error": err,
                       "indexed": True, **extra}
                docs.append(doc)
                event("load", **{k: v for k, v in doc.items() if k != "text"})

        # dedupe by title, preferring the format that extracted MORE text
        if dedupe:
            best: dict[str, dict] = {}
            for d in docs:
                keep = best.get(d["stem"])
                if keep is None or d["chars"] > keep["chars"]:
                    best[d["stem"]] = d
            for d in docs:
                if d is not best.get(d["stem"]):
                    d["indexed"] = False
                    d["skip_reason"] = f"duplicate title — {best[d['stem']]['fmt']} kept"

        # ── what we observed ──
        for fmt in formats:
            group = [d for d in docs if d["fmt"] == fmt]
            if not group:
                continue
            chars = [d["chars"] for d in group]
            say(f"  [bold]{fmt}[/bold] · {len(group)} files")
            obs[f"{fmt}_files"] = len(group)
            obs[f"{fmt}_chars"] = spread(chars, "chars extracted")
            obs[f"{fmt}_parse_ms"] = round(sum(d["ms"] for d in group), 1)
            kv("parse time", f"{obs[f'{fmt}_parse_ms']} ms",
               f"{round(obs[f'{fmt}_parse_ms'] / len(group), 1)} ms/file")
            # yield = extracted characters per KB on disk. It is the single number
            # that catches a scanned or image-only PDF before it poisons the index.
            yield_ = round(sum(chars) / (sum(d["bytes"] for d in group) / 1024), 1)
            kv("extraction yield", f"{yield_} chars/KB")
            obs[f"{fmt}_yield"] = yield_
            dead = [d["path"] for d in group if d["chars"] < 200]
            if dead:
                say(f"    [red]⚠ {len(dead)} file(s) extracted <200 chars[/red] — "
                    f"{dead[0]} … these would be invisible to search")
            obs[f"{fmt}_suspect"] = len(dead)

        # md vs pdf, same title, side by side — extraction loss made concrete
        pairs = {}
        for d in docs:
            pairs.setdefault(d["stem"], {})[d["fmt"]] = d
        both = [p for p in pairs.values() if len(p) > 1]
        if both:
            deltas = [(p["md"]["chars"] - p["pdf"]["chars"]) / max(p["md"]["chars"], 1)
                      for p in both]
            obs["md_vs_pdf_loss"] = round(statistics.mean(deltas), 3)
            say(f"\n  [bold]same title, both formats[/bold] · {len(both)} pairs")
            kv("text lost by the PDF", f"{obs['md_vs_pdf_loss']:+.1%}",
               "share of the markdown's characters missing from its PDF twin")
            worst = max(both, key=lambda p: abs(p["md"]["chars"] - p["pdf"]["chars"]))
            kv("widest gap", worst["md"]["stem"],
               f"md {worst['md']['chars']} chars vs pdf {worst['pdf']['chars']}")

        kept = [d for d in docs if d["indexed"]]
        obs["docs_loaded"], obs["docs_indexed"] = len(docs), len(kept)
        won = {f: sum(1 for d in kept if d["fmt"] == f) for f in formats}
        obs["indexed_by_format"] = won
        say(f"\n  [green]{len(kept)}[/green] of {len(docs)} parsed docs go forward "
            f"({len(docs) - len(kept)} dropped as duplicate titles) — "
            + " · ".join(f"{n} from {f}" for f, n in won.items() if n))
        return kept


# ══ Stage 2 · CHUNK ══════════════════════════════════════════════════════════
# Chunking is a retrieval decision wearing a text-processing costume. Too big and
# the answer hides inside noise; too small and a two-sentence fact gets cut in
# half — retrievable neither way. So: measure the distribution, not the average.

def chunk(text: str, doc: str, target_words: int = 180, overlap: int = 1) -> list[dict]:
    """Paragraph-packing with a heading carried into every chunk.

    Two deliberate choices, both visible in the output:
      · the doc title + nearest markdown heading are PREPENDED to the chunk text,
        so an orphan paragraph still embeds as being about the Aventro Storm SUV.
      · the last `overlap` paragraph(s) repeat at the head of the next chunk, so
        a fact straddling a boundary survives in at least one whole chunk.
    """
    blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
    out: list[dict] = []
    buf: list[str] = []
    heading = ""
    n = 0

    def flush():
        if not buf:
            return
        header = f"{doc}" + (f" — {heading}" if heading else "")
        body = "\n\n".join(buf)
        out.append({"text": f"{header}\n\n{body}", "heading": heading,
                    "words": len(body.split())})

    for b in blocks:
        if b.lstrip().startswith("#"):
            heading = b.lstrip("#").strip().splitlines()[0]
        w = len(b.split())
        if n + w > target_words and buf:
            flush()
            buf = buf[-overlap:] if overlap else []
            n = sum(len(p.split()) for p in buf)
        buf.append(b)
        n += w
    flush()
    return out


def chunk_all(docs: list[dict], target_words: int, overlap: int) -> list[dict]:
    with stage("chunk", target_words=target_words, overlap_paras=overlap) as obs:
        chunks: list[dict] = []
        for d in docs:
            pieces = chunk(d["text"], d["stem"], target_words, overlap)
            for i, p in enumerate(pieces):
                chunks.append({"id": f"{d['fmt']}:{d['stem']}#{i}", "doc": d["stem"],
                               "fmt": d["fmt"], "path": d["path"], "seq": i, **p})
            event("chunk", doc=d["stem"], fmt=d["fmt"], chunks=len(pieces),
                  doc_words=d["words"],
                  words=[p["words"] for p in pieces],
                  headings=sorted({p["heading"] for p in pieces if p["heading"]}))

        words = [c["words"] for c in chunks]
        per_doc = [sum(1 for c in chunks if c["doc"] == d["stem"]) for d in docs]
        obs["chunks"] = len(chunks)
        kv("chunks produced", len(chunks), f"from {len(docs)} docs")
        obs["words"] = spread(words, "words per chunk")
        obs["per_doc"] = spread(per_doc, "chunks per doc")
        histogram(words)

        # the two failure modes worth naming out loud
        singles = sum(1 for n in per_doc if n == 1)
        tiny = sum(1 for w in words if w < 30)
        obs["single_chunk_docs"], obs["tiny_chunks"] = singles, tiny
        if singles:
            say(f"    [dim]{singles} doc(s) fit in one chunk — nothing was split, so "
                f"retrieval returns the whole document.[/dim]")
        if tiny:
            say(f"    [yellow]{tiny} chunk(s) under 30 words[/yellow] — usually a "
                f"trailing fragment. Cheap to keep, but they dilute a top-k slot.")
        say(f"    [dim]raise --chunk-words and this histogram shifts right; the "
            f"golden-set score is what tells you whether that helped.[/dim]")
        return chunks


# ══ Stage 3 · EMBED ══════════════════════════════════════════════════════════
# A local, open-source, 22M-parameter model. No API key, no per-token cost, no
# network. The observability that matters here is a degeneracy check: an embedder
# that returns near-identical vectors for everything still "works" — every query
# just returns the same three chunks, forever, and nothing errors.

_model = None


def embedder():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        t0 = time.perf_counter()
        say(f"  [dim]loading {EMBED_MODEL} (first run downloads ~90MB)…[/dim]")
        _model = SentenceTransformer(EMBED_MODEL)
        _model.encode(["warm"], show_progress_bar=False)   # the FIRST encode pays
        event("model_load", model=EMBED_MODEL,             # lazy init (~2s); burn
              ms=round((time.perf_counter() - t0) * 1000))  # it here, not on a metric
    return _model


def embed(texts: list[str], batch: int = 64, label: str = "embed") -> list[list[float]]:
    model = embedder()
    vecs: list[list[float]] = []
    for i in range(0, len(texts), batch):
        part = texts[i:i + batch]
        t0 = time.perf_counter()
        # normalize → cosine similarity becomes a plain dot product, and every
        # vector norm should come back 1.0. That makes the sanity check below free.
        got = model.encode(part, normalize_embeddings=True, show_progress_bar=False)
        ms = round((time.perf_counter() - t0) * 1000)
        vecs.extend(v.tolist() for v in got)
        event("embed_batch", label=label, batch=i // batch, n=len(part), ms=ms,
              per_s=round(len(part) / max(ms / 1000, 1e-6), 1))
    return vecs


def embed_all(chunks: list[dict]) -> list[list[float]]:
    with stage("embed", model=EMBED_MODEL, n=len(chunks)) as obs:
        embedder()   # warm the model FIRST — folding a one-time 20s load into
        t0 = time.perf_counter()   # throughput would libel the embedder
        vecs = embed([c["text"] for c in chunks])
        secs = time.perf_counter() - t0
        obs["dim"] = len(vecs[0])
        kv("model", EMBED_MODEL.split("/")[-1], "local · Apache-2.0 · no API key")
        kv("vectors", f"{len(vecs)} × {len(vecs[0])} dim")
        kv("throughput", f"{round(len(vecs) / secs, 1)} chunks/s",
           f"{round(secs, 1)}s total, CPU")

        norms = [round(sum(x * x for x in v) ** 0.5, 4) for v in vecs[:200]]
        obs["norm_min"], obs["norm_max"] = min(norms), max(norms)
        kv("vector norms", f"{min(norms)}–{max(norms)}", "expected 1.0 — normalized")

        # Degeneracy check: mean cosine between 40 unrelated chunks. Healthy for
        # a single-domain corpus is roughly 0.1–0.45. Near 1.0 means the model
        # collapsed and every query will retrieve the same thing.
        sample = vecs[::max(len(vecs) // 40, 1)][:40]
        sims = [sum(a * b for a, b in zip(sample[i], sample[j]))
                for i in range(len(sample)) for j in range(i + 1, len(sample))]
        obs["mean_pairwise_cos"] = round(statistics.mean(sims), 3)
        verdict = ("[green]healthy spread[/green]" if obs["mean_pairwise_cos"] < 0.6
                   else "[red]⚠ collapsed — vectors are near-identical[/red]")
        kv("mean pairwise cosine", obs["mean_pairwise_cos"], "")
        say(f"    [dim]→[/dim] {verdict} [dim](one corpus, one topic, so some "
            f"similarity is correct; ~1.0 would mean the embedder failed)[/dim]")
        return vecs


# ══ Stage 4 · STORE ══════════════════════════════════════════════════════════
# Chroma is doing one job: keep vectors + metadata on disk and return the nearest
# k. We hand it embeddings we computed ourselves rather than letting it call an
# embedding function internally — same result, but the timing stays measurable.

def collection(reset: bool = False):
    import chromadb
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    if reset:
        try:
            client.delete_collection(COLLECTION)
        except Exception:  # noqa: BLE001 — not existing yet is the normal case
            pass
    return client.get_or_create_collection(
        COLLECTION, metadata={"hnsw:space": "cosine"})


def store(chunks: list[dict], vecs: list[list[float]], reset: bool) -> None:
    with stage("store", backend="chroma", path=str(CHROMA_DIR)) as obs:
        col = collection(reset=reset)
        for i in range(0, len(chunks), 256):        # Chroma caps batch size
            part = chunks[i:i + 256]
            t0 = time.perf_counter()
            col.add(ids=[c["id"] for c in part],
                    embeddings=vecs[i:i + 256],
                    documents=[c["text"] for c in part],
                    metadatas=[{"doc": c["doc"], "fmt": c["fmt"], "path": c["path"],
                                "heading": c["heading"], "seq": c["seq"],
                                "words": c["words"]} for c in part])
            event("store_batch", n=len(part),
                  ms=round((time.perf_counter() - t0) * 1000))
        obs["count"] = col.count()
        kv("collection", COLLECTION, f"cosine space · {CHROMA_DIR.name}/ on disk")
        kv("vectors stored", obs["count"])
        size = sum(f.stat().st_size for f in CHROMA_DIR.rglob("*") if f.is_file())
        obs["bytes_on_disk"] = size
        kv("on disk", f"{size / 1e6:.1f} MB")


# ══ Stage 5 · RETRIEVE + ANSWER ══════════════════════════════════════════════
# Retrieval is traced separately from generation on purpose. When an answer is
# wrong there are exactly two suspects, and the distances below tell you which:
# the right chunk never arrived (retrieval), or it arrived and was ignored
# (generation). Guessing between those two is how RAG debugging goes bad.

SYSTEM = (
    "You answer questions about Aventro Motors cars using ONLY the numbered "
    "sources below. Cite the sources you used like [1][2] after each claim. "
    "If the sources do not contain the answer, say exactly that — do not use "
    "general knowledge about cars.\n\n"
)


def retrieve(query: str, k: int = 4) -> list[dict]:
    embedder()   # warm before the clock starts, same reason as embed_all()
    with stage("retrieve", query=query, k=k) as obs:
        t0 = time.perf_counter()
        qv = embed([query], label="query")[0]
        embed_ms = round((time.perf_counter() - t0) * 1000)

        t1 = time.perf_counter()
        res = collection().query(query_embeddings=[qv], n_results=k,
                                 include=["documents", "metadatas", "distances"])
        search_ms = round((time.perf_counter() - t1) * 1000)

        hits = [{"rank": i + 1, "text": d, "distance": round(dist, 4),
                 "similarity": round(1 - dist, 4), **m}
                for i, (d, m, dist) in enumerate(zip(res["documents"][0],
                                                     res["metadatas"][0],
                                                     res["distances"][0]))]
        obs.update(embed_ms=embed_ms, search_ms=search_ms,
                   hits=[{"doc": h["doc"], "seq": h["seq"],
                          "similarity": h["similarity"]} for h in hits])
        kv("query embedding", f"{embed_ms} ms")
        kv("chroma search", f"{search_ms} ms", f"top-{k} of {collection().count()}")
        table("retrieved", ["#", "similarity", "doc", "heading"],
              [(h["rank"], f"{h['similarity']:.3f}", h["doc"],
                (h["heading"] or "—")[:38]) for h in hits])
        # 0.50 is calibrated to THIS corpus + MiniLM: real hits land 0.65+, misses
        # around 0.40. It is a tunable, not a constant — re-measure on your own docs.
        if hits and hits[0]["similarity"] < 0.50:
            say("    [yellow]⚠ best match is weak[/yellow] — the corpus probably "
                "does not cover this. Expect (and want) a refusal.")
        obs["top_similarity"] = hits[0]["similarity"] if hits else None
        return hits


def answer(query: str, k: int = 4) -> str:
    hits = retrieve(query, k=k)
    from _kit import chat, client, meter          # the class LLM proxy + its meter
    with stage("generate", query=query) as obs:
        ctx = "\n\n".join(f"[{h['rank']}] ({h['doc']})\n{h['text']}" for h in hits)
        msgs = [{"role": "system", "content": SYSTEM + ctx},
                {"role": "user", "content": query}]
        t0 = time.perf_counter()
        cap = 800
        before = meter.completion_tokens
        out = chat(client(), msgs, label="simple-rag", max_tokens=cap)
        spent = meter.completion_tokens - before
        # A reasoning model can burn the whole completion budget on hidden thinking
        # and return an empty string — ok:true, no error, no answer. Only the token
        # count gives it away, which is the entire argument for tracing usage.
        if not out.strip() and spent >= cap:
            say(f"  [yellow]⚠ blank answer — the model spent all {spent} completion "
                f"tokens before emitting text. Retrying at {cap * 3}.[/yellow]")
            obs["truncated_retry"] = True
            out = chat(client(), msgs, label="simple-rag-retry", max_tokens=cap * 3)
        # structural parse of the [n] citation markers — not a classifier
        cited = sorted({int(n) for n in re.findall(r"\[(\d+)\]", out) if 0 < int(n) <= k})
        obs.update(ms=round((time.perf_counter() - t0) * 1000),
                   context_chars=len(ctx), answer_chars=len(out),
                   cited=cited, uncited=[h["rank"] for h in hits if h["rank"] not in cited],
                   tokens=meter.total_tokens)
        say()
        say(f"  [bold green]{out}[/bold green]\n")
        kv("sources offered", k)
        kv("sources cited", obs["cited"] or "none",
           "uncited claims are the ones to check by hand")
        kv("context sent", f"{obs['context_chars']} chars")
        say(f"    [dim]the LLM call is also traced to traces.jsonl by labs/_kit.py "
            f"— tokens, latency, the exact messages sent[/dim]")
        return out


# ══ commands ═════════════════════════════════════════════════════════════════

def cmd_ingest(a) -> None:
    say(f"[bold]Aventro RAG · ingest[/bold]  [dim]run {RUN_ID} → {TRACE_FILE}[/dim]")
    docs = load(a.formats.split(","), dedupe=not a.no_dedupe)
    chunks = chunk_all(docs, a.chunk_words, a.overlap)
    vecs = embed_all(chunks)
    store(chunks, vecs, reset=not a.append)
    say("\n[green]Ingest complete.[/green]  "
        "Next: [bold]python simple_rag/rag.py ask \"how do I tow my car?\"[/bold]")
    say(f"[dim]Every stage above is one JSON line in {TRACE_FILE} — "
        f"read it with `python simple_rag/rag.py inspect` or jq.[/dim]")


def cmd_ask(a) -> None:
    if collection().count() == 0:
        say("[red]The collection is empty.[/red] Run: python simple_rag/rag.py ingest")
        sys.exit(1)
    if a.question:
        answer(" ".join(a.question), k=a.k)
        return
    say("[bold]Ask the Aventro corpus.[/bold] [dim]blank line or Ctrl-D to quit[/dim]")
    while True:
        try:
            q = input("\n> ").strip()
        except EOFError:
            break
        if not q:
            break
        answer(q, k=a.k)


def cmd_inspect(a) -> None:
    """Read back rag_traces.jsonl — the smallest possible observability UI."""
    import json
    from collections import defaultdict
    path = Path(a.file)
    if not path.exists():
        say(f"[yellow]No traces at {path}[/yellow] — run ingest first.")
        return
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    # order of first appearance, NOT sorted — run ids are random hex, so sorting
    # them would silently pick the wrong "latest run"
    runs = list(dict.fromkeys(r["run"] for r in rows))
    if not a.all_runs:
        rows = [r for r in rows if r["run"] == runs[-1]]
        say(f"[dim]run {runs[-1]} (of {len(runs)} in the file; --all-runs for every "
            f"one)[/dim]")

    cols = (["run"] if a.all_runs else []) + ["stage", "ms", "ok", "headline"]
    table("stages", cols,
          [tuple(([r["run"]] if a.all_runs else [])
                 + [r["stage"], r.get("ms"), "✓" if r.get("ok") else "[red]✗[/red]",
                    r.get("error") or _headline(r)])
           for r in rows if r.get("type") == "stage"])

    kinds = defaultdict(list)
    for r in rows:
        if r.get("type") == "event":
            kinds[r["kind"]].append(r)
    table("events", ["kind", "n", "total ms"],
          [(k, len(v), round(sum(x.get("ms") or 0 for x in v), 1))
           for k, v in sorted(kinds.items())])
    say(f"\n  [dim]{len(rows)} records · full detail: "
        f"jq 'select(.stage==\"chunk\")' {path}[/dim]")


def _headline(r: dict) -> str:
    for key in ("docs_indexed", "chunks", "dim", "count", "top_similarity", "cited"):
        if key in r:
            return f"{key}={r[key]}"
    return ""


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    i = sub.add_parser("ingest", help="load → chunk → embed → store")
    i.add_argument("--formats", default="md,pdf", help="md, pdf, or md,pdf")
    i.add_argument("--chunk-words", type=int, default=180, help="target chunk size")
    i.add_argument("--overlap", type=int, default=1, help="paragraphs repeated per chunk")
    i.add_argument("--no-dedupe", action="store_true",
                   help="index both formats of the same title (see what breaks)")
    i.add_argument("--append", action="store_true", help="keep the existing collection")
    i.set_defaults(func=cmd_ingest)

    q = sub.add_parser("ask", help="retrieve + answer")
    q.add_argument("question", nargs="*")
    q.add_argument("-k", type=int, default=4, help="chunks to retrieve")
    q.set_defaults(func=cmd_ask)

    n = sub.add_parser("inspect", help="summarize rag_traces.jsonl")
    n.add_argument("--file", default=str(TRACE_FILE))
    n.add_argument("--all-runs", action="store_true")
    n.set_defaults(func=cmd_inspect)

    args = p.parse_args()
    args.func(args)
