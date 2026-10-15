# Prior-auth appeal evaluation report

- Dataset: `synthetic_cases.json` (25 cases)
- Drafter: `mock:flawed`
- Generated: 2026-10-15 19:53 UTC

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
- PA-011: facts_in_chart failed
- PA-012: identifiers_match failed
- PA-013: identifiers_match failed
- PA-014: identifiers_match failed
- PA-015: facts_in_chart failed
- PA-016: citations failed
- PA-017: identifiers_match failed
- PA-018: facts_in_chart failed
- PA-019: denial_reason_addressed failed
- PA-021: denial_reason_addressed failed
- PA-022: citations failed
- PA-024: identifiers_match failed

_Deterministic checks are a floor, not a replacement for human review. A GO does not mean the letters are good. Not medical or legal advice._

## Failures by check

| Check | Severity | Cases failed |
|---|---|---|
| citations | critical | 4/25 |
| facts_in_chart | critical | 5/25 |
| denial_reason_addressed | critical | 4/25 |
| identifiers_match | critical | 8/25 |
| required_elements | major | 4/25 |
| extra_phi | major | 1/25 |

## Per-case results

| Case | Service | citations | facts_in_chart | denial_reason_addressed | identifiers_match | required_elements | extra_phi | Status |
|---|---|---|---|---|---|---|---|---|
| PA-001 | CPT 72148 | FAIL | pass | pass | pass | pass | pass | FAIL |
| PA-002 | CPT 95810 | FAIL | pass | pass | pass | pass | pass | FAIL |
| PA-003 | CPT 27447 | pass | FAIL | pass | pass | pass | pass | FAIL |
| PA-004 | CPT 64483 | pass | FAIL | pass | pass | pass | pass | FAIL |
| PA-005 | CPT 78452 | pass | pass | FAIL | pass | pass | pass | FAIL |
| PA-006 | CPT 70553 | pass | pass | FAIL | pass | pass | pass | FAIL |
| PA-007 | CPT 71250 | pass | pass | pass | FAIL | pass | pass | FAIL |
| PA-008 | CPT 45378 | pass | pass | pass | FAIL | pass | pass | FAIL |
| PA-009 | CPT 93306 | pass | pass | pass | pass | FAIL | pass | FAIL (minor) |
| PA-010 | CPT 29881 | pass | pass | pass | FAIL | FAIL | pass | FAIL |
| PA-011 | CPT 73221 | pass | FAIL | pass | pass | pass | pass | FAIL |
| PA-012 | CPT 93798 | pass | pass | pass | FAIL | pass | pass | FAIL |
| PA-013 | CPT 43239 | pass | pass | pass | FAIL | pass | pass | FAIL |
| PA-014 | CPT 72141 | pass | pass | pass | FAIL | pass | pass | FAIL |
| PA-015 | CPT 94760 | pass | FAIL | pass | pass | pass | pass | FAIL |
| PA-016 | CPT 73721 | FAIL | pass | pass | pass | pass | pass | FAIL |
| PA-017 | CPT 94010 | pass | pass | pass | FAIL | pass | pass | FAIL |
| PA-018 | CPT 93880 | pass | FAIL | pass | pass | pass | pass | FAIL |
| PA-019 | CPT 77080 | pass | pass | FAIL | pass | pass | pass | FAIL |
| PA-020 | CPT 93970 | pass | pass | pass | pass | FAIL | pass | FAIL (minor) |
| PA-021 | CPT 66984 | pass | pass | FAIL | pass | pass | pass | FAIL |
| PA-022 | CPT 78815 | FAIL | pass | pass | pass | pass | pass | FAIL |
| PA-023 | CPT 95165 | pass | pass | pass | pass | pass | FAIL | FAIL (minor) |
| PA-024 | CPT 97605 | pass | pass | pass | FAIL | pass | pass | FAIL |
| PA-025 | CPT 95811 | pass | pass | pass | pass | FAIL | pass | FAIL (minor) |

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

### PA-011: Left shoulder MRI: negation flip (synthetic)
- **facts_in_chart** (critical)
  - possible negation flip of chart-negated term(s) ['anticoagulants', 'cardiac', 'device', 'implanted']: "Currently on anticoagulants and has an implanted cardiac device (2026-01-15)."

### PA-012: Outpatient cardiac rehab: near miss member (synthetic)
- **identifiers_match** (critical)
  - member_id is SYN-MBR-300113, expected SYN-MBR-300112

### PA-013: Upper endoscopy: near miss cpt (synthetic)
- **identifiers_match** (critical)
  - cpt is 43240, expected 43239

### PA-014: Cervical spine MRI: swapped icd (synthetic)
- **identifiers_match** (critical)
  - icd10 is M54.13, expected M54.12

### PA-015: Home oxygen evaluation: paraphrase flip (synthetic)
- **facts_in_chart** (critical)
  - number(s) not in chart ['96']: "Resting SpO2 improved to 96 percent on room air after the recent exacerbation (2026-02-10)."

### PA-016: Right hip MRI: citation bad criterion (synthetic)
- **citations** (critical)
  - cites criterion SYN-LCD-1016-C4, which does not exist in SYN-LCD-1016

### PA-017: Spirometry: wrong patient name (synthetic)
- **identifiers_match** (critical)
  - patient_name is Riley Mockson, expected Quinn Mockdata

### PA-018: Carotid duplex ultrasound: date shift (synthetic)
- **facts_in_chart** (critical)
  - number(s) not in chart ['2026-01-25']: "Earlier transient episode of right hand weakness (2026-01-25)."

### PA-019: Bone density scan: reason terms missing (synthetic)
- **denial_reason_addressed** (critical)
  - response engages with 0/2 expected terms (missing: ['glucocorticoid', 'prednisone'])

### PA-020: Lower extremity venous duplex: late filing (synthetic)
- **required_elements** (major)
  - letter dated 2026-05-24 is after the appeal deadline 2026-05-21

### PA-021: Cataract surgery, right eye: multiple unmet (synthetic)
- **denial_reason_addressed** (critical)
  - response does not cite the unmet criterion SYN-LCD-1021-C2

### PA-022: PET/CT for lymphoma restaging: citation real looking ncd (synthetic)
- **citations** (critical)
  - cites policy NCD-220.6.17, which is not in the provided policy set

### PA-023: Allergen immunotherapy: extra phi ssn (synthetic)
- **extra_phi** (major)
  - SSN '900-00-0023' is not in the chart or denial letter (minimum necessary)

### PA-024: Negative pressure wound therapy: near miss claim (synthetic)
- **identifiers_match** (critical)
  - claim_id is SYN-CLM-200125, expected SYN-CLM-200124

### PA-025: CPAP titration study: missing overturn request (synthetic)
- **required_elements** (major)
  - no explicit request to overturn/reverse the denial

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
| PA-011 | facts_in_chart | facts_in_chart | yes |
| PA-012 | identifiers_match | identifiers_match | yes |
| PA-013 | identifiers_match | identifiers_match | yes |
| PA-014 | identifiers_match | identifiers_match | yes |
| PA-015 | facts_in_chart | facts_in_chart | yes |
| PA-016 | citations | citations | yes |
| PA-017 | identifiers_match | identifiers_match | yes |
| PA-018 | facts_in_chart | facts_in_chart | yes |
| PA-019 | denial_reason_addressed | denial_reason_addressed | yes |
| PA-020 | required_elements | required_elements | yes |
| PA-021 | denial_reason_addressed | denial_reason_addressed | yes |
| PA-022 | citations | citations | yes |
| PA-023 | extra_phi | extra_phi | yes |
| PA-024 | identifiers_match | identifiers_match | yes |
| PA-025 | required_elements | required_elements | yes |

25/25 cases matched. This validates the checkers against flaws written by the same author; it says nothing about real model output.
