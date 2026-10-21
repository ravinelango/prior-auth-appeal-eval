import pytest

from prior_auth_eval.schema import parse_case


def make_case_dict() -> dict:
    """A tiny hand-written SYNTHETIC case used across unit tests."""
    return {
        "id": "T-1",
        "title": "Synthetic test case",
        "denial": {
            "claim_id": "SYN-CLM-900001",
            "cpt": "72148",
            "icd10": "M54.16",
            "reason_code": "SYN-D01",
            "reason_text": "Not medically necessary",
            "unmet_criteria": ["SYN-LCD-9001-C2"],
            "reason_terms": ["physical therapy", "6 weeks"],
            "applicable_policy": "SYN-LCD-9001",
            "denial_date": "2026-03-02",
            "appeal_deadline": "2026-05-01",
            "letter_text": "Denied: criterion SYN-LCD-9001-C2 not met.",
        },
        "chart": {
            "patient_id": "P-1",
            "patient_name": "Pat Example",
            "dob": "1970-01-01",
            "member_id": "SYN-MBR-900001",
            "provider_name": "Dr. Sam Placeholder",
            "facts": [
                {
                    "id": "f1",
                    "date": "2026-01-05",
                    "text": "Low back pain radiating to the left leg since 2025-11-20.",
                },
                {
                    "id": "f2",
                    "date": "2026-02-23",
                    "text": "Completed 6 weeks of physical therapy (12 sessions); pain 7/10.",
                },
            ],
        },
        "policies": [
            {
                "id": "SYN-LCD-9001",
                "title": "Lumbar imaging (synthetic)",
                "criteria": [
                    {"id": "SYN-LCD-9001-C1", "text": "Radicular pain for at least 6 weeks."},
                    {"id": "SYN-LCD-9001-C2", "text": "Documented conservative therapy."},
                ],
            },
            {
                "id": "SYN-LCD-9002",
                "title": "Sleep testing (synthetic)",
                "criteria": [{"id": "SYN-LCD-9002-C1", "text": "Symptoms of sleep apnea."}],
            },
        ],
    }


@pytest.fixture
def case_dict():
    return make_case_dict()


@pytest.fixture
def case(case_dict):
    return parse_case(case_dict)


GOOD_LETTER = """Date: 2026-03-20
RE: Appeal of denial, claim SYN-CLM-900001 (SYNTHETIC)
Patient: Pat Example | Member ID: SYN-MBR-900001 | DOB: 1970-01-01
Requested service: CPT 72148 | Diagnosis: ICD-10 M54.16

## Response to denial reason
The plan denied this request under SYN-D01 (Not medically necessary), stating that
SYN-LCD-9001-C2 is not met. The chart documents 6 weeks of physical therapy without relief.

## Clinical summary
- Low back pain radiating to the left leg since 2025-11-20.
- Completed 6 weeks of physical therapy (12 sessions); pain 7/10.

## Policy basis
Under SYN-LCD-9001 (Lumbar imaging), criteria SYN-LCD-9001-C1 and SYN-LCD-9001-C2 apply.
We request that the denial be overturned.

## Enclosures
- Chart notes 2026-01-05 and 2026-02-23

Sincerely,
Dr. Sam Placeholder, NPI SYN-0000
"""


@pytest.fixture
def good_letter():
    return GOOD_LETTER
