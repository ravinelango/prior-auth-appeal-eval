"""Hand-written (non-template) cases: letters written as prose, not from the generator."""

import json
from pathlib import Path

import pytest

from prior_auth_eval.checks import CHECK_NAMES, run_checks
from prior_auth_eval.schema import load_cases

PATH = Path(__file__).parents[1] / "examples" / "handwritten_cases.json"
CASES = load_cases(PATH)
RAW = {c["id"]: c for c in json.loads(PATH.read_text())["cases"]}


def test_handwritten_set_is_synthetic_and_does_not_reuse_generated_ids():
    assert CASES.label.startswith("SYNTHETIC")
    generated = load_cases(PATH.with_name("synthetic_cases.json"))
    assert not {c.id for c in CASES.cases} & {c.id for c in generated.cases}
    for c in CASES.cases:
        assert c.chart.member_id.startswith("SYN-MBR-") and "SYNTHETIC" in c.denial.letter_text


@pytest.mark.parametrize("case", CASES.cases, ids=lambda c: c.id)
def test_good_handwritten_letter_passes(case):
    failed = [
        (r.name, r.findings)
        for r in run_checks(case, case.reference_drafts["good"].text)
        if not r.passed
    ]
    assert failed == []


@pytest.mark.parametrize("case", CASES.cases, ids=lambda c: c.id)
def test_flawed_handwritten_letter_fails_exactly_the_seeded_checks(case):
    flawed = case.reference_drafts["flawed"]
    failed = sorted(r.name for r in run_checks(case, flawed.text) if not r.passed)
    assert failed == sorted(flawed.seeded_flaws) and failed


def test_known_checker_gaps_are_still_missed():
    """Documents flaws the deterministic checks do not catch. If one starts failing, the gap
    was closed: move it into seeded_flaws. With no open gaps this passes instead of skipping."""
    for cid, raw in RAW.items():
        gaps = raw.get("known_checker_gaps", [])
        if not gaps:
            continue
        case = next(c for c in CASES.cases if c.id == cid)
        results = {r.name: r for r in run_checks(case, case.reference_drafts["flawed"].text)}
        for gap in gaps:
            assert gap["check"] in CHECK_NAMES, (cid, gap)
            assert results[gap["check"]].passed, (cid, gap["flaw"])
