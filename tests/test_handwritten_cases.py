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


def _known_fps(cid: str, draft: str) -> list[dict]:
    return [fp for fp in RAW[cid].get("known_false_positives", []) if fp["draft"] == draft]


def _is_known_fp(cid: str, draft: str, check: str, finding: str) -> bool:
    return any(
        fp["check"] == check and fp["finding_contains"] in finding for fp in _known_fps(cid, draft)
    )


@pytest.mark.parametrize("case", CASES.cases, ids=lambda c: c.id)
def test_good_handwritten_letter_passes(case):
    """Passes apart from documented false positives (see known_false_positives)."""
    failed = [
        (r.name, f)
        for r in run_checks(case, case.reference_drafts["good"].text)
        for f in r.findings
        if not r.passed and not _is_known_fp(case.id, "good", r.name, f)
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


def test_known_false_positives_still_fire():
    """Documents correct letters the heuristics wrongly flag. If one stops firing, a check got
    more precise: drop the entry. Keeps the false-positive cost of each heuristic visible."""
    for cid, raw in RAW.items():
        case = next(c for c in CASES.cases if c.id == cid)
        for fp in raw.get("known_false_positives", []):
            assert fp["check"] in CHECK_NAMES, (cid, fp)
            results = {r.name: r for r in run_checks(case, case.reference_drafts[fp["draft"]].text)}
            hits = [f for f in results[fp["check"]].findings if fp["finding_contains"] in f]
            assert hits, (cid, fp["flaw"])
