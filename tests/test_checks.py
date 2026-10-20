import pytest

from prior_auth_eval.checks import (
    check_citations,
    check_denial_reason,
    check_extra_phi,
    check_facts,
    check_identifiers,
    check_required_elements,
    extract_citations,
    extract_identifiers,
    run_checks,
    sections,
)
from prior_auth_eval.schema import parse_case


def test_good_letter_passes_everything(case, good_letter):
    results = run_checks(case, good_letter)
    assert [r.name for r in results] == [
        "citations", "facts_in_chart", "denial_reason_addressed", "identifiers_match",
        "required_elements", "extra_phi"]
    assert all(r.passed for r in results), [(r.name, r.findings) for r in results if not r.passed]


# ---- citations
def test_extract_citations_normalizes():
    assert extract_citations("see LCD L99999 and syn-lcd-9001-c2") == [
        ("LCD-L99999", None), ("SYN-LCD-9001", "SYN-LCD-9001-C2")]


def test_invented_policy_is_flagged(case, good_letter):
    bad = good_letter.replace("SYN-LCD-9001", "LCD L99999")
    r = check_citations(case, bad)
    assert not r.passed
    assert any("LCD-L99999" in f and "not in the provided" in f for f in r.findings)


def test_wrong_but_existing_policy_is_flagged(case, good_letter):
    bad = good_letter.replace("SYN-LCD-9001", "SYN-LCD-9002")
    r = check_citations(case, bad)
    assert any("does not govern" in f for f in r.findings)


def test_nonexistent_criterion_is_flagged(case, good_letter):
    r = check_citations(case, good_letter + "\nAlso SYN-LCD-9001-C9 applies.")
    assert any("C9" in f for f in r.findings)


def test_missing_governing_policy_is_flagged(case):
    r = check_citations(case, "No policy is mentioned here.")
    assert any("never cites" in f for f in r.findings)


# ---- facts
def test_invented_number_is_flagged(case, good_letter):
    bad = good_letter.replace("6 weeks of physical therapy (12 sessions)",
                              "9 weeks of physical therapy (12 sessions)")
    r = check_facts(case, bad)
    assert not r.passed and "9" in r.findings[0]


def test_spelled_out_number_is_checked_against_chart(case, good_letter):
    ok = good_letter.replace("6 weeks of physical therapy", "six weeks of physical therapy")
    assert check_facts(case, ok).passed
    bad = good_letter.replace("6 weeks of physical therapy", "nine weeks of physical therapy")
    r = check_facts(case, bad)
    assert not r.passed and "'9'" in r.findings[0]


def test_spelled_out_word_without_a_unit_is_not_a_number():
    from prior_auth_eval.checks import _numbers
    assert _numbers("one of the criteria was met; no one disputes it") == set()
    assert _numbers("Two-week trial, then three visits") == {"2", "3"}


def test_invented_clinical_term_is_flagged(case, good_letter):
    bad = good_letter.replace(
        "## Policy basis",
        "- Patient previously underwent lumbar fusion surgery with persistent hardware pain.\n\n"
        "## Policy basis")
    r = check_facts(case, bad)
    assert not r.passed and "fusion" in r.findings[0]


def test_light_paraphrase_is_tolerated(case, good_letter):
    ok = good_letter.replace(
        "- Low back pain radiating to the left leg since 2025-11-20.",
        "- Low back pain that radiates to the left leg, present since 2025-11-20.")
    assert check_facts(case, ok).passed


def test_invented_date_is_flagged(case, good_letter):
    bad = good_letter.replace("since 2025-11-20", "since 2025-09-01")
    assert not check_facts(case, bad).passed


def test_no_summary_fails(case):
    assert not check_facts(case, "## Policy basis\nSYN-LCD-9001").passed


# ---- denial reason
def test_reason_requires_criterion_and_terms(case, good_letter):
    generic = good_letter.replace(
        "The plan denied this request under SYN-D01 (Not medically necessary), stating that\n"
        "SYN-LCD-9001-C2 is not met. The chart documents 6 weeks of physical therapy without "
        "relief.",
        "We believe this service is appropriate and ask for prompt review.")
    r = check_denial_reason(case, generic)
    assert not r.passed and len(r.findings) == 2


def test_reason_criterion_missing_but_terms_present(case, good_letter):
    bad = good_letter.replace(
        "stating that\nSYN-LCD-9001-C2 is not met", "stating that it is unmet")
    r = check_denial_reason(case, bad)
    assert [f for f in r.findings if "unmet criterion" in f]


def test_reason_section_missing(case):
    assert not check_denial_reason(case, "Dear plan, please approve.").passed


# ---- identifiers
def test_identifier_extraction(good_letter):
    ids = extract_identifiers(good_letter)
    assert ids["member_id"] == ["SYN-MBR-900001"] and ids["cpt"] == ["72148"]
    assert ids["icd10"] == ["M54.16"] and ids["patient_name"] == ["Pat Example"]


@pytest.mark.parametrize("old,new,key", [
    ("SYN-MBR-900001", "SYN-MBR-900002", "member_id"),
    ("SYN-CLM-900001", "SYN-CLM-900009", "claim_id"),
    ("CPT 72148", "CPT 72149", "cpt"),
    ("ICD-10 M54.16", "ICD-10 M54.17", "icd10"),
    ("Patient: Pat Example", "Patient: Pat Someoneelse", "patient_name"),
])
def test_wrong_identifier_flagged(case, good_letter, old, new, key):
    r = check_identifiers(case, good_letter.replace(old, new))
    assert not r.passed and any(f.startswith(key) for f in r.findings)


def test_missing_identifier_flagged(case, good_letter):
    r = check_identifiers(case, good_letter.replace("Member ID: SYN-MBR-900001", "Member ID: n/a"))
    assert any("member_id not found" in f for f in r.findings)


# ---- required elements
def test_missing_elements_each_detected(case, good_letter):
    no_req = good_letter.replace("We request that the denial be overturned.", "")
    assert any("request" in f for f in check_required_elements(case, no_req).findings)
    no_enc = good_letter.replace("- Chart notes 2026-01-05 and 2026-02-23", "")
    assert any("Enclosures" in f for f in check_required_elements(case, no_enc).findings)
    no_sig = good_letter.replace(", NPI SYN-0000", "")
    assert any("NPI" in f for f in check_required_elements(case, no_sig).findings)


def test_late_filing_flagged(case, good_letter):
    late = good_letter.replace("Date: 2026-03-20", "Date: 2026-05-02")
    r = check_required_elements(case, late)
    assert not r.passed and "after the appeal deadline" in r.findings[0]
    on_deadline = good_letter.replace("Date: 2026-03-20", "Date: 2026-05-01")
    assert check_required_elements(case, on_deadline).passed


def test_sections_helper():
    s = sections("head\n## A b\nx\n## C\ny")
    assert s["a b"] == "x" and s["c"] == "y" and s["_header"] == "head"



def test_negation_flip_is_flagged(case_dict, good_letter):
    """Chart says 'not on anticoagulants'; asserting the patient is on them fails."""
    from prior_auth_eval.schema import parse_case
    case_dict["chart"]["facts"].append({
        "id": "f3", "date": "2026-02-03",
        "text": "Not on anticoagulants or antiplatelet agents; no signs of infection.",
    })
    case2 = parse_case(case_dict)
    inject = good_letter.replace(
        "## Clinical summary\n",
        "## Clinical summary\n"
        "- Currently taking anticoagulants and antiplatelet agents (2026-02-03).\n",
    )
    r = check_facts(case2, inject)
    assert not r.passed
    assert any("negation flip" in f and "anticoagulants" in f for f in r.findings)


def test_chart_negation_restated_with_negation_is_ok(case_dict, good_letter):
    from prior_auth_eval.schema import parse_case
    case_dict["chart"]["facts"].append({
        "id": "f3", "date": "2026-02-03",
        "text": "Not on anticoagulants; no signs of infection.",
    })
    case2 = parse_case(case_dict)
    inject = good_letter.replace(
        "## Clinical summary\n",
        "## Clinical summary\n"
        "- Not on anticoagulants; no signs of infection (2026-02-03).\n",
    )
    assert check_facts(case2, inject).passed


def test_term_negated_in_one_fact_but_asserted_in_another_is_not_a_flip(case_dict, good_letter):
    """'No personal history of cancer' must not flag a family-history mention of cancer."""
    from prior_auth_eval.schema import parse_case
    case_dict["chart"]["facts"] += [
        {"id": "f3", "date": "2026-02-03", "text": "No personal history of cancer."},
        {"id": "f4", "date": "2026-02-03",
         "text": "Mother diagnosed with breast cancer at age 44."},
    ]
    case2 = parse_case(case_dict)
    inject = good_letter.replace(
        "## Clinical summary\n",
        "## Clinical summary\n- Mother diagnosed with breast cancer at age 44 (2026-02-03).\n",
    )
    assert check_facts(case2, inject).passed


def test_near_miss_member_id_is_flagged(case, good_letter):
    r = check_identifiers(case, good_letter.replace("SYN-MBR-900001", "SYN-MBR-900002"))
    assert not r.passed and any(f.startswith("member_id") for f in r.findings)


# ---- extra PHI / minimum necessary
def test_extra_phi_passes_on_good_letter(case, good_letter):
    r = check_extra_phi(case, good_letter)
    assert r.passed and r.severity == "major"


@pytest.mark.parametrize("snippet,kind", [
    ("SSN: 900-00-0021", "SSN"),
    ("Call the patient at 555-555-0142.", "phone number"),
    ("Call the patient at (555) 555-0142.", "phone number"),
    ("Email pat.example@example.org with questions.", "email address"),
    ("Home address: 742 Placeholder Lane, Faketown.", "street address"),
])
def test_extra_phi_flags_identifiers_not_in_source(case, good_letter, snippet, kind):
    bad = good_letter.replace("## Response to denial reason",
                              f"{snippet}\n\n## Response to denial reason")
    r = check_extra_phi(case, bad)
    assert not r.passed and any(f.startswith(kind) for f in r.findings), r.findings


def test_extra_phi_allows_identifiers_found_in_chart_or_denial(case_dict, good_letter):
    case_dict["chart"]["facts"].append({
        "id": "f3", "date": "2026-02-23",
        "text": "Caregiver contact on file: 555-555-0142, 742 Placeholder Lane.",
    })
    case_dict["denial"]["letter_text"] += " Questions: appeals@example.org."
    case2 = parse_case(case_dict)
    ok = good_letter.replace(
        "## Enclosures",
        "Contact: (555) 555-0142, 742 Placeholder Lane, appeals@example.org.\n\n## Enclosures")
    assert check_extra_phi(case2, ok).passed


def test_extra_phi_ignores_dates_and_synthetic_ids(case, good_letter):
    ok = good_letter + "\nSee claim SYN-CLM-900001 dated 2026-03-02 and NPI SYN-0000.\n"
    assert check_extra_phi(case, ok).passed


def test_laterality_swap_is_flagged(case, good_letter):
    bad = good_letter.replace("radiating to the left leg", "radiating to the right leg")
    assert bad != good_letter
    r = check_facts(case, bad)
    assert not r.passed and any("laterality" in f and "right" in f for f in r.findings)


def test_relative_swap_is_flagged(case_dict, good_letter):
    case_dict["chart"]["facts"].append(
        {"id": "f3", "date": "2026-01-05", "text": "Father had lumbar stenosis."})
    c = parse_case(case_dict)
    ok = good_letter.replace("## Policy basis",
                             "- Father had lumbar stenosis (2026-01-05).\n\n## Policy basis")
    assert check_facts(c, ok).passed
    bad = ok.replace("- Father had", "- Brother had")
    r = check_facts(c, bad)
    assert not r.passed and any("brother" in f for f in r.findings)


def test_planned_procedure_stated_as_done_is_flagged(case_dict, good_letter):
    case_dict["chart"]["facts"].append({
        "id": "f3", "date": "2026-02-03",
        "text": "Referral placed; surgical consult planned for nerve decompression.",
    })
    c = parse_case(case_dict)
    ok = good_letter.replace(
        "## Policy basis",
        "- Referral placed; surgical consult planned for nerve decompression (2026-02-03)."
        "\n\n## Policy basis")
    assert check_facts(c, ok).passed
    bad = ok.replace("- Referral placed; surgical consult planned for",
                     "- Referral placed; pain persisted after")
    r = check_facts(c, bad)
    assert not r.passed and any("only plans" in f and "decompression" in f for f in r.findings)


def test_bullet_dated_to_a_different_chart_fact_is_flagged(case, good_letter):
    ok = good_letter.replace(
        "## Policy basis",
        "- Completed 6 weeks of physical therapy (12 sessions); pain 7/10 (2026-02-23)."
        "\n\n## Policy basis")
    assert check_facts(case, ok).passed
    bad = ok.replace("pain 7/10 (2026-02-23)", "pain 7/10 (2026-01-05)")
    r = check_facts(case, bad)
    assert not r.passed and any("dated 2026-01-05" in f and "2026-02-23" in f for f in r.findings)
    # A date written inside the fact text ("since 2025-11-20") is not a misdate.
    assert check_facts(case, good_letter).passed
