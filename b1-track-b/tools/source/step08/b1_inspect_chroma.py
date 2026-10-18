"""Look inside the Chroma vector store directly — no rag.py, no LLM.

    python simple_rag/b1_inspect_chroma.py                       # list chunks + demo query
    python simple_rag/b1_inspect_chroma.py "your question here"  # demo with your own question

1. Lists every stored chunk with its B1 metadata (version, effective_date, superseded).
2. Counts chunks per metadata value with Chroma's own get(where=...).
3. Runs ONE question against Chroma twice — plain top-4, then top-4 with
   where={"superseded": False} — so you can see what the Step 9 filter will do,
   using the same embedder and normalisation as rag.py.

Read-only: it never writes to the store.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import chromadb

HERE = Path(__file__).resolve().parent
COLLECTION = os.environ.get("RAG_COLLECTION", "kafka")
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"   # must match rag.EMBED_MODEL
QUESTION = " ".join(sys.argv[1:]) or "Broker 4's data volume just hit 87%. Should that have paged someone?"

col = chromadb.PersistentClient(path=str(HERE / ".chroma")).get_collection(COLLECTION)
got = col.get(include=["metadatas"])
print(f"collection '{COLLECTION}': {col.count()} chunks\n")
print(f"  {'chunk id':<38} {'file':<34} {'ver':>3}  {'effective':<10}  superseded")
for cid, m in sorted(zip(got["ids"], got["metadatas"])):
    print(f"  {cid:<38} {Path(m['path']).name:<34} {str(m.get('version')):>3}  "
          f"{str(m.get('effective_date')):<10}  {m.get('superseded')}")

print()
for value in (False, True):
    n = len(col.get(where={"superseded": value})["ids"])
    print(f'  col.get(where={{"superseded": {value}}})  -> {n} chunks')

from sentence_transformers import SentenceTransformer  # noqa: E402 — slow import, only now

qv = SentenceTransformer(EMBED_MODEL).encode([QUESTION], normalize_embeddings=True)[0].tolist()
print(f'\nquestion: "{QUESTION}"')
for label, where in (("plain top-4 (filter OFF)", None),
                     ('top-4 with where={"superseded": False} (filter ON)', {"superseded": False})):
    r = col.query(query_embeddings=[qv], n_results=4, where=where,
                  include=["metadatas", "distances"])
    print(f"\n  {label}")
    for rank, (m, d) in enumerate(zip(r["metadatas"][0], r["distances"][0]), 1):
        flag = "SUPERSEDED" if m.get("superseded") else "current"
        print(f"    #{rank}  {1 - d:.3f}  {Path(m['path']).name:<34} {flag}")
