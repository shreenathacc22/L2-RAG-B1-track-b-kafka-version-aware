"""A terminal chatbot with two kinds of memory.

Modern AI Pro · Level 2 · AI Practitioner

    python labs/chatbot.py

The API has no memory, so WE keep it. But "keep it" splits into two very
different jobs, and confusing them is the classic beginner's cost bug:

  TRANSCRIPT   memory.jsonl — every message, appended as it happens.
               Complete, disposable, and it grows without limit. We resend
               only the last few turns of it (MAI_WINDOW), because the
               tail of a conversation is what keeps replies coherent.

  PROFILE      profile.json — durable key:value facts about YOU.
                   name: Balaji
                   role: workshop instructor
               A handful of lines, resent in the system prompt on every
               single turn, forever. This is what makes the bot still know
               your name in three weeks when the transcript is long gone.

The trade the profile makes: the transcript is exact but expensive and
temporary; the profile is lossy but cheap and permanent. Every turn prints
both numbers so you can watch that trade instead of taking my word for it.

A model — never regex — decides what's durable. "Is this an invariant fact
about the user?" is a classification, and classification is a model's job.

Commands:  /profile  what's remembered   ·   /forget <key>  drop one fact
           /mem      the transcript       ·   /cost  the meter
           /reset    clear the transcript ·   /quit (or Ctrl-D)  leave

Off switches:  MAI_PROFILE=0  no extraction   ·   MAI_WINDOW=6  turns resent
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import episodic
from _kit import ask_yn, banner, chat, client, meter, say, stream_chat

SYSTEM = "You are a friendly, concise assistant. Answer in a few sentences unless asked for more."

MEMORY_FILE = Path(os.environ.get("MAI_MEMORY_FILE", "memory.jsonl"))
PROFILE_FILE = Path(os.environ.get("MAI_PROFILE_FILE", "profile.json"))
WINDOW = int(os.environ.get("MAI_WINDOW", "6"))     # messages, not turns: 6 ≈ 3 exchanges

# Extraction is the WRITE path, and it isn't free: one extra call whose
# instructions cost more than a short chat turn does. You CAN batch it — mine
# the last N turns at once — and MAI_PROFILE_EVERY=3 does exactly that.
#
# But the default is 1, deliberately. Batching makes turns 2 and 3 look broken:
# you say something durable, no `learned:` line appears, and the only honest
# conclusion is that the feature doesn't work. Feedback you can see beats tokens
# you can't. The real savings live in the READ path anyway — a 40-token profile
# standing in for a transcript that grows forever — and that runs every turn
# regardless. Set =3 in class to show the cost, then set it back.
EVERY = int(os.environ.get("MAI_PROFILE_EVERY", "1"))

# The trace classifier (labs/classify.py) downloads a ~370MB model and prints HF
# progress bars straight into the bot's reply. Fine for the traces lab, wrong for
# an interactive chat. Off here unless you asked for it.
os.environ.setdefault("MAI_CLASSIFY", "0")


# ── the transcript: append-only, complete, disposable ────────────────────────

def load_memory() -> list[dict]:
    """Replay the file into a message list (user/assistant only — the system
    prompt is rebuilt each run so edits to SYSTEM take effect immediately)."""
    history: list[dict] = []
    if not MEMORY_FILE.exists():
        return history
    for line in MEMORY_FILE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:      # a half-written last line: skip it, keep the rest
            continue
        if msg.get("role") in ("user", "assistant") and msg.get("content"):
            history.append({"role": msg["role"], "content": msg["content"]})
    return history


def remember(msg: dict) -> None:
    """Append one message. Never raises — a full disk must not kill the chat."""
    try:
        with MEMORY_FILE.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(msg, ensure_ascii=False) + "\n")
    except OSError:
        say("[yellow](couldn't write memory.jsonl — this turn won't survive a restart)[/yellow]")


# ── the profile: durable, tiny, permanent ────────────────────────────────────

def load_profile() -> dict:
    if not PROFILE_FILE.exists():
        return {}
    try:
        data = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
        return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        say(f"[yellow]({PROFILE_FILE} unreadable — starting a fresh profile)[/yellow]")
        return {}


def save_profile(profile: dict) -> None:
    """Write via a temp file + replace, so an interrupted write can't leave you
    with a truncated profile. The transcript can afford a torn last line; the
    profile is the file you'd actually miss."""
    try:
        tmp = PROFILE_FILE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(PROFILE_FILE)
    except OSError:
        say("[yellow](couldn't write profile.json — this fact won't survive a restart)[/yellow]")


PROFILE_SYS = """You maintain a user's durable profile — the small set of facts
worth remembering forever.

You are given the CURRENT profile exactly as it is stored on disk, plus the
latest conversation. Return the COMPLETE updated profile:

  {"profile": {"key": "value", ...}, "changes": ["added location: Chennai", ...]}

How to update it:
  KEEP   every existing fact, unchanged, unless the conversation contradicts it.
         Silence is not contradiction — a fact you weren't reminded of is still true.
  UPDATE a value in place when it genuinely changed (moved city, left a job).
         Reuse the existing key. Never add a second key for the same thing.
  ADD    a new fact only if it is durable — still true next month.
  DROP   a fact only when the user says it is no longer true, and say so in
         "changes".

A fact is durable if it is identity (name, role, employer, location, timezone,
language), a stable preference or constraint (dietary, accessibility, tools,
how they like answers formatted), or a long-running project or goal.

NOT durable: the current question, today's mood or weather, one-off requests,
facts about people other than the user, and anything you inferred rather than
were told.

Rules: snake_case keys · values under 8 words · "changes" lists only what you
actually altered, empty when nothing changed.

Prefer these key names when they fit, and only coin a new one when none does:
  name · preferred_name · role · employer · location · timezone · language
  expertise · current_project · goal · communication_style · constraint
Coining synonyms is the failure mode here: `occupation` and `employment`
alongside an existing `role` gives you three half-truths instead of one fact."""


def update_profile(cli, pending: list[dict]) -> tuple[dict, list[str]]:
    """The dedicated profile call: show the model the profile as it exists on
    disk, plus what was just said, and let it return the merged result.

    Why re-read the file instead of trusting the copy in memory? Because
    profile.json is a plain file a student may have hand-edited in the editor
    while the chat was running — and the whole promise of this design is that
    the file is the memory. Read what's actually there.

    Returns (merged_profile, changes). On any failure it returns the profile
    unchanged: a bad update must never be able to erase what we already knew."""
    current = load_profile()                    # ← the previous profile.json, verbatim
    if os.environ.get("MAI_PROFILE", "1") == "0" or not pending:
        return current, []
    convo = "\n".join(f"{m['role']}: {m['content']}" for m in pending)
    raw = chat(cli, [
        {"role": "system", "content": PROFILE_SYS},
        {"role": "user", "content": f"Current profile.json:\n"
                                    f"{json.dumps(current, ensure_ascii=False, indent=2)}\n\n"
                                    f"Latest conversation:\n{convo}"},
    # 400, not 200: json_object mode guarantees valid JSON only if the model
    # FINISHES. Hit the cap and you get a truncated string — or, measured on this
    # proxy, an empty one — about 4% of the time at 200. A cap sized to the answer
    # forgets to budget for the thinking that precedes it.
    ], label="profile", max_tokens=400, response_format={"type": "json_object"})
    try:
        obj = json.loads(raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip())
    except json.JSONDecodeError:
        # Fail soft: a bad update costs one turn's learning, never the profile.
        # The transcript still has the turn, so a later call can pick it up.
        return current, []
    merged = obj.get("profile") if isinstance(obj, dict) else None
    if not isinstance(merged, dict):
        return current, []
    merged = {str(k): str(v) for k, v in merged.items() if v not in (None, "", "unknown")}

    # The cost of letting a model rewrite your whole record: it can drop a fact
    # by simply not repeating it. Omission is not deletion — restore anything
    # that vanished without being reported in "changes", and say so out loud.
    changes = [str(c) for c in obj.get("changes", [])] if isinstance(obj.get("changes"), list) else []
    for key, value in current.items():
        if key not in merged and not any(key in c for c in changes):
            merged[key] = value
            say(f"[yellow](kept '{key}' — the update dropped it without saying why)[/yellow]")
    return merged, changes


def profile_block(profile: dict) -> str:
    """The cheapest possible encoding: one `key: value` line each. No JSON
    braces, no prose, no quotes — those are tokens that teach the model nothing."""
    return "\n".join(f"{k}: {v}" for k, v in profile.items())


def build_messages(profile: dict, history: list[dict], idx: dict | None = None) -> list[dict]:
    """What we actually send — all three memories in one system prompt, cheapest
    first:

      durable   every fact, always                        ~25 tokens
      episodic  the last few episode TITLES and gists     ~40 tokens
      working   the last WINDOW messages, verbatim        the expensive part

    The episode pointers are the interesting line. We can't afford to resend old
    conversations, but we can always afford to resend the fact that they
    happened — which is what lets the bot say "we worked on the pricing deck
    last week" without carrying one word of that deck."""
    system = SYSTEM
    if profile:
        system += ("\n\nWhat you know about the user (durable memory — use it "
                   "naturally, don't recite it back):\n" + profile_block(profile))
    if idx:
        block = episodic.pointer_block(idx)
        if block:
            system += ("\n\nEarlier conversations with this user (you remember that "
                       "these happened, not what was said — offer to pick one up if "
                       "it becomes relevant):\n" + block)
        current = episodic.title_of(idx, idx.get("current"))
        if current:
            system += f"\n\nRight now you are in the episode: {current}"
    return [{"role": "system", "content": system}] + history[-WINDOW:]


def rewrite_working_memory(messages: list[dict]) -> None:
    """memory.jsonl always holds exactly ONE episode's working memory. On a
    switch we replace it wholesale — but only ever after the outgoing episode
    has been written to its own file. Order matters: archive, then overwrite."""
    try:
        with MEMORY_FILE.open("w", encoding="utf-8") as fh:
            for m in messages:
                fh.write(json.dumps(m, ensure_ascii=False) + "\n")
    except OSError:
        say("[yellow](couldn't rewrite memory.jsonl — working memory may be stale)[/yellow]")


def maybe_switch_episode(cli, idx: dict, history: list[dict], user: str) -> list[dict] | None:
    """Did the subject change? If so, ASK — never decide silently.

    Returns the new working memory when we switched, or None to carry on.

    The asking is the design, not a limitation. Filing someone's conversation
    under the wrong heading without telling them is how a memory system loses
    their trust; a one-line question costs nothing and keeps them in charge."""
    if os.environ.get("MAI_EPISODE", "1") == "0" or len(history) < 4:
        return None                       # too early to tell a topic from an opening

    shift = episodic.detect_shift(cli, episodic.title_of(idx, idx.get("current")),
                                  history, user, idx)
    if not shift or shift.get("same_topic", True) or shift.get("confidence") == "low":
        return None                       # continuing is always the safe answer

    theme = str(shift.get("theme") or "something new")
    resume_id = shift.get("resume_episode_id")
    resume_title = episodic.title_of(idx, resume_id) if resume_id else ""

    say(f"\n[yellow]—[/yellow] that looks like a new subject: [bold]{theme}[/bold]")
    if resume_title:
        say(f"  [dim](we have an episode for it: {resume_title})[/dim]")
    if not ask_yn("switch episodes?", default=False):
        say("[dim]staying put.[/dim]\n")
        return None

    # 1. close the current episode: its working memory becomes its transcript,
    #    plus a summary of the state it was left in.
    old_id = idx.get("current")
    if old_id and history:
        ep = episodic.archive(cli, idx, old_id, history)
        say(f"[dim]filed [bold]{ep['title']}[/bold] — "
            f"{plural(len(history), 'message')}, summarised.[/dim]")

    # 2. open the destination, either an old episode or a fresh one.
    if resume_id and episodic.load_episode(resume_id):
        new_history = episodic.resume(idx, resume_id)
        ep = episodic.load_episode(resume_id) or {}
        say(f"[green]resumed[/green] [bold]{ep.get('title', resume_id)}[/bold] "
            f"({plural(len(new_history), 'message')})")
        if ep.get("summary"):
            say(f"[dim]where we left off: {ep['summary']}[/dim]")
    else:
        new_id = episodic.start(idx, title=theme)
        new_history = []
        say(f"[green]started[/green] [bold]{theme}[/bold] [dim]({new_id})[/dim]")

    # 3. working memory now belongs to the new episode.
    rewrite_working_memory(new_history)
    say()
    return new_history


def plural(n: int, word: str) -> str:
    """'1 fact' / '2 facts' — this text lands on a projector."""
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def approx_tokens(text: str) -> int:
    """~4 characters per token. Enough to watch a trend, not to bill anyone —
    the exact numbers come from the API's usage block."""
    return len(text) // 4


def main() -> None:
    banner("Level 2 · AI Practitioner", "Three kinds of memory")
    cli = client()
    say("[dim]/profile facts · /episodes list · /switch new · /mem · /cost · /quit[/dim]\n")

    history = load_memory()
    profile = load_profile()
    idx = episodic.load_index()
    pending: list[dict] = []            # turns seen but not yet mined for facts

    # Every conversation belongs to an episode, including the first one.
    if not idx.get("current"):
        episodic.start(idx, title="First conversation")

    if profile:
        say(f"[green]profile:[/green] {plural(len(profile), 'durable fact')} "
            f"(~{approx_tokens(profile_block(profile))} tokens) — "
            + " · ".join(f"[bold]{k}[/bold] {v}" for k, v in list(profile.items())[:4])
            + (" …" if len(profile) > 4 else ""))
    else:
        say("[dim]profile: empty (tell me your name and watch)[/dim]")
    # Absolute paths, always. These are relative filenames written to the CWD, so
    # `python labs/chatbot.py` and `cd labs && python chatbot.py` put them in
    # different directories — and a file you can't find reads as a file that
    # was never written.
    say(f"[dim]  profile    → {PROFILE_FILE.resolve()}[/dim]")
    say(f"[dim]  transcript → {MEMORY_FILE.resolve()} ({len(history)} messages, "
        f"resending last {WINDOW})[/dim]")
    say(f"[dim]  episodes   → {episodic.EPISODE_DIR.resolve()}[/dim]")

    say(f"\n[cyan]episode:[/cyan] [bold]{episodic.title_of(idx, idx['current'])}[/bold] "
        f"[dim]({idx['current']})[/dim]")
    for ep in episodic.pointers(idx):
        say(f"  [dim]· {ep.get('title')} — {(ep.get('summary') or '')[:70]}[/dim]")
    say()

    while True:
        try:
            user = input("you > ").strip()
        except (EOFError, KeyboardInterrupt):   # Ctrl-D / Ctrl-C
            break
        if not user:
            continue
        if user in ("/quit", "/exit", "/q"):
            break
        if user == "/episodes":
            say(f"[bold]episodic memory[/bold] [dim]({episodic.EPISODE_DIR})[/dim]")
            for ep in sorted(idx["episodes"], key=lambda e: e.get("updated", ""), reverse=True):
                current = ep["id"] == idx["current"]
                # The index row is only rewritten when an episode is archived, so
                # for the one we're inside, the live count is the true one.
                count = len(history) if current else ep.get("messages", 0)
                here = " [cyan]← you are here[/cyan]" if current else ""
                say(f"  [bold]{ep['id']}[/bold] {ep.get('title','')} "
                    f"[dim]({plural(count, 'msg')})[/dim]{here}")
                if ep.get("summary"):
                    say(f"      [dim]{ep['summary'][:100]}[/dim]")
            say()
            continue
        if user.startswith("/switch"):
            target = user[len("/switch"):].strip()
            if history:                       # close the current one first, always
                ep = episodic.archive(cli, idx, idx["current"], history)
                say(f"[dim]filed [bold]{ep['title']}[/bold].[/dim]")
            if target and target != "new" and episodic.load_episode(target):
                history = episodic.resume(idx, target)
                ep = episodic.load_episode(target) or {}
                say(f"[green]resumed[/green] [bold]{ep.get('title', target)}[/bold]")
                if ep.get("summary"):
                    say(f"[dim]where we left off: {ep['summary']}[/dim]")
            else:
                if target and target != "new":
                    say(f"[yellow]no episode {target}[/yellow] — starting a new one")
                episodic.start(idx, title="New episode")
                history = []
                say("[green]started a new episode.[/green]")
            rewrite_working_memory(history)
            pending = []
            say()
            continue
        if user == "/profile":
            if profile:
                say(f"[bold]durable memory[/bold] [dim]({PROFILE_FILE}, "
                    f"~{approx_tokens(profile_block(profile))} tokens)[/dim]")
                for k, v in profile.items():
                    say(f"  [cyan]{k}[/cyan]: {v}")
            else:
                say("[dim]profile is empty — nothing durable learned yet[/dim]")
            say()
            continue
        if user.startswith("/forget"):
            key = user[len("/forget"):].strip()
            if key == "all":
                profile = {}
                save_profile(profile)
                say("[yellow]profile cleared.[/yellow]\n")
            elif key in profile:
                profile.pop(key)
                save_profile(profile)
                say(f"[yellow]forgot[/yellow] {key}\n")
            else:
                say("[dim]usage: /forget <key>  ·  /forget all[/dim]\n")
            continue
        if user == "/reset":
            if MEMORY_FILE.exists():
                MEMORY_FILE.replace(MEMORY_FILE.with_suffix(MEMORY_FILE.suffix + ".bak"))
            history = []
            say(f"[yellow]transcript cleared[/yellow] [dim](kept as {MEMORY_FILE.name}.bak). "
                f"The profile survives — that's the point of it.[/dim]\n")
            continue
        if user == "/mem":
            size = MEMORY_FILE.stat().st_size if MEMORY_FILE.exists() else 0
            full = approx_tokens("".join(m["content"] for m in history))
            say(f"[dim]transcript: {len(history)} messages · {size} bytes · ~{full} tokens "
                f"if we resent all of it (we resend {min(WINDOW, len(history))})[/dim]\n")
            continue
        if user == "/cost":
            meter.show()
            say()
            continue

        # Check for a change of subject BEFORE this message joins the transcript,
        # so that if we do switch, the message that started the new topic lands in
        # the new episode rather than the one it just ended.
        switched = maybe_switch_episode(cli, idx, history, user)
        if switched is not None:
            history = switched
            pending = []                  # those turns went with the old episode

        history.append({"role": "user", "content": user})
        remember({"role": "user", "content": user})

        sent_before = (meter.prompt_tokens, meter.completion_tokens)

        say("bot > ", end="")
        try:
            reply = stream_chat(cli, build_messages(profile, history, idx), label="chat",
                                max_tokens=400, on_delta=lambda d: say(d, end=""))
        except KeyboardInterrupt:
            # Ctrl-C DURING the reply, not at the prompt. Uncaught, this killed the
            # process outright and took the end-of-session save with it.
            say("\n[yellow](interrupted)[/yellow]")
            pending.append({"role": "user", "content": user})
            break
        say("\n")

        history.append({"role": "assistant", "content": reply})
        remember({"role": "assistant", "content": reply})

        chat_tok = (meter.prompt_tokens - sent_before[0],
                    meter.completion_tokens - sent_before[1])

        # Learn AFTER answering: the user waits for the reply, not for bookkeeping.
        pending += [{"role": "user", "content": user},
                    {"role": "assistant", "content": reply}]
        extract_tok = 0
        # Cold start beats batching: while the profile is still empty, mine every
        # turn. Turn 1 is when the user says their name, it's when they're checking
        # whether this thing works at all, and batching there means they type
        # "I'm Balaji", see nothing happen, quit, and find no file. (It did. Sorry.)
        if not profile or len(pending) >= 2 * EVERY:
            extract_before = meter.total_tokens
            merged, changes = update_profile(cli, pending)
            extract_tok = meter.total_tokens - extract_before
            pending = []
            if merged != profile:
                profile = merged                    # the model's merge, not dict.update
                save_profile(profile)
                say("[green]profile updated:[/green] " +
                    (" · ".join(changes) if changes else
                     " · ".join(f"[bold]{k}[/bold]: {v}" for k, v in profile.items())))

        # The whole lesson in one line: what the profile costs, versus what
        # carrying the same knowledge as raw transcript would have cost.
        prof_tok = approx_tokens(profile_block(profile))
        full_tok = approx_tokens("".join(m["content"] for m in history))
        if chat_tok[0] or chat_tok[1]:
            say(f"[dim]this turn: {chat_tok[0]} sent + {chat_tok[1]} received"
                + (f" · +{extract_tok} to extract facts" if extract_tok else "")
                + f" · session {meter.total_tokens}[/dim]")
        say(f"[dim]memory: profile ~{prof_tok} tok ({plural(len(profile), 'fact')}, always sent) "
            f"vs full transcript ~{full_tok} tok ({len(history)} msgs, "
            f"{min(WINDOW, len(history))} sent)[/dim]\n")

    # Flush: whatever we learned in the last partial batch would otherwise be
    # lost at the exact moment the user walks away.
    if pending:
        say("\n[dim](updating the profile…)[/dim]")
        merged, changes = update_profile(cli, pending)
        if merged != profile:
            profile = merged
            save_profile(profile)
            say("[green]profile updated:[/green] " +
                (" · ".join(changes) if changes else ", ".join(profile)))
        else:
            say("[dim]nothing durable in the last few turns.[/dim]")

    # Close the episode on the way out. An episode nobody closed has no summary,
    # and an episode with no summary is one you can't meaningfully resume — the
    # transcript survives, but the thing that made it cheap to return to doesn't.
    if history and os.environ.get("MAI_EPISODE", "1") != "0":
        say("[dim](closing this episode…)[/dim]")
        ep = episodic.archive(cli, idx, idx["current"], history)
        say(f"[cyan]episode:[/cyan] [bold]{ep['title']}[/bold] "
            f"[dim]({plural(len(history), 'message')})[/dim]")
        if ep.get("summary"):
            say(f"[dim]{ep['summary']}[/dim]")

    say("\n[dim]bye — this session cost:[/dim]")
    meter.show()
    if profile:
        say(f"[dim]I'll still know {plural(len(profile), 'thing')} about you next time: "
            f"{', '.join(profile)}[/dim]")


if __name__ == "__main__":
    main()
