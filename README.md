# prior-auth-appeal-eval

Work in progress. An eval suite for LLM-drafted prior-authorization appeal letters.

**Use case:** a provider revenue-cycle team uses an LLM to draft an appeal after a payer
denies a prior-authorization request. Before a human signs it, the draft should be checked for
the failures that get appeals rejected or create compliance risk:

- citing a coverage policy or criterion that is not in the policy set (invented citations)
- stating clinical facts that are not in the chart excerpt
- not addressing the specific denial reason
- wrong patient, member ID, CPT, or ICD-10 code
- missing required elements of the appeal

**Data:** every patient, chart excerpt, denial, and policy in `cases/` is **synthetic** and made
up for testing. No real patient data. Policies are labeled `SYN-` and are not real payer or
Medicare coverage documents.

## Case schema

Each case is one JSON file with:

| field | meaning |
| --- | --- |
| `case_id` | stable id, e.g. `PA-001` |
| `synthetic` | must be `true` |
| `patient` | synthetic name, DOB, member ID |
| `request` | requested CPT/HCPCS and ICD-10 codes |
| `denial` | denial reason code and text, and the policy it cites |
| `chart_facts` | atomic facts from the chart, each with an id (`F1`, `F2`, ...) |
| `policy_ids` | policies the appeal may cite (must exist in `cases/policies.json`) |
| `required_elements` | items the appeal must contain |

Status: case schema and loader. Deterministic checks, a mock drafter, and the report are next.
