"""Request classification with a local Hugging Face model — no API call, no key.

Modern AI Pro · Level 2 · AI Practitioner

    python labs/classify.py            # run the golden set, print accuracy
    python labs/classify.py "fix this react bug"

Every request the kit sends is tagged with one of four categories, and the tag
is written into traces.jsonl next to the tokens and latency (see _kit.py).
Observability tells you WHAT it cost; this tells you WHAT IT WAS FOR.

The model — MoritzLaurer/deberta-v3-base-zeroshot-v2.0, ~370MB, downloads once
and is cached in ~/.cache/huggingface — is ZERO-SHOT: it was never trained on
our four categories. It scores how well a sentence entails a hypothesis
("This example is {label}."), so you change the categories by editing a dict,
not by collecting a dataset. That is the whole reason to reach for it.

Note it is a CLASSIFIER, not a generator: 109ms on CPU vs ~1s for an LLM call,
runs offline, and costs nothing per call. Right tool, right job — you don't
need a chat model to answer a four-way question.

Two things worth reading below:

  · the labels the model actually sees are DESCRIPTIONS, not our short names.
    "code generation" alone scored 6/12 on the golden set; "writing, debugging
    or refactoring software code" scores 15/16. The hypothesis is the prompt —
    same lesson as Lab 1, different model family.
  · GOLDEN_SET is a real eval, not a demo. Change a label, rerun this file, see
    the number move. That's Lab 3's discipline applied to a classifier.
"""

from __future__ import annotations

import sys

from _kit import say

# what the model sees  →  what we record
HYPOTHESES = {
    "writing, debugging or refactoring software code": "code generation",
    "sales, pricing, leads, prospecting or customer outreach messaging": "sales",
    "visual design, user interface, layout, typography, fonts or branding": "design",
    "a personal or social topic unrelated to work": "non-work related",
}
CATEGORIES = list(HYPOTHESES.values())
MODEL_ID = "MoritzLaurer/deberta-v3-base-zeroshot-v2.0"

# Below this the top label is a coin-flip dressed up as a decision. We still
# report it — we just mark it, so you can route low-confidence traffic to a
# human, an LLM tie-breaker, or an "unsure" bucket instead of trusting it.
LOW_CONFIDENCE = 0.50

_pipe = None          # loaded on first use — importing torch costs ~2s
_unavailable = False  # transformers missing: degrade, never crash the lab


def _pipeline():
    global _pipe, _unavailable
    if _pipe is not None or _unavailable:
        return _pipe
    try:
        say(f"[dim](loading classifier {MODEL_ID} — first run downloads ~370MB)[/dim]")
        from transformers import pipeline  # noqa: PLC0415 — deliberately lazy
        _pipe = pipeline("zero-shot-classification", model=MODEL_ID)
    except Exception as e:  # noqa: BLE001 — no transformers, no disk, no network
        _unavailable = True
        say(f"[dim](classifier unavailable — {type(e).__name__}; "
            f"pip install transformers torch to enable)[/dim]")
    return _pipe


def classify(text: str) -> dict | None:
    """Tag one request. Returns {category, score, low_confidence} or None if the
    model can't run — callers treat None as 'not classified', never as an error."""
    text = (text or "").strip()
    if not text:
        return None
    pipe = _pipeline()
    if pipe is None:
        return None
    try:
        r = pipe(text[:1000], list(HYPOTHESES))   # long inputs add latency, not accuracy
        top, score = r["labels"][0], float(r["scores"][0])
        return {"category": HYPOTHESES[top],
                "score": round(score, 3),
                "low_confidence": score < LOW_CONFIDENCE}
    except Exception:  # noqa: BLE001 — classification must never break the call it tags
        return None


# ── the golden set — 16 labelled requests, four per category ─────────────────
# Known miss: "write a cold outreach sequence for CFOs" lands on code generation
# at ~0.59. Left in ON PURPOSE. Deleting the case you fail is how eval sets
# start lying to you, and its low score is exactly what LOW_CONFIDENCE catches.

GOLDEN_SET = [
    ("fix this bug in my react component", "code generation"),
    ("refactor this function to be async", "code generation"),
    ("write me a python script to parse csv", "code generation"),
    ("add a unit test for the login handler", "code generation"),
    ("how do I price our enterprise tier", "sales"),
    ("write a cold outreach sequence for CFOs", "sales"),
    ("draft a follow-up to a prospect who went quiet", "sales"),
    ("build me a pipeline for qualifying leads", "sales"),
    ("what font pairs well with Inter", "design"),
    ("make the button spacing feel less cramped", "design"),
    ("mock up a dashboard layout", "design"),
    ("pick a color palette for our landing page", "design"),
    ("tell me a joke", "non-work related"),
    ("what should I cook for dinner", "non-work related"),
    ("who won the world cup", "non-work related"),
    ("plan my weekend trip to Goa", "non-work related"),
]


def evaluate() -> None:
    say(f"[bold]Golden set[/bold] · {len(GOLDEN_SET)} requests · model {MODEL_ID}\n")
    hits = 0
    for text, expected in GOLDEN_SET:
        got = classify(text)
        if got is None:
            say("[red]classifier unavailable — nothing to score.[/red]")
            return
        ok = got["category"] == expected
        hits += ok
        flag = " [yellow]low-confidence[/yellow]" if got["low_confidence"] else ""
        say(f"  {'[green]✓[/green]' if ok else '[red]✗[/red]'} "
            f"{got['category']:<17} {got['score']:.2f}{flag}  [dim]← {text}[/dim]"
            + ("" if ok else f"   [red]expected {expected}[/red]"))
    say(f"\n[bold]{hits}/{len(GOLDEN_SET)}[/bold] correct "
        f"({hits / len(GOLDEN_SET):.0%}) — rerun after editing HYPOTHESES.")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
        got = classify(text)
        say(f"\n  {text}\n  → [bold]{got['category']}[/bold] ({got['score']:.2f})"
            f"{' [yellow]· low confidence[/yellow]' if got['low_confidence'] else ''}\n"
            if got else "\n  [red]classifier unavailable.[/red]\n")
    else:
        evaluate()
