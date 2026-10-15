# Prior-auth appeal evaluation report

- Dataset: `synthetic_cases.json` (10 cases)
- Drafter: `mock:good`
- Generated: 2026-10-15 12:51 UTC

> **Synthetic demo.** Cases are invented and the mock drafter replays fixed reference letters, so this report shows the format and that the checkers fire on seeded flaws. It is not a measurement of any model.

## Decision: **GO**

_Deterministic checks are a floor, not a replacement for human review. A GO does not mean the letters are good. Not medical or legal advice._

## Failures by check

| Check | Severity | Cases failed |
|---|---|---|
| citations | critical | 0/10 |
| facts_in_chart | critical | 0/10 |
| denial_reason_addressed | critical | 0/10 |
| identifiers_match | critical | 0/10 |
| required_elements | major | 0/10 |

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

10/10 cases matched. This validates the checkers against flaws written by the same author; it says nothing about real model output.
