"""A ReAct agent in ~60 lines of real code, printing every step.

Modern AI Pro · Level 2 · AI Practitioner · the simple companion to labs/lab_4.py

    python simple_rag/agent.py ask "how much does the Aventro Storm cost?"
    python simple_rag/agent.py ask "..." --show-messages   # what the model saw
    python simple_rag/agent.py chat                        # history carried
    python simple_rag/agent.py tools                       # the catalogue

An agent is three things a chatbot is not: TOOLS it may call, a LOOP that feeds
results back, and a STOP decision. That is `run()` at the bottom — thought,
action, observation, repeat. Everything printed is the same loop narrating
itself; delete every say() and the agent still works.

  ┌──────────────────────────────────────────────────────────────┐
  │  ADDING A TOOL: write a function, put @tool over it. Done.    │
  │  The decorator registers it, builds the JSON schema from your  │
  │  kwargs, and the docstring becomes the description the model   │
  │  reads. Three examples below — copy the shape.                 │
  └──────────────────────────────────────────────────────────────┘

Needs an ingested corpus:  python simple_rag/rag.py ingest
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))                    # rag.py, observe.py
sys.path.insert(1, str(HERE.parent / "labs"))    # _kit.py — the class LLM client

import observe  # noqa: E402
from observe import event, say, stage, table  # noqa: E402
from rag import collection, retrieve  # noqa: E402

from _kit import MODEL, banner, client, meter  # noqa: E402


# ══ the tool registry ════════════════════════════════════════════════════════
# One decorator, three dicts. FN runs it, SPEC is what the model sees, RISK is
# what YOUR code enforces. The risk tag is deliberately not in the prompt: a rule
# the model can read is a rule it can be talked out of.

FN: dict[str, callable] = {}
SPEC: list[dict] = []
RISK: dict[str, str] = {}


def tool(risk: str = "read", **params: str):
    """Register a function as a tool. `risk="destructive"` routes it via a human.

    params maps argument name → description, e.g. query="what to search for".
    Every argument is a required string — deliberately the only shape supported,
    because 90% of tools need nothing more and the other 10% can take JSON.
    """
    def wrap(fn):
        FN[fn.__name__] = fn
        RISK[fn.__name__] = risk
        SPEC.append({"type": "function", "function": {
            "name": fn.__name__,
            "description": " ".join((fn.__doc__ or "").split()),
            "parameters": {
                "type": "object",
                "properties": {k: {"type": "string", "description": v}
                               for k, v in params.items()},
                "required": list(params)}}})
        return fn
    return wrap


# ── your tools go here ───────────────────────────────────────────────────────
# The docstring IS the prompt — it is the only thing the model knows about a
# tool when it chooses one. Vague docstring → wrong tool → no error anywhere.

@tool(risk="read", query="what to look up in the owner documentation")
def search_manual(query: str) -> str:
    """Search Aventro Motors owner docs — models, prices, features, service
    centres, warranty, how-tos. Returns numbered excerpts to cite as [1][2]."""
    observe.set_quiet(True)          # still traced, just not dumped mid-step
    try:
        hits = retrieve(query, k=K)
    finally:
        observe.set_quiet(False)
    if hits:
        say("      " + " · ".join(f"[dim]{h['similarity']:.2f}[/dim] {h['doc'][:28]}"
                                  for h in hits))
    return "\n\n".join(f"[{h['rank']}] ({h['doc']})\n{h['text']}" for h in hits) or "no results"


@tool(risk="read", expression="arithmetic only, e.g. 2228000 * 1.12")
def calc(expression: str) -> str:
    """Evaluate an arithmetic expression. Use this for every sum — never do the
    arithmetic yourself."""
    if not all(c in "0123456789.+-*/() " for c in expression):
        return "error: only arithmetic characters allowed"
    try:
        return str(eval(expression, {"__builtins__": {}}, {}))  # charset-fenced above
    except Exception as e:  # noqa: BLE001 — a bad expression is feedback, not a crash
        return f"error: {e}"


@tool(risk="destructive", centre="service centre name", date="requested date")
def book_service(centre: str, date: str) -> str:
    """Book a service appointment at a named Aventro centre. THIS ACTS — only
    call it when the customer explicitly asks to book."""
    BOOKINGS.append({"ref": f"AV-{len(BOOKINGS) + 1:03}", "centre": centre, "date": date})
    return f"booked {BOOKINGS[-1]['ref']} at {centre} on {date}"


BOOKINGS: list[dict] = []
K = 4        # chunks per search; set by the CLI

SYSTEM = (
    "You are the Aventro Motors service agent. Ground every claim about a car in "
    "search_manual results and cite them like [1][2]; if the manual does not cover "
    "it, say so instead of using general knowledge about cars. Use calc for "
    "arithmetic. Be concise."
)


# ══ the human checkpoint ═════════════════════════════════════════════════════

def approve(name: str, args: dict) -> bool:
    """Fail closed: with nobody at the keyboard, a destructive call is DENIED."""
    if not sys.stdin.isatty():
        say("      [dim](no human present → denied)[/dim]")
        return False
    return input(f"      ✋ allow {name}({json.dumps(args)[:70]})? [y/N] > "
                 ).strip().lower().startswith("y")


# ══ the ReAct loop ═══════════════════════════════════════════════════════════
# Strip the printing and it is exactly this:
#
#     while True:
#         msg = model(messages, tools)            # THOUGHT
#         if not msg.tool_calls: return msg       # STOP
#         for call in msg.tool_calls:             # ACTION
#             messages.append(run(call))          # OBSERVATION
#
# The budget and the risk gate are the two guards that loop needs to be shippable.

def run(cli, question: str, *, budget: int = 6, history: list | None = None,
        yes: bool = False, dump: bool = False) -> dict:
    messages = ([{"role": "system", "content": SYSTEM}] + (history or [])
                + [{"role": "user", "content": question}])
    ledger, step, calls, stopped, answer = [], 0, 0, "answered", ""
    say(f"\n  [bold]you ›[/bold] {question}")

    with stage("agent_run", question=question, budget=budget) as obs:
        while calls < budget:
            # ── THOUGHT ─────────────────────────────────────────────────────
            step += 1
            say(f"\n  [bold yellow]step {step} · THOUGHT[/bold yellow]  "
                f"[dim]{len(messages)} messages · {len(SPEC)} tools offered[/dim]")
            if dump:
                # The most useful print in agent work: what the model SAW. Most
                # "it ignored my instruction" bugs are "the instruction was never
                # in the list" bugs, and only this print tells them apart.
                for i, m in enumerate(messages):
                    body = " ".join((m.get("content") or "").split()) or "→ " + ", ".join(
                        f"{t['function']['name']}({t['function']['arguments']})"
                        for t in m.get("tool_calls", []))
                    say(f"      [dim]{i:>2} {m['role']:<9} {body[:100]}[/dim]")

            t0 = time.perf_counter()
            resp = ask_model(cli, messages)
            ms = round((time.perf_counter() - t0) * 1000)
            meter.add(resp.usage, "agent")
            calls += 1
            msg = resp.choices[0].message
            say(f"      [dim]{ms} ms · {resp.usage.prompt_tokens} tok sent · "
                f"{resp.usage.completion_tokens} back · call {calls}/{budget}[/dim]")
            if (msg.content or "").strip():
                say(f"      [dim]says:[/dim] {msg.content.strip()[:250]}")

            entry = {"role": "assistant", "content": msg.content or ""}
            if msg.tool_calls:
                entry["tool_calls"] = [{"id": t.id, "type": "function", "function": {
                    "name": t.function.name, "arguments": t.function.arguments}}
                    for t in msg.tool_calls]
            messages.append(entry)
            ledger.append({"step": step, "kind": "thought", "ms": ms,
                           "what": (", ".join(t.function.name for t in msg.tool_calls)
                                    if msg.tool_calls else "final answer"),
                           "tokens": resp.usage.total_tokens})
            event("agent_step", step=step, phase="thought", ms=ms,
                  tools=[t.function.name for t in (msg.tool_calls or [])])

            # ── STOP ────────────────────────────────────────────────────────
            if not msg.tool_calls:
                answer = (msg.content or "").strip()
                say("      [dim]no tool calls → the loop is done[/dim]")
                break

            # ── ACTION → OBSERVATION ────────────────────────────────────────
            for t in msg.tool_calls:
                step += 1
                name = t.function.name
                args = json.loads(t.function.arguments or "{}")
                risk = RISK.get(name, "unknown")
                say(f"\n  [bold cyan]step {step} · ACTION[/bold cyan]  "
                    f"[dim]{name}({json.dumps(args)[:90]}) · risk={risk}[/dim]")

                if risk != "read" and not (yes or approve(name, args)):
                    messages.append({"role": "tool", "tool_call_id": t.id,
                                     "content": "DENIED by a human. Do not retry — "
                                                "tell the customer to do it manually."})
                    say("      [red]✋ denied at the checkpoint[/red]")
                    ledger.append({"step": step, "kind": "action", "ms": 0,
                                   "what": f"{name} DENIED", "tokens": 0})
                    stopped = "denied"
                    continue

                t0 = time.perf_counter()
                result = FN[name](**args) if name in FN else f"error: unknown tool {name}"
                ms = round((time.perf_counter() - t0) * 1000)
                say(f"      [dim]{ms} ms → {len(result)} chars back into context:[/dim] "
                    f"{result[:110].strip()}…")
                messages.append({"role": "tool", "tool_call_id": t.id, "content": result})
                ledger.append({"step": step, "kind": "observation", "ms": ms,
                               "what": name, "tokens": 0})
                event("agent_step", step=step, phase="action", tool=name, risk=risk,
                      ms=ms, chars=len(result))
        else:
            # the budget ran out — stop at a THOUGHT boundary, never mid-tool,
            # and say so. An agent that fails loudly costs one question; one that
            # loops quietly costs a bill.
            answer = ("I hit my step budget before finishing — a human should "
                      "take this one.")
            stopped = "budget"
            say(f"\n  [bold red]⛔ budget of {budget} model call(s) spent[/bold red]")

        say(f"\n  [bold green]agent ›[/bold green] [green]{answer}[/green]\n")
        table("the step ledger", ["step", "kind", "what", "ms", "tokens"],
              [(r["step"], r["kind"], r["what"], r["ms"], r["tokens"] or "—")
               for r in ledger])
        obs.update(steps=step, model_calls=calls, stopped=stopped)
        say(f"\n    [dim]{step} steps · {calls} model call(s) · stopped: "
            f"[bold]{stopped}[/bold] · steps are what you WATCH, model calls are "
            f"what you PAY for[/dim]")
    return {"answer": answer, "ledger": ledger, "stopped": stopped}


def ask_model(cli, messages: list[dict], max_tokens: int = 900):
    """One model call. Rides out a burst-limit 429 once — the class lane is shared."""
    for attempt in (1, 2):
        try:
            return cli.chat.completions.create(model=MODEL, messages=messages,
                                               tools=SPEC, max_tokens=max_tokens)
        except Exception as e:  # noqa: BLE001
            if attempt == 1 and "429" in str(e):
                say("      [dim](burst limit — waiting 25s)[/dim]")
                time.sleep(25)
                continue
            raise


# ══ commands ═════════════════════════════════════════════════════════════════

def cmd_ask(a) -> None:
    globals()["K"] = a.k
    require_corpus()
    run(client(), " ".join(a.question), budget=a.budget, yes=a.yes,
        dump=a.show_messages)
    meter.show()


def cmd_chat(a) -> None:
    """Same loop, history carried. Only user/assistant turns are kept — tool
    calls were scaffolding for one answer; resending them forever grows context
    without bound and lets a stale retrieval ground a later reply."""
    globals()["K"] = a.k
    require_corpus()
    cli = client()
    banner("Level 2 · AI Practitioner", "Aventro agent · every step printed")
    say("[dim]blank line quits · /bookings · /cost[/dim]")
    history: list[dict] = []
    while True:
        try:
            q = input("\nyou > ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not q:
            break
        if q == "/bookings":
            say(f"  {BOOKINGS or 'none yet'}")
            continue
        if q == "/cost":
            meter.show()
            continue
        out = run(cli, q, budget=a.budget, history=history, yes=a.yes)
        history += [{"role": "user", "content": q},
                    {"role": "assistant", "content": out["answer"]}]
    meter.show()


def cmd_tools(a) -> None:
    table("the catalogue, exactly as the model receives it",
          ["tool", "risk", "arguments", "description"],
          [(s["function"]["name"], RISK[s["function"]["name"]],
            ", ".join(s["function"]["parameters"]["properties"]),
            s["function"]["description"][:60] + "…") for s in SPEC])
    say(f"\n  [dim]{collection().count()} chunks behind search_manual. The "
        f"description is the prompt — reword one badly and the agent picks the "
        f"wrong tool, with no error anywhere.[/dim]")


def require_corpus() -> None:
    if collection().count() == 0:
        say("[red]The collection is empty.[/red] Run: "
            "[bold]python simple_rag/rag.py ingest[/bold]")
        sys.exit(1)
    # Load the embedding model BEFORE the loop starts. Otherwise the first
    # search_manual step wears a ~13s one-time model load as its own latency,
    # and the ledger — the thing you're teaching people to read — lies about
    # which step is slow. Warm before the clock starts; same rule as rag.py.
    observe.set_quiet(True)
    try:
        from rag import embedder
        embedder()
    finally:
        observe.set_quiet(False)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    q = sub.add_parser("ask", help="one question, every step printed")
    q.add_argument("question", nargs="+")
    q.add_argument("-k", type=int, default=4, help="chunks per search")
    q.add_argument("--budget", type=int, default=6, help="max model calls")
    q.add_argument("--show-messages", action="store_true",
                   help="dump the message list the model sees each step")
    q.add_argument("--yes", action="store_true",
                   help="auto-approve destructive tools (demo only)")
    q.set_defaults(func=cmd_ask)

    c = sub.add_parser("chat", help="interactive, history carried between turns")
    c.add_argument("-k", type=int, default=4)
    c.add_argument("--budget", type=int, default=6)
    c.add_argument("--yes", action="store_true")
    c.set_defaults(func=cmd_chat)

    t = sub.add_parser("tools", help="print the catalogue the model receives")
    t.set_defaults(func=cmd_tools)

    args = p.parse_args()
    args.func(args)
