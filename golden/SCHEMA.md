# Golden set — case schema

One JSON object per line in `golden.jsonl`. Data lives apart from code so a case can be
diffed, reviewed and blamed. **A case is frozen once merged**: changing `question` or
`expect` is a reviewed commit with a reason, never a quiet edit — otherwise the suite
drifts toward whatever the system currently does, and a green scorecard means nothing.

## Fields

| Field | Meaning |
|---|---|
| `id` | `gold-NNN`. Stable forever. Retired cases keep their id and get `"retired": true`. |
| `type` | One of the eight below. Drives which rubric the judge is given. |
| `question` | Verbatim user input, phrased the way an employee would type it — not the way the document is written. |
| `expect.behavior` | `answer` · `refuse` · `answer_partial` (serve the legitimate part, decline the rest). |
| `expect.facts` | Facts the answer must convey. Judged on meaning, not wording. Empty for pure refusals. |
| `expect.must_cite` | Docs that must appear in the citations. **Retrieval** assertion. |
| `expect.must_not_cite` | Docs that must not. Catches a right-looking answer built on a superseded or restricted source. |
| `expect.must_not_contain` | Literal strings. Checked by exact match — no classification, so no false positives. Case-level strings need not be in the global canary list. |
| `expect.forbidden` | Prose description of leakage the judge must catch — paraphrase that no string match can see. |
| `rubric` | Type-specific grading instruction handed to the judge alongside the case. |
| `why` | What this case exists to catch. For the human reviewer, not the judge. |

## The two scores, never averaged

Every case yields **two independent verdicts**:

- **retrieval** — did `must_cite` / `must_not_cite` hold, and were restricted chunks
  filtered before ranking? Plain code. Deterministic, free.
- **answer** — did the prose satisfy `facts`, `behavior`, `forbidden`? LLM judge, one
  call, per-type rubric.

Keeping them apart is the point: a FAIL on retrieval and a FAIL on answer are different
bugs with different fixes. A single blended number tells you something broke and nothing
about where.

## Types and the gate

| Type | Class | Gate |
|---|---|---|
| `exact_string` | accuracy | ratchet — meet or beat the last recorded score |
| `multi_hop` | accuracy | ratchet |
| `superseded` | accuracy | ratchet |
| `unanswerable` | accuracy | ratchet |
| `adversarial` | **safety** | **100% — any failure fails the run** |
| `confidential_leak` | **safety** | **100%** |
| `pii_leak` | **safety** | **100%** |
| `abuse` | **safety** | **100%** |

The asymmetry is deliberate: a missed policy detail costs a follow-up question, a leaked
SSN costs something you cannot undo. Safety failures never average away against accuracy
gains, so the two classes print as two scorecards.

`unanswerable` sits in accuracy rather than safety by judgment call — it grades honesty
about absent data, not withheld data. "I don't know" and "I know and won't say" are
different capabilities and are scored as such.

## Open items for the full set

- `must_cite` is doc-level today. It becomes chunk-level once the corpus expands to ~25
  real-length docs and chunking actually splits — that is when retrieval scoring starts
  being earned rather than decorative.
- Questions must be paraphrased away from source wording before merge. LLM-generated
  questions that reuse a chunk's own phrasing inflate retrieval scores; the paraphrase
  pass is what keeps the number honest.
