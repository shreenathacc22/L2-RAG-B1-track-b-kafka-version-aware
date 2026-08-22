"""Episodic memory — the third tier.

Modern AI Pro · Level 2 · AI Practitioner

    DURABLE   profile.json     facts that are true regardless of topic
    EPISODIC  episodes/*.json  past conversations, filed by theme, each with a
                               summary of where it left off      ← this file
    WORKING   memory.jsonl     the conversation happening right now

Human memory works roughly this way and the analogy is worth making in class:
you know your own name without recalling when you learned it (durable), you can
recall "that argument about the budget last March" as an episode with a gist
rather than a transcript (episodic), and you are holding this sentence in your
head right now (working).

The moves this module supports:

    detect     did the user just change the subject?  (a model decides — never
               a keyword list, because "anyway, unrelated —" and "oh also, my
               taxes" are the same event wearing different words)
    archive    move working memory into an episode file, with a summary
    resume     load a past episode back into working memory
    pointers   the last few episode titles + gists, cheap enough to carry in
               every system prompt so the bot knows what you've discussed before

Layout on disk:

    episodes/index.json          which episode is current + pointers to the rest
    episodes/ep-0001.json        {id, title, summary, messages: [...]}
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from _kit import chat, say

EPISODE_DIR = Path(os.environ.get("MAI_EPISODE_DIR", "episodes"))
INDEX_FILE = EPISODE_DIR / "index.json"
POINTERS = int(os.environ.get("MAI_EPISODE_POINTERS", "3"))   # how many to carry


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _write_json(path: Path, data: dict) -> None:
    """Temp file + replace, same reasoning as profile.json: an interrupted write
    must not be able to shred an episode you can never reconstruct."""
    try:
        EPISODE_DIR.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(path)
    except OSError as e:
        say(f"[yellow](couldn't write {path.name}: {e})[/yellow]")


# ── the index ────────────────────────────────────────────────────────────────

def load_index() -> dict:
    if not INDEX_FILE.exists():
        return {"current": None, "episodes": []}
    try:
        idx = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
        idx.setdefault("current", None)
        idx.setdefault("episodes", [])
        return idx
    except (json.JSONDecodeError, OSError):
        say("[yellow](episodes/index.json unreadable — starting a fresh index)[/yellow]")
        return {"current": None, "episodes": []}


def save_index(idx: dict) -> None:
    _write_json(INDEX_FILE, idx)


def next_id(idx: dict) -> str:
    """ep-0001, ep-0002, … Sortable, and it reads fine in a file listing."""
    n = 0
    for ep in idx["episodes"]:
        try:
            n = max(n, int(str(ep["id"]).split("-")[-1]))
        except (ValueError, KeyError):
            continue
    return f"ep-{n + 1:04d}"


def pointers(idx: dict, limit: int = POINTERS) -> list[dict]:
    """The last few episodes, newest first, excluding the one we're in.

    These ride in the system prompt — a title and a one-line gist each. That's
    the whole trick: you can't afford to carry old conversations, but you can
    always afford to carry the fact that they happened."""
    out = [ep for ep in idx["episodes"] if ep.get("id") != idx.get("current")]
    out.sort(key=lambda e: e.get("updated", ""), reverse=True)
    return out[:limit]


def pointer_block(idx: dict, limit: int = POINTERS) -> str:
    rows = pointers(idx, limit)
    if not rows:
        return ""
    return "\n".join(f"- {ep.get('title', ep['id'])}: {ep.get('summary', '')}" for ep in rows)


# ── episode files ────────────────────────────────────────────────────────────

def episode_path(ep_id: str) -> Path:
    return EPISODE_DIR / f"{ep_id}.json"


def load_episode(ep_id: str) -> dict | None:
    path = episode_path(ep_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        say(f"[yellow](couldn't read {path.name})[/yellow]")
        return None


def _upsert(idx: dict, ep: dict) -> None:
    row = {"id": ep["id"], "title": ep.get("title", ep["id"]),
           "summary": ep.get("summary", ""), "updated": ep.get("updated", _now()),
           "messages": len(ep.get("messages", []))}
    idx["episodes"] = [e for e in idx["episodes"] if e.get("id") != ep["id"]] + [row]


# ── the LLM calls ────────────────────────────────────────────────────────────

TOPIC_SYS = """You watch a conversation for THEMATIC changes of subject.

You get the current episode's title, the last few messages, the user's newest
message, and a list of past episodes. Decide whether the newest message belongs
to the conversation in progress.

Return ONLY JSON:
  {"same_topic": true|false,
   "theme": "3-6 words naming the new subject, if it changed",
   "resume_episode_id": "ep-0002" | null,
   "confidence": "high"|"low"}

same_topic is FALSE only for a real change of subject — the user has moved to
different work, a different project, a different part of their life.

same_topic is TRUE for: follow-up questions, tangents that serve the same task,
clarifications, "wait, back up", small talk inside a working session, and
anything ambiguous. Continuing is the safe default; interrupting someone to ask
about filing is worse than filing it wrong.

Set resume_episode_id when the new subject clearly matches a PAST episode in the
list — the user is returning to something, not starting it. Otherwise null.

Set confidence "low" if you are unsure at all. Low confidence means we won't
interrupt the user."""


def detect_shift(cli, title: str, recent: list[dict], new_msg: str, idx: dict) -> dict:
    """Has the subject changed? A classifier, never a keyword list.

    Returns {} on any failure — the conversation continues in the current
    episode, which is always a safe answer."""
    if os.environ.get("MAI_EPISODE", "1") == "0":
        return {}
    past = "\n".join(f"- {e['id']}: {e.get('title','')} — {e.get('summary','')[:80]}"
                     for e in pointers(idx, 6)) or "(none yet)"
    convo = "\n".join(f"{m['role']}: {m['content'][:200]}" for m in recent[-4:])
    raw = chat(cli, [
        {"role": "system", "content": TOPIC_SYS},
        {"role": "user", "content": f"Current episode: {title or '(untitled)'}\n\n"
                                    f"Recent messages:\n{convo}\n\n"
                                    f"Newest user message:\n{new_msg}\n\n"
                                    f"Past episodes:\n{past}"},
    ], label="topic", max_tokens=300, response_format={"type": "json_object"})
    try:
        out = json.loads(raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip())
    except json.JSONDecodeError:
        return {}
    return out if isinstance(out, dict) else {}


SUMMARY_SYS = """Summarize a finished stretch of conversation so it can be
picked up later, by someone who will NOT have the transcript.

Return ONLY JSON:
  {"title": "3-6 words naming the episode",
   "summary": "3-4 sentences: what was discussed, what was decided, and what
               was still open when it ended"}

Write the summary for the person who was there. Concrete nouns, actual
decisions, real numbers. No 'the user asked about various topics'."""


def summarize(cli, messages: list[dict], fallback_title: str = "") -> dict:
    """The 'summary of the last state' — what this episode was, and where it
    stopped. This is the thing that makes an episode resumable: the transcript
    is too expensive to reload, the gist is not."""
    convo = "\n".join(f"{m['role']}: {m['content']}" for m in messages)[-6000:]
    if not convo.strip():
        return {"title": fallback_title or "Empty episode", "summary": ""}
    raw = chat(cli, [
        {"role": "system", "content": SUMMARY_SYS},
        {"role": "user", "content": convo},
    ], label="summary", max_tokens=500, response_format={"type": "json_object"})
    try:
        out = json.loads(raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip())
    except json.JSONDecodeError:
        out = {}
    return {"title": str(out.get("title") or fallback_title or "Untitled episode"),
            "summary": str(out.get("summary") or "")}


# ── the moves ────────────────────────────────────────────────────────────────

def archive(cli, idx: dict, ep_id: str, messages: list[dict], title: str = "") -> dict:
    """Move working memory into its episode file, with a fresh summary.

    Called on every switch AND on quit — an episode you never closed is an
    episode with no summary, which is an episode you can't resume."""
    existing = load_episode(ep_id) or {"id": ep_id, "created": _now()}
    combined = messages                      # working memory IS the episode's transcript
    meta = summarize(cli, combined, fallback_title=title or existing.get("title", ""))
    ep = {**existing, "id": ep_id, "title": meta["title"], "summary": meta["summary"],
          "updated": _now(), "messages": combined}
    _write_json(episode_path(ep_id), ep)
    _upsert(idx, ep)
    save_index(idx)
    return ep


def start(idx: dict, title: str = "New episode") -> str:
    """Open a fresh episode and make it current."""
    ep_id = next_id(idx)
    ep = {"id": ep_id, "title": title, "summary": "", "created": _now(),
          "updated": _now(), "messages": []}
    _write_json(episode_path(ep_id), ep)
    _upsert(idx, ep)
    idx["current"] = ep_id
    save_index(idx)
    return ep_id


def resume(idx: dict, ep_id: str) -> list[dict]:
    """Load a past episode back into working memory. Returns its messages."""
    ep = load_episode(ep_id)
    if ep is None:
        return []
    idx["current"] = ep_id
    save_index(idx)
    return [m for m in ep.get("messages", [])
            if m.get("role") in ("user", "assistant") and m.get("content")]


def title_of(idx: dict, ep_id: str | None) -> str:
    for e in idx["episodes"]:
        if e.get("id") == ep_id:
            return e.get("title", ep_id or "")
    return ep_id or ""
