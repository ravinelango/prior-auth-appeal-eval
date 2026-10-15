# Prior-auth appeal evaluation report

- Dataset: `synthetic_cases.json` (15 cases)
- Drafter: `mock:good`
- Generated: 2026-10-15 14:24 UTC

> **Synthetic demo.** Cases are invented and the mock drafter replays fixed reference letters, so this report shows the format and that the checkers fire on seeded flaws. It is not a measurement of any model.

## Decision: **GO**

_Deterministic checks are a floor, not a replacement for human review. A GO does not mean the letters are good. Not medical or legal advice._

## Failures by check

| Check | Severity | Cases failed |
|---|---|---|
| citations | critical | 0/15 |
| facts_in_chart | critical | 0/15 |
| denial_reason_addressed | critical | 0/15 |
| identifiers_match | critical | 0/15 |
| required_elements | major | 0/15 |

## Per-case results

| Case | Service | citations | facts_in_chart | denial_reason_addressed | identifiers_match | required_elements | Status |
|---|---|---|---|---|---|---|---|
| PA-001 | CPT 72148 | pass | pass | pass | pass | pass | PASS |
| PA-002 | CPT 95810 | pass | pass | pass | pass | pass | PASS |
| PA-003 | CPT 27447 | pass | pass | pass | pass | pass | PASS |
| PA-004 | CPT 64483 | pass | pass | pass | pass | pass | PASS |
| PA-005 | CPT 78452 | pass | pass | pass | pass | pass | PASS |
| PA-006 | CPT 70553 | pass | pass | pass | pass | pass | PASS |
| PA-007 | CPT 71250 | pass | pass | pass | pass | pass | PASS |
| PA-008 | CPT 45378 | pass | pass | pass | pass | pass | PASS |
| PA-009 | CPT 93306 | pass | pass | pass | pass | pass | PASS |
| PA-010 | CPT 29881 | pass | pass | pass | pass | pass | PASS |
| PA-011 | CPT 73221 | pass | pass | pass | pass | pass | PASS |
| PA-012 | CPT 93798 | pass | pass | pass | pass | pass | PASS |
| PA-013 | CPT 43239 | pass | pass | pass | pass | pass | PASS |
| PA-014 | CPT 72141 | pass | pass | pass | pass | pass | PASS |
| PA-015 | CPT 94760 | pass | pass | pass | pass | pass | PASS |

## Findings

No findings.
## Checker validation (seeded flaws, mock drafter only)

| Case | Seeded flaws | Checks that failed | Match |
|---|---|---|---|
| PA-001 | - | - | yes |
| PA-002 | - | - | yes |
| PA-003 | - | - | yes |
| PA-004 | - | - | yes |
| PA-005 | - | - | yes |
| PA-006 | - | - | yes |
| PA-007 | - | - | yes |
| PA-008 | - | - | yes |
| PA-009 | - | - | yes |
| PA-010 | - | - | yes |
| PA-011 | - | - | yes |
| PA-012 | - | - | yes |
| PA-013 | - | - | yes |
| PA-014 | - | - | yes |
| PA-015 | - | - | yes |

15/15 cases matched. This validates the checkers against flaws written by the same author; it says nothing about real model output.
