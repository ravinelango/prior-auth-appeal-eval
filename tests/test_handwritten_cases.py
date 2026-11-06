"""Hand-written (non-template) cases: letters written as prose, not from the generator."""

import json
from pathlib import Path

import pytest

from prior_auth_eval.checks import CHECK_NAMES, run_checks
from prior_auth_eval.schema import load_cases, parse_case

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


def test_inflated_count_is_caught_even_when_another_fact_has_that_number():
    """PA-054 with F1 reworded to "every two weeks": the chart now contains a 2, so only the
    per-fact number check can see that the 2026-06-02 bullet's "two infusions" is wrong."""
    raw = json.loads(json.dumps(RAW["PA-054"]))
    old = "every other week"
    raw["chart"]["facts"][0]["text"] = raw["chart"]["facts"][0]["text"].replace(
        old, "every two weeks"
    )
    drafts = raw["reference_drafts"]
    for kind in ("good", "flawed"):
        drafts[kind]["text"] = drafts[kind]["text"].replace(old, "every two weeks")
    case = parse_case(raw)
    good = {r.name: r for r in run_checks(case, drafts["good"]["text"])}
    assert good["facts_in_chart"].passed
    flawed = {r.name: r for r in run_checks(case, drafts["flawed"]["text"])}["facts_in_chart"]
    assert not flawed.passed
    assert any("not in the matching chart fact" in f and "Two iron" in f for f in flawed.findings)


def test_loose_summary_inflated_count_is_caught_via_vocabulary_overlap():
    """Same reworded PA-054 chart as above, but the flawed bullet is a loose, undated summary.
    It falls below DATE_MATCH_MIN against any one fact, yet shares content words with the
    infiltration fact (which has "one", not "two"), so the inflated count is caught against
    that best-overlapping fact rather than the chart-wide "every two weeks" 2."""
    raw = json.loads(json.dumps(RAW["PA-054"]))
    raw["chart"]["facts"][0]["text"] = raw["chart"]["facts"][0]["text"].replace(
        "every other week", "every two weeks"
    )
    case = parse_case(raw)
    flawed = raw["reference_drafts"]["flawed"]["text"]
    old = next(line for line in flawed.splitlines() if line.startswith("- Two iron"))
    loose = "- Two infusions so far ended early after the IV infiltrated."
    results = {r.name: r for r in run_checks(case, flawed.replace(old, loose))}
    fic = results["facts_in_chart"]
    assert not fic.passed
    assert any("vocabulary-overlapping" in f and ("Two" in f or "2" in f) for f in fic.findings), (
        fic.findings
    )


def test_loose_summary_same_number_different_count_noun_is_caught():
    """A loose undated summary must not borrow a schedule fact's number for a different count noun.

    Chart F1 has "every three weeks" (a 3) and shares outpatient/clinic words with the bullet;
    F2 has one infiltrated infusion (and a separate "three attempts"). The flawed bullet claims
    three infiltrated infusions. Count-noun role matching rejects F1's weeks-3 and F2's
    attempts-3, so the inflation is flagged on the overlapping-fact path.
    """
    raw = json.loads(json.dumps(RAW["PA-054"]))
    raw["chart"]["facts"][0]["text"] = (
        "Iron deficiency anemia from chronic blood loss; oral iron stopped for intolerance and "
        "IV iron sucrose infusions continue every three weeks at the outpatient clinic for at "
        "least six months."
    )
    case = parse_case(raw)
    flawed = raw["reference_drafts"]["flawed"]["text"]
    old = next(line for line in flawed.splitlines() if line.startswith("- Two iron"))
    loose = (
        "- Three iron sucrose infusions at the outpatient clinic stopped early after the "
        "peripheral line infiltrated."
    )
    results = {r.name: r for r in run_checks(case, flawed.replace(old, loose))}
    fic = results["facts_in_chart"]
    assert not fic.passed
    assert any(
        "vocabulary-overlapping" in f and ("Three" in f or "3" in f) for f in fic.findings
    ), fic.findings
