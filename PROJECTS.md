# Level 2 — Project Ideas

Pick **one** project. Each is a weekend of work on top of what Labs 1–5 already gave you,
and each ends in **one number a stranger can act on**.

Three shapes, three starting points — do not start from a blank file:

| Track | Extends | The artifact |
|---|---|---|
| **A · Evals** | [`golden/SCHEMA.md`](./golden/SCHEMA.md) + `rag.py eval` | a **RAG Readiness Report** for a real industry |
| **B · RAG design** | [`simple_rag/`](./simple_rag/README.md) — a new stage in the pipeline | a **before/after ablation** on your own golden set |
| **C · Agents** | [`stock_rag/predict.py`](./stock_rag/predict.py) — 2 retrievers, 1 grounded call | a **JSON verdict with citations** you can grade |

**The one rule that makes it a project and not a demo:** the golden set is written **before**
the system is good, and frozen. Cases written after you see the output grade whatever you
already built.

---

## Track A — Evals: score somebody's RAG

The deliverable is not a chatbot. It is a **report a company could read and know where their
RAG is weak** — and *which fix* to buy. That report is only as good as the corpus you pick.

### Pick a corpus that can be scored

A scorable corpus has all four traps in it naturally. Yours must too, or the score is
decorative:

| Trap | What it catches | Looks like |
|---|---|---|
| **exact alphanumerics** | embeddings blur `net-45`; only BM25/hybrid nails it | thresholds, dosages, section numbers |
| **cross-references** | chunk too small and the fact splits in half | "except as provided in §1926.502" |
| **a superseded version** | similarity cannot tell two versions apart — only metadata can | 2024 vs 2026 edition, both public |
| **something it must refuse** | the safety class, gated at 100% | PII, medical/legal advice, restricted docs |

### Five industries where that corpus is free and real

| # | Industry | Where the docs are | Why it scores well |
|---|---|---|---|
| A1 | **Workplace safety** | eCFR bulk XML — 29 CFR 1926 (construction) | cross-references are *built into the text*; amendments are dated; numbers everywhere ("guardrails 42 in ± 3") |
| A2 | **Drug labels** | DailyMed / openFDA, free API | dosage strings, contraindication multi-hop, revised labels for supersession — and "should I take this?" is a **must-refuse** |
| A3 | **Health plans** | any insurer's public SBC PDFs, 2 plan years | deductible/copay numbers, plan-year supersession, PHI questions to refuse |
| A4 | **Public company filings** | SEC EDGAR full-text, one company × 3 years | figures live in *tables* (where naive chunking dies), YoY questions are multi-hop, last year's 10-K is the superseded doc |
| A5 | **Tax guidance** | IRS Pub 17, two tax years | the exact `travel-policy v2 vs v4` trap at national scale — pick a number that sits *between* the two years' thresholds |

Start at **30–40 documents and 25 cases**. More documents than that and you spend the weekend
on ingestion; fewer than 25 cases and one flipped case moves the score 4 points.

### The score

Two scorecards, **never averaged** — that discipline is already specified in
[`golden/SCHEMA.md`](./golden/SCHEMA.md); your job is to turn it into a report.

```
SAFETY      pass/fail       any single failure fails the run
ACCURACY    0–100           four sub-scores, each naming its own fix
```

The sub-scores are the product. A single 72/100 tells a company nothing; this tells them
what to go do on Monday:

| Sub-score | If it's low, the fix is |
|---|---|
| `exact_string` | add BM25 + RRF — you are on pure embeddings |
| `multi_hop` | chunk size / overlap, or query decomposition |
| `superseded` | version metadata + a filter at query time, not better ranking |
| `unanswerable` | no abstain path — the prompt never gave it permission to say "I don't know" |

Split every case into **retrieval** (deterministic, free) and **answer** (LLM judge), and
print them apart — "the chunk never arrived" and "it arrived and was ignored" are different
bugs. Add cost and p50 latency per query from the Lab 1 meter, because "how good" and "at
what price" are the same question to a buyer.

**Ship:** `report.md` — one page, the two scorecards, the four sub-scores, the three worst
failing cases quoted verbatim. That last part is what makes people believe the number.

---

## Track B — RAG design: add one stage, prove it earned its place

`simple_rag/` already measures five stages (load → chunk → embed → store → retrieve/generate)
and writes `rag_traces.jsonl`. Each project below adds **one** stage or one metric, then
proves it with an ablation: same golden set, feature off vs on, report which case *types*
moved.

*A feature that improves the average but moves no case type is noise. Say so if that happens —
that is a real finding, not a failed project.*

| # | Project | The new stage | The number that proves it |
|---|---|---|---|
| B1 | **Version-aware retrieval** | `effective_date` / `version` into Chroma metadata, filtered at query | % of retrieved chunks that are superseded — should go to 0 while `exact_string` stays flat |
| B2 | **Tiered access** | drop restricted chunks **before** ranking, not after | leak rate on the `confidential_leak` cases — must be exactly 0, and the accuracy score must not drop |
| B3 | **Reranker** | a local cross-encoder as stage 6 over top-20 → top-4 | top-1 similarity *and* answer score, against +Xms and +$0 (it's local) |
| B4 | **Tables** | a table-aware chunker for the PDFs naive packing shreds | extraction yield on table pages, then which `exact_string` cases flip |
| B5 | **Query decomposition** | split a multi-hop question into two retrievals, merge | the `multi_hop` sub-score, and only that one |
| B6 | **The router earns its keep** | extend `route.py` to 3-way: chat / retrieve / act | ms and $ saved per 100 turns vs. retrieving on every turn |
| B7 | **Chunk-level `must_cite`** | assert the *chunk*, not the doc | this closes a real open item in `golden/SCHEMA.md` — retrieval scoring stops being decorative |

Any of these swaps in your own corpus for the Aventro one. That version is the portfolio piece.

---

## Track C — Agents: a verdict you can grade

`stock_rag/predict.py` is the whole pattern in 147 lines: **two retrievers → one grounded LLM
call → strict JSON with citations**, plus the honesty contract (`if the sources don't support a
view, keep confidence ≤ 0.5`). Keep that shape. Swap the domain.

| # | Agent | Retriever 1 | Retriever 2 | The JSON verdict |
|---|---|---|---|---|
| C1 | **Vendor risk pre-check** | Tavily news on the vendor | their public trust/security page | `{risk, confidence, findings[], needs_human}` |
| C2 | **On-call triage** | provider status pages / GitHub issues API | your own runbook corpus (Track B store) | `{severity, first_action, page_who}` |
| C3 | **Recall checker** | openFDA / CPSC recall API | the product's own manual | `{affected: bool, lot_range, what_to_do}` |
| C4 | **Grant / RFP fit** | grants.gov API | your capability one-pager | `{fit, requirements_failed[], confidence}` |
| C5 | **Disruption rights** | live flight/order status API | the DOT rules corpus | `{entitled_to[], not_entitled[], cite}` |

Two upgrades take it from Lab 4 to shippable, both already demonstrated in the repo:

→ **Risk tags travel with the tool, not the prompt** (`lab_4.py → RISK`) — a read tool runs, a
`destructive` one pauses for a human. No wording gets past a structural tag.
→ **A budget cap**, so a tool loop cannot run away.

### Grading an agent is different — score the trajectory, not just the answer

The final answer being right does not mean the agent was right. Write ~15 cases and score four
things, each of which fails independently:

| Metric | Fails when |
|---|---|
| **tool-choice precision** | it searched when it should have calculated, or retrieved on "thanks" |
| **HITL recall** | a destructive action ran without pausing — **gate this at 100%** |
| **budget adherence** | it hit the cap instead of finishing |
| **honesty under thin sources** | retrieval came back empty and it answered confidently anyway |

That last one is the most valuable case class you can write, and the cheapest: delete the
sources, run it, see whether it admits it. `predict.py`'s "no news retrieved — watch whether it
admits that" is exactly this test, run by hand.

---

## What "done" looks like

→ a **frozen** `golden.jsonl` — ≥ 25 cases for Track A, ≥ 15 for B and C — committed *before* the
  scores were good, with a `why` on every case
→ an **ablation**: the same suite, feature off and on, in one table
→ a **report** a non-engineer can read: the two scorecards, the sub-scores, three failing cases
  quoted, cost and latency per query
→ your **own corpus** — not Meridian, not Aventro

Skip the frozen-first step and everything downstream is decoration. That is the whole lesson of
Level 2, and it is the one thing employers can check.
