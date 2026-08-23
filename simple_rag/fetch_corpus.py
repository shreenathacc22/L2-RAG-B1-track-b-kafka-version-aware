"""Download the Aventro Motors corpus into corpus/aventro/{md,pdf}.

    python simple_rag/fetch_corpus.py

Source: github.com/udayallu/RAG-Multi-Corpus → datasets/Aventro Motors
50 car-owner documents, published in both .md and .pdf (same 50 titles in each).

Stdlib only, no API key, and idempotent — files already on disk are skipped, so
re-running costs one API listing call per folder.
"""

from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

REPO = "udayallu/RAG-Multi-Corpus"
BASE = "datasets/Aventro Motors"
DEST = Path(__file__).resolve().parent.parent / "corpus" / "aventro"


def listing(folder: str) -> list[dict]:
    """One GitHub contents API call → the files in datasets/Aventro Motors/<folder>."""
    path = urllib.parse.quote(f"{BASE}/{folder}")
    url = f"https://api.github.com/repos/{REPO}/contents/{path}?per_page=100"
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)


def pull(folder: str, suffix: str) -> tuple[int, int]:
    out = DEST / folder
    out.mkdir(parents=True, exist_ok=True)
    got = skipped = 0
    for entry in listing(folder):
        if entry["type"] != "file" or not entry["name"].endswith(suffix):
            continue  # skips .DS_Store and any stray formats
        target = out / entry["name"]
        if target.exists() and target.stat().st_size == entry["size"]:
            skipped += 1
            continue
        with urllib.request.urlopen(entry["download_url"], timeout=60) as r:
            target.write_bytes(r.read())
        got += 1
        print(f"  ↓ {folder}/{entry['name']}")
    return got, skipped


if __name__ == "__main__":
    print(f"Aventro Motors corpus → {DEST}\n")
    try:
        for folder, suffix in (("md", ".md"), ("pdf", ".pdf")):
            got, skipped = pull(folder, suffix)
            print(f"{folder}: {got} downloaded, {skipped} already present")
    except urllib.error.HTTPError as e:  # rate limit is the realistic failure
        print(f"\n✗ GitHub said {e.code} {e.reason}. If it's 403, the anonymous API "
              f"rate limit (60/hr) is spent — wait, or clone the repo by hand.")
        sys.exit(1)
    print("\nNext:  python simple_rag/rag.py ingest")
