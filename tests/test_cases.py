from pathlib import Path

from prior_auth_appeal_eval.schema import load_cases, load_policies

CASES = Path(__file__).resolve().parents[1] / "cases"


def test_all_cases_load_and_reference_known_policies():
    cases = load_cases(CASES)
    assert [c.case_id for c in cases] == ["PA-001", "PA-002", "PA-003"]


def test_policies_are_labeled_synthetic():
    policies = load_policies(CASES / "policies.json")
    assert all(pid.startswith("SYN-") for pid in policies)
    assert all("(synthetic)" in p["title"] for p in policies.values())
