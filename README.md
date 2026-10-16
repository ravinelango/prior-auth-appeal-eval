# prior-auth-appeal-eval

![status](https://img.shields.io/badge/status-early%20(v0.1)-orange)
![license](https://img.shields.io/badge/license-MIT-blue)

**Deterministic checks for LLM-drafted prior-authorization appeal letters.** Given a denial,
a patient chart and the policy criteria the drafter is allowed to cite, it checks whether the
appeal draft invents a policy, invents a clinical fact, ignores the denial reason, gets an
identifier wrong, leaves out required parts, or over-shares identifiers the appeal does not
need, then rolls the results up into a go/no-go style
report.

> **Everything here is synthetic.** Patients, members, claims, clinicians and policies are
> invented (IDs start with `SYN-`). The policies are written for testing and are **not** real
> payer or Medicare text. **No real-model results are published.**

## Use case
A provider's revenue-cycle team uses an LLM to draft appeal letters after a payer denies a
prior-authorization request. A wrong letter costs time at best and, at worst, misstates the
chart or cites coverage language that does not exist. Before such a drafter is used, the team
needs to know what it gets wrong and to gate changes to it.

Public context (descriptive only; this project does not implement or claim compliance with
either):
- Medicare coverage criteria are published in the
  [Medicare Coverage Database](https://www.cms.gov/medicare-coverage-database/search.aspx)
  (NCDs and LCDs). The synthetic policies here only imitate that general shape: indications
  plus documentation requirements.
- The [CMS Interoperability and Prior Authorization final rule (CMS-0057-F)](https://www.cms.gov/newsroom/fact-sheets/cms-interoperability-prior-authorization-final-rule-cms-0057-f)
  is why payers' prior-authorization decisions and reasons are getting more structured and
  visible.

## Failure modes and the check for each
| Failure mode | Check | Severity | How it is detected |
|---|---|---|---|
| Invented or wrong policy citation | `citations` | critical | Every LCD/NCD-style reference must be in the provided policy set, must be the policy that governs the denial, and any cited criterion must exist; the governing policy must be cited |
| Clinical fact not in the chart | `facts_in_chart` | critical | Each bullet under "Clinical summary": every number and date must appear in the chart, and the share of content words absent from the chart must be small |
| Denial reason not addressed | `denial_reason_addressed` | critical | The "Response to denial reason" section must cite each unmet criterion id and engage with the expected reason terms |
| Wrong patient, claim, member, CPT or ICD | `identifiers_match` | critical | Extracted identifiers must equal the case's; missing ones are flagged |
| Missing required elements | `required_elements` | major | Explicit request to overturn, enclosures list, signature with NPI, letter dated on or before the appeal deadline |
| Extra PHI (minimum necessary) | `extra_phi` | major | SSNs, US phone numbers, email addresses and street-address strings in the letter must appear in the chart or denial letter; anything else is flagged as over-shared |

**Decision rollup:** NO-GO if any critical check fails on any case; GO WITH CONDITIONS if only
major checks (`required_elements`, `extra_phi`) fail; GO otherwise.

## How it works
1. **Cases** (`examples/synthetic_cases.json`): 25 synthetic denials, each with the denial
   letter text, reason code and unmet criteria, a patient chart, the provided policy set, and
   two reference drafts: one good and one with a seeded flaw. They are generated from templates
   by `scripts/build_example_cases.py`, so they are reproducible but formulaic. PA-011..PA-015
   carry harder flaws: a negation flip, near-miss member ID and CPT, a swapped ICD-10 code, and
   a paraphrased number. PA-016..PA-020 add a criterion number the policy does not have, a
   patient name pasted from another case, a shifted chart date, a response that cites the
   criterion but never engages the stated reason, and a letter filed after the deadline.
   PA-021..PA-025 add a denial with two unmet criteria where the flawed letter answers only
   one, a citation to a real-looking NCD number that was never provided, an SSN pasted into the
   header (caught only by `extra_phi`), a one-digit near-miss claim ID, and a letter that drops
   the explicit request to overturn.
2. **Drafter** (`drafters.py`): a small interface. The offline `mock:good` / `mock:flawed`
   drafters replay the reference drafts, so everything runs with no API keys.
   `files:DIR` reads letters you produced elsewhere (`DIR/<case id>.txt`).
   `openai` / `openai:MODEL` posts `build_prompt(case)` to an OpenAI-compatible chat
   endpoint (`OPENAI_API_KEY`, optional `OPENAI_BASE_URL`; `pip install -e '.[openai]'`).
   `pae prompt` prints the exact drafting prompt and output format for a case.
3. **Checks** (`checks.py`): the six deterministic checkers above.
4. **Report** (`report.py`): per-check and per-case tables, findings, the decision, and, for
   the mock drafters, a validation table showing the checks fire on exactly the seeded flaws.

## Quickstart
```bash
pip install -e '.[dev]'
pae validate --cases examples/synthetic_cases.json
pae run --cases examples/synthetic_cases.json --drafter mock:good   --out reports/good.md
pae run --cases examples/synthetic_cases.json --drafter mock:flawed --out reports/flawed.md
pae check  --cases examples/synthetic_cases.json --case-id PA-001 --letter my_letter.txt
pytest -q
```
`--strict` makes `run` exit 1 unless the decision is GO. Sample output:
[`examples/sample_report_flawed.md`](examples/sample_report_flawed.md) and
[`examples/sample_report_good.md`](examples/sample_report_good.md).

To evaluate a real model, either:

```bash
# Option A: OpenAI-compatible API (adapter present; no published scorecard yet)
pip install -e '.[openai]'
export OPENAI_API_KEY=sk-...          # required
# export OPENAI_BASE_URL=https://...  # optional compatible endpoint
pae run --cases examples/synthetic_cases.json --drafter openai --out reports/openai.md
# or: --drafter openai:gpt-4o-mini
```

```bash
# Option B: generate letters elsewhere, then score them offline
pae prompt --cases examples/synthetic_cases.json --case-id PA-001
# save each reply as DIR/<case id>.txt
pae run --cases examples/synthetic_cases.json --drafter files:DIR --out reports/files.md
```

**Do not publish fabricated pass rates.** A scorecard belongs only after real runs with a
real key; the adapter is wired for that, but this repo still ships mock-only sample reports.

## Letter format the checks expect
Sections `## Response to denial reason`, `## Clinical summary` (one `- ` bullet per clinical
assertion), `## Policy basis` and `## Enclosures`, plus `Date:`, `Patient: ... | Member ID: ...`,
`Requested service: CPT ... | Diagnosis: ICD-10 ...` header lines and a `Sincerely, ... NPI ...`
signature. See `src/prior_auth_eval/checks.py` for the contract.

## Limitations (read these)
- **Synthetic only.** The cases are formulaic and the seeded flaws were written by the same
  author as the checkers, so "25/25 matched" validates the plumbing, not real-world recall.
- **A floor, not a verdict.** A GO means the deterministic checks passed. It does not mean the
  letter is persuasive, complete, or clinically right. Human review is still required.
- **Literal by design.** The fact check is lexical (numbers, dates and vocabulary), so it can
  flag legitimate paraphrases and will miss fluent but wrong claims built from chart words.
  Negation flips are caught only when a cue word ("no", "denies", "negative", ...) sits
  shortly before the term in the same chart sentence. Only bullets in "Clinical summary" are checked.
- The extra-PHI check is a pattern floor, not a minimum-necessary review: it looks only for
  SSN, phone, email and street-address patterns that are not in the source material. It misses
  other identifiers (account numbers, free-text family details, unneeded diagnoses) and does
  not judge whether chart content that *is* present was needed.
- No judge model, no published real-model results, no payer-specific rules. An OpenAI-compatible drafter adapter is present for local runs when you have a key.
- **Not medical or legal advice.** Nothing here determines coverage or appeal strategy.

## Status
**Early, v0.1.** Schema, 25 synthetic cases, six checkers, mock / files / OpenAI-compatible
drafters, report, CLI and tests (all passing). **No published real-model results.**

## Roadmap
- ~~More cases with harder seeded flaws (negation flips, near-miss identifiers)~~ (done)
- ~~Grow to 25 synthetic cases~~ (done: 25 cases, including multi-criterion denials)
- Hand-written (non-template) cases and letters, so recall is not measured on the author's own
  templates
- Calibrated LLM-as-judge for persuasiveness and completeness, validated against human labels
  (see [judge-calibration-kit](https://github.com/ravinelango/judge-calibration-kit))
- ~~Minimum-necessary / extra-PHI check~~ (done: pattern-level `extra_phi`)
- OpenAI-compatible drafter adapter present (`openai` / `openai:MODEL`); published
  scorecard still blocked on real runs with a real key

## License
MIT © Ravin Elango
