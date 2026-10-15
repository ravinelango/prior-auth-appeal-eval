import copy

import pytest

from prior_auth_appeal_eval.schema import CaseError, parse_case

BASE = {
    "case_id": "PA-900",
    "synthetic": True,
    "patient": {"name": "Test Patient", "dob": "1970-01-01", "member_id": "SYN000"},
    "request": {"cpt": ["00000"], "icd10": ["Z00.00"]},
    "denial": {"reason_code": "MN", "reason_text": "test", "cited_policy": "SYN-POL-1"},
    "chart_facts": [{"id": "F1", "text": "fact one"}, {"id": "F2", "text": "fact two"}],
    "policy_ids": ["SYN-POL-1"],
    "required_elements": ["member_id"],
}


def test_parses_valid_case():
    case = parse_case(copy.deepcopy(BASE))
    assert case.case_id == "PA-900"
    assert case.fact("F2").text == "fact two"
    assert case.fact("F9") is None


@pytest.mark.parametrize(
    "mutate, msg",
    [
        (lambda d: d.pop("denial"), "missing keys"),
        (lambda d: d.update(synthetic=False), "synthetic"),
        (lambda d: d.update(case_id="X-1"), "case_id"),
        (lambda d: d["chart_facts"].append({"id": "F1", "text": "dup"}), "unique"),
        (lambda d: d["denial"].update(cited_policy="SYN-POL-404"), "cited_policy"),
    ],
)
def test_rejects_bad_case(mutate, msg):
    data = copy.deepcopy(BASE)
    mutate(data)
    with pytest.raises(CaseError, match=msg):
        parse_case(data)
