# Prior-auth appeal evaluation report

- Dataset: `synthetic_cases.json` (10 cases)
- Drafter: `mock:flawed`
- Generated: 2026-10-15 12:51 UTC

> **Synthetic demo.** Cases are invented and the mock drafter replays fixed reference letters, so this report shows the format and that the checkers fire on seeded flaws. It is not a measurement of any model.

## Decision: **NO-GO**

- PA-001: citations failed
- PA-002: citations failed
- PA-003: facts_in_chart failed
- PA-004: facts_in_chart failed
- PA-005: denial_reason_addressed failed
- PA-006: denial_reason_addressed failed
- PA-007: identifiers_match failed
- PA-008: identifiers_match failed
- PA-010: identifiers_match failed

_Deterministic checks are a floor, not a replacement for human review. A GO does not mean the letters are good. Not medical or legal advice._

## Failures by check

| Check | Severity | Cases failed |
|---|---|---|
| citations | critical | 2/10 |
| facts_in_chart | critical | 2/10 |
| denial_reason_addressed | critical | 2/10 |
| identifiers_match | critical | 3/10 |
| required_elements | major | 2/10 |

## Per-case results

| Case | Service | citations | facts_in_chart | denial_reason_addressed | identifiers_match | required_elements | Status |
|---|---|---|---|---|---|---|---|
| PA-001 | CPT 72148 | FAIL | pass | pass | pass | pass | FAIL |
| PA-002 | CPT 95810 | FAIL | pass | pass | pass | pass | FAIL |
| PA-003 | CPT 27447 | pass | FAIL | pass | pass | pass | FAIL |
| PA-004 | CPT 64483 | pass | FAIL | pass | pass | pass | FAIL |
| PA-005 | CPT 78452 | pass | pass | FAIL | pass | pass | FAIL |
| PA-006 | CPT 70553 | pass | pass | FAIL | pass | pass | FAIL |
| PA-007 | CPT 71250 | pass | pass | pass | FAIL | pass | FAIL |
| PA-008 | CPT 45378 | pass | pass | pass | FAIL | pass | FAIL |
| PA-009 | CPT 93306 | pass | pass | pass | pass | FAIL | FAIL (minor) |
| PA-010 | CPT 29881 | pass | pass | pass | FAIL | FAIL | FAIL |

## Findings

### PA-001: Lumbar spine MRI: citation invented (synthetic)
- **citations** (critical)
  - cites policy LCD-L99999, which is not in the provided policy set

### PA-002: Attended sleep study: citation wrong policy (synthetic)
- **citations** (critical)
  - cites SYN-LCD-1003, which exists but does not govern this denial (SYN-LCD-1002)

### PA-003: Total knee replacement: fact numeric (synthetic)
- **facts_in_chart** (critical)
  - number(s) not in chart ['26']: "Completed 26 weeks of supervised physical therapy (2026-02-10)."

### PA-004: Lumbar epidural steroid injection: fact nonnumeric (synthetic)
- **facts_in_chart** (critical)
  - term(s) not in chart ['hardware', 'lumbar', 'prior', 'retained', 'surgery']: "Documented history of prior lumbar surgery with retained hardware (2026-02-03)."

### PA-005: Myocardial perfusion imaging: reason unaddressed (synthetic)
- **denial_reason_addressed** (critical)
  - response does not cite the unmet criterion SYN-LCD-1005-C2
  - response engages with 0/2 expected terms (missing: ['unable to exercise', 'ECG'])

### PA-006: Brain MRI after first seizure: criterion not cited (synthetic)
- **denial_reason_addressed** (critical)
  - response does not cite the unmet criterion SYN-LCD-1006-C1

### PA-007: Follow-up chest CT: wrong member (synthetic)
- **identifiers_match** (critical)
  - member_id is SYN-MBR-300114, expected SYN-MBR-300107

### PA-008: Diagnostic colonoscopy: wrong cpt (synthetic)
- **identifiers_match** (critical)
  - cpt is 45380, expected 45378

### PA-009: Transthoracic echocardiogram: missing elements (synthetic)
- **required_elements** (major)
  - no '## Enclosures' list
  - no signature block with provider NPI

### PA-010: Knee arthroscopy: late and incomplete (synthetic)
- **identifiers_match** (critical)
  - icd10 is M23.222, expected M23.221
- **required_elements** (major)
  - no explicit request to overturn/reverse the denial
  - letter dated 2026-05-20 is after the appeal deadline 2026-05-11

## Checker validation (seeded flaws, mock drafter only)

| Case | Seeded flaws | Checks that failed | Match |
|---|---|---|---|
| PA-001 | citations | citations | yes |
| PA-002 | citations | citations | yes |
| PA-003 | facts_in_chart | facts_in_chart | yes |
| PA-004 | facts_in_chart | facts_in_chart | yes |
| PA-005 | denial_reason_addressed | denial_reason_addressed | yes |
| PA-006 | denial_reason_addressed | denial_reason_addressed | yes |
| PA-007 | identifiers_match | identifiers_match | yes |
| PA-008 | identifiers_match | identifiers_match | yes |
| PA-009 | required_elements | required_elements | yes |
| PA-010 | identifiers_match, required_elements | identifiers_match, required_elements | yes |

10/10 cases matched. This validates the checkers against flaws written by the same author; it says nothing about real model output.
