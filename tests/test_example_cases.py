import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from prior_auth_eval.checks import CHECK_NAMES, run_checks
from prior_auth_eval.schema import load_cases

ROOT = Path(__file__).parents[1]
CASES = load_cases(ROOT / "examples" / "synthetic_cases.json")


def test_dataset_is_labeled_synthetic_and_sized():
    assert CASES.label.startswith("SYNTHETIC")
    assert len(CASES.cases) == 25
    for c in CASES.cases:
        assert c.chart.member_id.startswith("SYN-MBR-") and c.denial.claim_id.startswith("SYN-CLM-")
        assert all(p.id.startswith("SYN-") and "(synthetic)" in p.title for p in c.policies)
        assert "SYNTHETIC" in c.denial.letter_text


@pytest.mark.parametrize("case", CASES.cases, ids=lambda c: c.id)
def test_good_reference_draft_passes_all_checks(case):
    failed = [(r.name, r.findings) for r in run_checks(case, case.reference_drafts["good"].text)
              if not r.passed]
    assert failed == []


@pytest.mark.parametrize("case", CASES.cases, ids=lambda c: c.id)
def test_flawed_reference_draft_fails_exactly_the_seeded_checks(case):
    flawed = case.reference_drafts["flawed"]
    failed = sorted(r.name for r in run_checks(case, flawed.text) if not r.passed)
    assert failed == sorted(flawed.seeded_flaws) and failed


def test_every_failure_mode_is_covered_at_least_once():
    seeded = {f for c in CASES.cases for f in c.reference_drafts["flawed"].seeded_flaws}
    assert seeded == set(CHECK_NAMES)


def test_multi_unmet_case_names_both_criteria_and_flaw_answers_one():
    case = next(c for c in CASES.cases if c.id == "PA-021")
    assert len(case.denial.unmet_criteria) == 2
    assert all(u in case.denial.letter_text for u in case.denial.unmet_criteria)
    flawed = case.reference_drafts["flawed"].text
    assert case.denial.unmet_criteria[0] in flawed
    (r,) = [r for r in run_checks(case, flawed) if r.name == "denial_reason_addressed"]
    assert r.findings == [f"response does not cite the unmet criterion "
                          f"{case.denial.unmet_criteria[1]}"]


def test_no_real_looking_policy_ids_in_provided_sets():
    for c in CASES.cases:
        text = json.dumps([p.id for p in c.policies])
        assert not re.search(r"\b(?:LCD|NCD)[- ]?L?\d", text.replace("SYN-LCD-", ""))


def test_committed_dataset_matches_generator():
    out = subprocess.run([sys.executable, str(ROOT / "scripts" / "build_example_cases.py")],
                         capture_output=True, text=True, check=True).stdout
    assert json.loads(out) == json.loads((ROOT / "examples" / "synthetic_cases.json").read_text())
