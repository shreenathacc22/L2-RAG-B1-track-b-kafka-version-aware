"""Turn routing with a local zero-shot classifier — no API call, no key.

Modern AI Pro · Level 2 · AI Practitioner

    python simple_rag/route.py                  # run the golden set, print accuracy
    python simple_rag/route.py "what's the storm cost"

Same model and same discipline as labs/classify.py, different question. That file
asks "what was this request FOR?" and writes the answer into a trace. This one
asks something the chatbot has to ACT on:

    does this turn need retrieval?

Which is where a free local classifier earns its keep. "hey" and "thanks" and
"what did I just say" do not need a vector search, a query rewrite, or 4 chunks
of car documentation stuffed into the prompt — but a naive RAG chatbot retrieves
for every one of them, paying twice: once in latency, once in a context window
full of irrelevant policy text that makes the reply worse.

109ms on CPU and $0 decides whether to spend ~1.5s and two LLM calls. That is the
whole argument for keeping a classifier in the loop.

Two things carried over from classify.py because they are the actual lessons:

  · the labels the model sees are DESCRIPTIONS, not our short names. The
    hypothesis IS the prompt.
  · GOLDEN_SET is a real eval. Edit a hypothesis, rerun this file, watch the
    number move — before you ship the edit.
"""

from __future__ import annotations

import sys

# what the model sees  →  the route we take
HYPOTHESES = {
    "a question about a car model, its price, features, servicing or how to operate it":
        "product_lookup",
    # "not asking a question" earns its words: without it, "what SUVs do you have
    # in that range?" landed here at 0.51 because it mentions a budget range, and
    # a product question skipped retrieval. Ablated against the 20-case set —
    # costly 1 → 0, label 14 → 15. Widening product_lookup scored the same, but
    # fixing the boundary beats stretching the neighbour.
    "the speaker stating a fact about themselves, their budget or their family, "
    "not asking a question":
        "personal_context",
    "a greeting, thanks, or small talk that asks for no information":
        "chitchat",
    "a question about this conversation itself or about what was said earlier":
        "conversation_meta",
}
ROUTES = list(HYPOTHESES.values())
MODEL_ID = "MoritzLaurer/deberta-v3-base-zeroshot-v2.0"   # same model as classify.py,
                                                          # so the HF cache is shared

# Only product_lookup pays for retrieval. Everything else answers from memory.
RETRIEVES = {"product_lookup"}

LOW_CONFIDENCE = 0.50

# Below the threshold we RETRIEVE anyway — but this is only safe because the
# caller cleans up after it. First version of this comment claimed a needless
# retrieval merely "costs a few hundred milliseconds and some tokens". That was
# wrong, and a real conversation proved it: "what do you remember about me?"
# fell back here, pulled four chunks at 0.17 similarity, and the grounding rule
# then made the assistant RETRACT a correct answer it had given two turns
# earlier. Irrelevant context plus "trust only the context" is not a cheap
# failure — it manufactures a confident wrong answer out of a right one.
#
# So the fallback stays (a missed product question is still worse), but see
# assistant.py → WEAK_MATCH: when this fallback fires AND the search comes back
# weak, the sources are dropped before they reach the prompt.
FALLBACK = "product_lookup"

_pipe = None
_unavailable = False


def _pipeline():
    global _pipe, _unavailable
    if _pipe is not None or _unavailable:
        return _pipe
    try:
        from transformers import pipeline  # noqa: PLC0415 — lazy: torch costs ~2s
        _pipe = pipeline("zero-shot-classification", model=MODEL_ID)
    except Exception:  # noqa: BLE001 — no transformers, no disk, no network
        _unavailable = True
    return _pipe


def route(text: str) -> dict:
    """Classify one turn. ALWAYS returns a usable dict — never None.

    classify.py returns None when the model can't run, because a missing trace
    tag is harmless. Here the caller has to make a decision either way, so an
    unavailable classifier degrades to the safe route rather than to nothing."""
    text = (text or "").strip()
    pipe = _pipeline() if text else None
    if pipe is None:
        return {"route": FALLBACK, "score": 0.0, "low_confidence": True,
                "reason": "classifier unavailable — defaulted to retrieving"}
    try:
        r = pipe(text[:1000], list(HYPOTHESES))
        top, score = HYPOTHESES[r["labels"][0]], float(r["scores"][0])
        low = score < LOW_CONFIDENCE
        return {"route": FALLBACK if low else top, "score": round(score, 3),
                "low_confidence": low, "predicted": top,
                "reason": (f"low confidence ({score:.2f}) — defaulted to retrieving"
                           if low else "")}
    except Exception:  # noqa: BLE001 — routing must never break the turn it routes
        return {"route": FALLBACK, "score": 0.0, "low_confidence": True,
                "reason": "classifier error — defaulted to retrieving"}


def retrieves(decision: dict) -> bool:
    return decision["route"] in RETRIEVES


# ── the golden set — 16 labelled turns, four per route ───────────────────────
# Written the way a customer types, not the way a document is worded. Cases that
# fail stay in: deleting the case you fail is how an eval set starts lying.

GOLDEN_SET = [
    ("how much is the storm zx", "product_lookup"),
    ("does the glory have adaptive cruise control", "product_lookup"),
    ("where can I get my car serviced in pune", "product_lookup"),
    ("how do I open the boot when the battery is dead", "product_lookup"),
    ("my budget is around 20 lakh", "personal_context"),
    ("we're a family of five and I drive mostly in the city", "personal_context"),
    ("I'm looking for something in an electric variant", "personal_context"),
    ("call me Bala", "personal_context"),
    ("hey there", "chitchat"),
    ("thanks, that helps", "chitchat"),
    ("good morning", "chitchat"),
    ("ok cool", "chitchat"),
    ("what did I just ask you", "conversation_meta"),
    ("can you repeat that last bit", "conversation_meta"),
    ("what do you remember about me", "conversation_meta"),
    ("what have we talked about so far", "conversation_meta"),

    # Added after real use, not invented up front. Turn 3 of the first live
    # conversation — "what SUVs do you have in that range?" — scored 0.51 as
    # personal_context, skipped retrieval, and the bot answered that it had no
    # access to Aventro's model inventory. A costly miss with no case covering
    # it. These four are that gap: product questions that LEAN on prior context,
    # which is the shape a real second turn actually takes.
    ("what SUVs do you have in that range?", "product_lookup"),
    ("which of those comes in electric?", "product_lookup"),
    ("is that one available with a sunroof", "product_lookup"),
    ("and how much for the diesel version", "product_lookup"),
]


def evaluate() -> None:
    from observe import say
    say(f"[bold]Routing golden set[/bold] · {len(GOLDEN_SET)} turns · {MODEL_ID}\n")
    if _pipeline() is None:
        say("[red]classifier unavailable[/red] — pip install transformers torch")
        return
    hits = costly = wasteful = action_ok = 0
    for text, expected in GOLDEN_SET:
        got = route(text)
        ok = got["route"] == expected
        hits += ok
        # The label is not the decision. Four routes collapse into TWO actions,
        # so score the action too — that is what the chatbot actually does.
        want_retrieval = expected in RETRIEVES
        did_retrieval = retrieves(got)
        action_ok += want_retrieval == did_retrieval
        costly += want_retrieval and not did_retrieval      # invents facts
        wasteful += did_retrieval and not want_retrieval    # burns tokens
        flag = " [yellow]low-conf→retrieve[/yellow]" if got["low_confidence"] else ""
        say(f"  {'[green]✓[/green]' if ok else '[red]✗[/red]'} "
            f"{got['route']:<18} {got['score']:.2f}{flag}  [dim]← {text}[/dim]"
            + ("" if ok else f"   [red]expected {expected}[/red]"
                             + ("" if want_retrieval == did_retrieval
                                else "  [red](wrong action)[/red]")))
    n = len(GOLDEN_SET)
    say(f"\n[bold]label   {hits}/{n}[/bold] ({hits / n:.0%})   "
        f"[dim]did it pick the right one of four routes[/dim]")
    say(f"[bold]action  {action_ok}/{n}[/bold] ({action_ok / n:.0%})   "
        f"[dim]did it retrieve when it should have — the decision that ships[/dim]")
    say(f"\n  [{'green' if not costly else 'red'}]{costly} costly[/]  "
        "[dim]product question routed AWAY from retrieval → answers from imagination[/dim]")
    say(f"  [{'green' if not wasteful else 'yellow'}]{wasteful} wasteful[/]  "
        "[dim]retrieved when it needn't have → a few hundred ms and some tokens[/dim]")
    say("\n[dim]These two never average. A router at 69% labels can still be at "
        "100% on the error that matters — and a router that looks better on labels "
        "can be worse where it counts. Pick the metric your system acts on.[/dim]")


if __name__ == "__main__":
    from observe import say
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
        got = route(text)
        say(f"\n  {text}\n  → [bold]{got['route']}[/bold] ({got['score']:.2f})"
            f"{'  [yellow]· ' + got['reason'] + '[/yellow]' if got['reason'] else ''}"
            f"\n  retrieval: {'[green]yes[/green]' if retrieves(got) else '[dim]skipped[/dim]'}\n")
    else:
        evaluate()
