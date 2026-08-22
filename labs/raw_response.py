"""What does the API ACTUALLY send back? Print it and look.

Modern AI Pro · Level 2 · AI Practitioner

    python labs/raw_response.py

The natural assumption, once chatbot.py starts remembering your name, is that
the API is doing the remembering — that somewhere in the response there's a
profile, a user record, a memory field.

There isn't. This script prints the raw response object, whole and unedited,
so you can check every key yourself. Two calls, side by side:

  1. a normal chat turn      → text + usage. No user. No memory. Nothing.
  2. our fact-extraction call → the SAME shape. The "profile" is just text
                                in choices[0].message.content, because we
                                asked for JSON in the prompt.

The lesson: memory is 100% our side of the wire. The model is a pure
function — messages in, text out. Everything else is a file we maintain.
"""

from __future__ import annotations

import json

from _kit import MODEL, banner, client, rule, say


def dump(resp) -> dict:
    """The raw response as plain JSON — every field the server actually sent."""
    return json.loads(resp.model_dump_json())


def key_paths(obj, prefix: str = "") -> list[str]:
    """Every key in the response, dotted. Structural walk of a known format —
    the one job regex-ish string matching should never be doing (see below)."""
    out: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            path = f"{prefix}.{k}" if prefix else k
            out.append(path)
            out += key_paths(v, path)
    elif isinstance(obj, list):
        for item in obj:
            out += key_paths(item, f"{prefix}[]")
    return out


def main() -> None:
    banner("Level 2 · AI Practitioner", "What the API really returns")
    cli = client()

    # ── Call 1 · a normal chat turn ──────────────────────────────────────────
    rule("Call 1 · an ordinary chat turn")
    say("[dim]We tell it a fact and ask it to reply. Watch what comes back.[/dim]\n")

    resp = cli.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a friendly, concise assistant."},
            {"role": "user", "content": "Hi, I'm Balaji and I'm vegetarian."},
        ],
        max_tokens=60,
    )
    raw = dump(resp)
    say(json.dumps(raw, indent=2, ensure_ascii=False))

    say("\n[bold]Top-level keys the server sent:[/bold]")
    say("  " + " · ".join(sorted(raw)))
    say("\n[bold]Now search the object for the fields you assumed were there.[/bold]")
    say("[dim]Checking real KEY names, not substrings — 'user' would otherwise\n"
        "'match' usage.latency_checkpoint.user_visible_ttft_ms, which is a\n"
        "stopwatch reading, not you. Sloppy greps are how myths like this start.[/dim]\n")
    for field in ("profile", "memory", "user", "user_id", "history", "name"):
        hits = [p for p in key_paths(raw) if p.split(".")[-1] == field]
        mark = f"[red]{hits[0]}[/red]" if hits else "[green]no such key[/green]"
        say(f"  {field:10} {mark}")

    reply = resp.choices[0].message.content or ""
    say(f"\n[bold]And the one place your fact does show up — the reply text:[/bold]")
    say(f"  [cyan]{reply.strip()}[/cyan]")
    say("[dim]That's the model echoing you inside a string it just generated.\n"
        "Read it back next turn and it's gone — unless you saved it.[/dim]")

    # ── Call 2 · the extraction call ─────────────────────────────────────────
    rule("Call 2 · the fact-extraction call from chatbot.py")
    say("[dim]This is the call that 'produces the profile'. Same endpoint, same\n"
        "response shape — the only difference is what we asked for.[/dim]\n")

    resp2 = cli.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content":
                'Extract durable facts about the user. Return ONLY JSON: '
                '{"facts": {"key": "value"}}'},
            {"role": "user", "content": "Hi, I'm Balaji and I'm vegetarian."},
        ],
        max_tokens=100,
        response_format={"type": "json_object"},
    )
    raw2 = dump(resp2)
    say(json.dumps(raw2, indent=2, ensure_ascii=False))

    say("\n[bold]Same keys as call 1:[/bold]")
    say("  " + " · ".join(sorted(raw2)))
    say(f"  [dim]identical shape: {sorted(raw) == sorted(raw2)}[/dim]")

    say("\n[bold]The 'profile' lives here — and it is a STRING:[/bold]")
    content = resp2.choices[0].message.content
    say(f"  choices[0].message.content = [cyan]{content!r}[/cyan]")
    say(f"  [dim]type: {type(content).__name__} — not a dict, not a record.[/dim]")
    say("\n[dim]We call json.loads() on it ourselves, then WE write it to a file.\n"
        "The server has already forgotten this conversation happened.[/dim]")

    # ── The point ────────────────────────────────────────────────────────────
    rule("The logic")
    say("""
Both calls return the same four things: an id, a model name, a list of
choices containing text, and a usage block. That is the entire contract.

  No user id.  No profile.  No memory.  No history.

The API is [bold]stateless[/bold]. Call it twice with the same messages and it
cannot tell the second call from the first. Everything your chatbot appears
to 'remember' — the transcript in memory.jsonl, the facts in profile.json —
is state YOU keep and YOU resend, every single turn.

That is not a limitation to work around. It is the design: statelessness is
why the API scales, and why memory is an application concern with your own
retention rules, your own deletion story, and your own token bill.
""".strip())


if __name__ == "__main__":
    main()
