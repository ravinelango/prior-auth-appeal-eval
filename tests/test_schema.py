import json

import pytest

from prior_auth_eval.schema import load_cases, parse_case


def test_parse_case_ok(case):
    assert case.denial.applicable_policy == "SYN-LCD-9001"
    assert case.policy("SYN-LCD-9002").title.startswith("Sleep")
    assert "SYN-LCD-9001-C2" in case.criterion_ids()


def test_missing_field_is_reported(case_dict):
    del case_dict["denial"]["reason_code"]
    with pytest.raises(ValueError, match="reason_code"):
        parse_case(case_dict)


def test_applicable_policy_must_be_in_set(case_dict):
    case_dict["denial"]["applicable_policy"] = "SYN-LCD-0000"
    with pytest.raises(ValueError, match="applicable_policy"):
        parse_case(case_dict)


def test_unmet_criteria_must_exist(case_dict):
    case_dict["denial"]["unmet_criteria"] = ["SYN-LCD-9001-C7"]
    with pytest.raises(ValueError, match="unmet criteria"):
        parse_case(case_dict)


def test_duplicate_ids(tmp_path, case_dict):
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"cases": [case_dict, case_dict]}))
    with pytest.raises(ValueError, match="duplicate"):
        load_cases(p)


def test_reference_drafts_loaded(tmp_path, case_dict):
    case_dict["reference_drafts"] = {"flawed": {"text": "x", "seeded_flaws": ["citation"]}}
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"label": "SYNTHETIC", "cases": [case_dict]}))
    cs = load_cases(p)
    assert cs.label == "SYNTHETIC"
    assert cs.cases[0].reference_drafts["flawed"].seeded_flaws == ("citation",)
