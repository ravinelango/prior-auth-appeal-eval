# prior-auth-appeal-eval

[![CI](https://github.com/ravinelango/prior-auth-appeal-eval/actions/workflows/ci.yml/badge.svg)](https://github.com/ravinelango/prior-auth-appeal-eval/actions/workflows/ci.yml)
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
| Clinical fact not in the chart | `facts_in_chart` | critical | Each bullet under "Clinical summary": every number and date must appear in the chart, family-relationship and laterality words (mother, sister, left, right...) must appear in the chart, and the share of content words absent from the chart must be small |
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
   `examples/handwritten_cases.json` adds PA-026..PA-043, written by hand as prose letters
   instead of from the templates: an invented diet history, a letter that argues the wrong
   criterion and adds a phone number, and a near-miss CPT code. PA-028 also swaps "Mother"
   for "Sister" in the family history. The first version of `facts_in_chart` missed that (one
   changed word stays under the unseen-term ratio), so relationship and laterality words are
   now pinned to the chart. Any future miss goes under `known_checker_gaps`, and a test keeps
   it visible until a check closes it. PA-029 (lumbar MRI) was the first: the flawed letter
   is filed after the appeal deadline (caught by `required_elements`) and also says an
   epidural injection was already given when the chart only plans one. Every word of that
   claim is in the chart, so the lexical check passed it. `facts_in_chart` now tracks terms
   the chart mentions only after a planning cue ("planned", "possible", "requested",
   "scheduled", ...) and flags a bullet that states them outside such a cue, which closed the
   gap. It is still a word-window heuristic, not a parser of clinical tense. PA-030 (upper
   endoscopy) was the second: the flawed letter cites a criterion the policy does not have
   (caught by `citations`) and also moves the omeprazole start date to the day the endoscopy
   was requested, so the 8-week PPI trial reads as if it had just begun. That date is a real
   chart date and every word is in the chart, so the per-bullet check passed it.
   `facts_in_chart` now matches each dated bullet to the chart fact it most closely
   paraphrases (word overlap) and flags it when the bullet's date belongs to a different
   fact, which closed the gap. A bullet that blends several facts falls under the overlap
   threshold and is not date-checked. PA-031 (knee MRI) is the third: the flawed letter
   miscodes the diagnosis (caught by `identifiers_match`) and also says "nine weeks" of
   conservative therapy where the chart says 7, which overstates the very criterion the
   denial is about. The number check used to read digits only, so it passed. It now also
   reads spelled-out numbers (zero to twenty and the round tens) when a unit follows them
   ("nine weeks", "two visits"), so "one of the criteria" is not read as 1. That closed the
   gap. PA-032 (in-lab sleep study) is the fourth: the flawed letter cites a criterion the
   policy does not have (caught by `citations`) and also drops "suspected" from the chart's
   "suspected obstructive sleep apnea", so a working diagnosis reads as established. Every
   word is still in the chart, so the per-bullet check passed it. `facts_in_chart` now
   collects terms the chart mentions only after a hedge cue ("suspected", "probable",
   "rule out", "concern for", ...) and flags a bullet that states them with no hedge in
   front, which closed the gap. Any hedge word counts, so "probable" for "suspected" passes.
   PA-033 (lumbar MRI) is the fifth: the flawed letter misdates a physical therapy bullet
   (caught by `facts_in_chart`) and also says SYN-LCD-3110-C3 is met when the chart records
   no neurologic deficit and no planned surgery or injection. The criterion id is real and
   the claim sits in the policy basis, so no check read it. `citations` now takes each
   criterion the policy basis calls met and looks for any of its terms in the chart (4-letter
   prefixes plus acronyms such as BMI, ignoring words from the policy title that only name
   the service). None of C3's terms appear, so it is flagged, which closed the gap. This is a
   loose keyword floor: one shared word counts as support, and a chart that backs a criterion
   only in other words would be flagged. PA-034 (continuous glucose monitor) measured that
   cost: its good letter says the diabetes self-management education criterion is met, and
   the chart backs it only as "a 4-session class with the clinic's diabetes teacher". No
   criterion term appeared, so `citations` flagged a correct letter. A short synonym list
   (`_CRIT_SYNONYMS`; for now only education, teacher, class, course, instruction) now lets
   a chart word stand in for the criterion's word, which cleared it; each entry also widens
   what counts as support, so the list stays small. `test_synonym_list_can_hide_an_overstated_education_criterion` pins that cost: a chart
   that only says the patient works as a teacher lets a letter call an education criterion met. Misfires like this are listed under
   `known_false_positives` in the case file; the good-letter test tolerates exactly those
   findings, and a second test fails once a fix stops them firing, so the entry gets
   removed (PA-034's list is now empty). (The flawed PA-034 letter inflates the
   hypoglycemia count, caught by `facts_in_chart`.) PA-035 (lumbar MRI) has the flawed letter inflate a spelled-out count
   ("twelve physical therapy sessions", chart: eight), which `facts_in_chart` reads as 12.
   PA-036 (shoulder MRI) has the flawed letter add a patient email address that is in
   neither the chart nor the denial (caught by `extra_phi`) and drop the enclosures list
   (caught by `required_elements`). PA-037 (cervical spine MRI) has the flawed letter move the
   reflex and weakness findings from the left arm to the right, which `facts_in_chart` catches
   because laterality words are pinned to the chart. PA-038 (brain MRI for headache) has the
   flawed letter claim "prior brain imaging was unremarkable" when the chart says there was no
   prior brain imaging; `facts_in_chart` flags it as a negation flip. PA-039 (total knee
   replacement) is denied on two criteria, and the flawed letter answers only the conservative
   treatment one; `denial_reason_addressed` flags the x-ray criterion it never mentions.
   PA-040 (cardiac rehabilitation) keeps the header correct but transposes two digits of the
   member ID in the body, so only `identifiers_match` fails: every ID mention is checked, not
   just the first. PA-041 (pulmonary rehabilitation) has the flawed letter call a third
   criterion, SYN-LCD-7150-C3, met when the policy only has two; `citations` is the only check
   that fails. PA-042 (home sleep apnea test) adds a street address line to the
   flawed letter's header; only `extra_phi` fails. PA-043 (bone density scan) drops the
   `## Enclosures` list from an otherwise correct letter; only `required_elements` fails.
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
**Early, v0.1.** Schema, 43 synthetic cases (25 generated, 18 hand-written), six checkers, mock / files / OpenAI-compatible
drafters, report, CLI and tests (all passing). **No published real-model results.**

## Roadmap
- ~~More cases with harder seeded flaws (negation flips, near-miss identifiers)~~ (done)
- ~~Grow to 25 synthetic cases~~ (done: 25 cases, including multi-criterion denials)
- Hand-written (non-template) cases and letters, so recall is not measured on the author's own
  templates (started: PA-026..PA-043; more needed)
- Calibrated LLM-as-judge for persuasiveness and completeness, validated against human labels
  (see [judge-calibration-kit](https://github.com/ravinelango/judge-calibration-kit))
- ~~Minimum-necessary / extra-PHI check~~ (done: pattern-level `extra_phi`)
- OpenAI-compatible drafter adapter present (`openai` / `openai:MODEL`); published
  scorecard still blocked on real runs with a real key

## License
MIT © Ravin Elango
