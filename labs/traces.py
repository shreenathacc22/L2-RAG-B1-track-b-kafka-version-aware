"""Read the trace file the labs write — the smallest possible observability UI.

Modern AI Pro · Level 2 · AI Practitioner

    python labs/traces.py                     # summary + the last 10 calls
    python labs/traces.py --all               # every call
    python labs/traces.py --errors            # only the failures
    python labs/traces.py --category sales    # only one category
    python labs/traces.py --file x.jsonl

Every LLM call in this kit appends one JSON object to traces.jsonl (see
_kit.py → trace()). It is plain JSON Lines, so this file is a convenience,
not a requirement — `cat traces.jsonl | jq` works just as well.
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

from rich.table import Table

from _kit import console, say


def load(path: Path) -> list[dict]:
    if not path.exists():
        say(f"[yellow]No traces yet at {path}.[/yellow] Run a lab or labs/chatbot.py first.")
        sys.exit(0)
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue          # a half-written last line during `tail -f` — skip it
    return rows


def summarize(rows: list[dict]) -> None:
    by_label = defaultdict(lambda: {"n": 0, "tok": 0, "ms": 0, "err": 0})
    for r in rows:
        s = by_label[r.get("label", "?")]
        s["n"] += 1
        s["tok"] += r.get("total_tokens") or 0
        s["ms"] += r.get("latency_ms") or 0
        s["err"] += 0 if r.get("ok", True) else 1

    t = Table(title="by label", title_justify="left", header_style="bold")
    for col in ("label", "calls", "errors", "tokens", "avg ms"):
        t.add_column(col, justify="right" if col != "label" else "left")
    for label, s in sorted(by_label.items(), key=lambda kv: -kv[1]["tok"]):
        t.add_row(label, str(s["n"]),
                  f"[red]{s['err']}[/red]" if s["err"] else "0",
                  str(s["tok"]), str(round(s["ms"] / max(s["n"], 1))))
    console.print(t)

    by_cat = defaultdict(lambda: {"n": 0, "tok": 0, "unsure": 0})
    for r in rows:
        if not r.get("category"):
            continue
        c = by_cat[r["category"]]
        c["n"] += 1
        c["tok"] += r.get("total_tokens") or 0
        c["unsure"] += 1 if r.get("category_low_confidence") else 0

    if by_cat:
        tagged = sum(c["n"] for c in by_cat.values())
        t = Table(title="by category", title_justify="left", header_style="bold")
        for col in ("category", "calls", "share", "tokens", "low-conf"):
            t.add_column(col, justify="right" if col != "category" else "left")
        for cat, c in sorted(by_cat.items(), key=lambda kv: -kv[1]["n"]):
            t.add_row(cat, str(c["n"]), f"{c['n'] / tagged:.0%}", str(c["tok"]),
                      f"[yellow]{c['unsure']}[/yellow]" if c["unsure"] else "0")
        console.print(t)

    total_tok = sum(r.get("total_tokens") or 0 for r in rows)
    sessions = len({r.get("session") for r in rows})
    errors = sum(1 for r in rows if not r.get("ok", True))
    say(f"\n[bold]{len(rows)}[/bold] calls · [bold]{total_tok}[/bold] tokens · "
        f"{sessions} session(s) · [{'red' if errors else 'green'}]{errors} errors[/]")


def show(rows: list[dict]) -> None:
    for r in rows:
        cat = ""
        if r.get("category"):
            colour = "yellow" if r.get("category_low_confidence") else "magenta"
            cat = f" · [{colour}]{r['category']} {r.get('category_score')}[/{colour}]"
        head = (f"[dim]{r.get('ts')}[/dim] [yellow]{r.get('label')}[/yellow] "
                f"{r.get('latency_ms')}ms · {r.get('total_tokens') or '?'} tok"
                + (" · [cyan]streamed[/cyan]" if r.get("streamed") else "") + cat)
        say(head if r.get("ok", True) else head + f"  [red]{r.get('error')}[/red]")
        last_user = next((m for m in reversed(r.get("messages", []))
                          if m.get("role") == "user"), None)
        if last_user:
            say(f"    [dim]user →[/dim] {last_user['content']}")
        if r.get("output"):
            say(f"    [green]out  →[/green] {r['output']}")
        say()


if __name__ == "__main__":
    args = sys.argv[1:]
    path = Path(args[args.index("--file") + 1]) if "--file" in args else Path("traces.jsonl")
    rows = load(path)

    if "--category" in args:
        want = args[args.index("--category") + 1].lower()
        rows = [r for r in rows if (r.get("category") or "").lower() == want]
        if not rows:
            say(f"[yellow]No calls tagged '{want}'.[/yellow] "
                "Categories: code generation · sales · design · non-work related")
            sys.exit(0)

    if "--errors" in args:
        rows = [r for r in rows if not r.get("ok", True)]
        if not rows:
            say("[green]No failed calls in the trace file.[/green]")
            sys.exit(0)
        show(rows)
    else:
        summarize(rows)
        say()
        shown = rows if "--all" in args else rows[-10:]
        if len(shown) < len(rows):
            say(f"[dim]— last {len(shown)} calls (--all for every one) —[/dim]\n")
        show(shown)
