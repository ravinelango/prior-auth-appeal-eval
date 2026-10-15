"""Deterministic checkers for LLM-drafted prior-authorization appeal letters.

Output contract the checkers rely on (give this to the drafter):

    Date: YYYY-MM-DD
    RE: ... claim SYN-CLM-xxxxxx
    Patient: <name> | Member ID: <id> | DOB: <date>
    Requested service: CPT <5 digits> | Diagnosis: ICD-10 <code>
    ## Response to denial reason      (cite each unmet criterion id; address the stated reason)
    ## Clinical summary               (one "- " bullet per clinical assertion, from the chart only)
    ## Policy basis                   (cite provided policy ids only)
    ## Enclosures                     ("- " bullets)
    Sincerely, <clinician>, NPI <number>

These checks are a floor, not a verdict. They are intentionally literal: they catch
fabricated citations, ungrounded numbers/terms, wrong identifiers and missing parts, and
they will also flag some legitimate paraphrases. Human review is still required.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from .schema import Case

CRITICAL = "critical"
MAJOR = "major"


@dataclass
class CheckResult:
    name: str
    passed: bool
    severity: str
    findings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------- helpers

def sections(text: str) -> dict[str, str]:
    """Split on '## Heading' lines. Keys are lower-cased headings."""
    out: dict[str, list[str]] = {}
    current = "_header"
    for line in text.splitlines():
        m = re.match(r"^##\s+(.*?)\s*$", line)
        if m:
            current = m.group(1).lower()
            out.setdefault(current, [])
        else:
            out.setdefault(current, []).append(line)
    return {k: "\n".join(v).strip() for k, v in out.items()}


def bullets(block: str) -> list[str]:
    return [m.group(1).strip() for line in block.splitlines()
            if (m := re.match(r"^\s*[-*]\s+(.*\S)\s*$", line))]


# ---------------------------------------------------------------- 1. citations

_CITE = re.compile(r"\b((?:SYN-)?(?:LCD|NCD)[- ]?[A-Z]?\d+(?:\.\d+)*)(?:-C(\d+))?", re.IGNORECASE)


def _norm_policy(raw: str) -> str:
    return re.sub(r"\s+", "-", raw.strip().upper())


def extract_citations(text: str) -> list[tuple[str, str | None]]:
    """(policy_id, criterion_id or None) for every LCD/NCD-style reference in the text."""
    out = []
    for m in _CITE.finditer(text):
        pid = _norm_policy(m.group(1))
        out.append((pid, f"{pid}-C{m.group(2)}" if m.group(2) else None))
    return out


def check_citations(case: Case, letter: str) -> CheckResult:
    res = CheckResult("citations", True, CRITICAL)
    provided = {p.id for p in case.policies}
    applicable = case.denial.applicable_policy
    cites = extract_citations(letter)
    for pid, crit in cites:
        if pid not in provided:
            res.findings.append(f"cites policy {pid}, which is not in the provided policy set")
        elif pid != applicable:
            res.findings.append(
                f"cites {pid}, which exists but does not govern this denial ({applicable})")
        elif crit and crit not in case.criterion_ids():
            res.findings.append(f"cites criterion {crit}, which does not exist in {pid}")
    if applicable not in {pid for pid, _ in cites}:
        res.findings.append(f"never cites the governing policy {applicable}")
    res.findings = sorted(set(res.findings))
    res.passed = not res.findings
    return res


# ---------------------------------------------------------------- 2. facts

_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_NUM = re.compile(r"\d+(?:\.\d+)?")
_WORD = re.compile(r"[a-z]{4,}")
_STOP = set("""
patient patients with that this from have been were was documented documents history shows
showed shown record records chart noted note notes reports reported after before during over
since than then also both each their there which while into onto upon about during
completed started continued presented present currently remains remained
""".split())
UNSEEN_RATIO = 0.34


def _numbers(text: str) -> set[str]:
    dates = set(_DATE.findall(text))
    rest = _DATE.sub(" ", text)
    return dates | set(_NUM.findall(rest))


def _words(text: str) -> set[str]:
    return {w for w in _WORD.findall(_DATE.sub(" ", text).lower()) if w not in _STOP}


def check_facts(case: Case, letter: str) -> CheckResult:
    """Every bullet under '## Clinical summary' must be traceable to the chart."""
    res = CheckResult("facts_in_chart", True, CRITICAL)
    block = sections(letter).get("clinical summary")
    if not block or not bullets(block):
        res.findings.append("no '## Clinical summary' bullets to verify")
        res.passed = False
        return res
    chart_text = " ".join(f"{f.date} {f.text}" for f in case.chart.facts)
    chart_nums = _numbers(chart_text)
    chart_words = _words(chart_text) | _words(case.chart.patient_name)
    for b in bullets(block):
        bad_nums = sorted(n for n in _numbers(b) if n not in chart_nums)
        words = _words(b)
        unseen = sorted(w for w in words if w not in chart_words)
        ratio = len(unseen) / len(words) if words else 0.0
        if bad_nums:
            res.findings.append(f"number(s) not in chart {bad_nums}: \"{b}\"")
        elif ratio > UNSEEN_RATIO:
            res.findings.append(f"term(s) not in chart {unseen}: \"{b}\"")
    res.passed = not res.findings
    return res


# ---------------------------------------------------------------- 3. denial reason

def check_denial_reason(case: Case, letter: str) -> CheckResult:
    res = CheckResult("denial_reason_addressed", True, CRITICAL)
    block = sections(letter).get("response to denial reason")
    if not block:
        res.findings.append("missing '## Response to denial reason' section")
        res.passed = False
        return res
    low = block.lower()
    for crit in case.denial.unmet_criteria:
        if crit.lower() not in low:
            res.findings.append(f"response does not cite the unmet criterion {crit}")
    terms = [t for t in case.denial.reason_terms]
    hit = [t for t in terms if t.lower() in low]
    if len(hit) * 2 < len(terms):
        res.findings.append(
            f"response engages with {len(hit)}/{len(terms)} expected terms "
            f"(missing: {[t for t in terms if t not in hit]})")
    res.passed = not res.findings
    return res


# ---------------------------------------------------------------- 4. identifiers

_RX = {
    "claim_id": re.compile(r"\bSYN-CLM-\d+\b"),
    "member_id": re.compile(r"\bSYN-MBR-\d+\b"),
    "cpt": re.compile(r"\bCPT[:\s]*#?\s*(\d{5})\b", re.IGNORECASE),
    "icd10": re.compile(r"\bICD-?10[:\s]*([A-Z]\d{2}(?:\.\w{1,4})?)\b", re.IGNORECASE),
    "patient_name": re.compile(r"^Patient:\s*([^|\n]+?)\s*(?:\||$)", re.MULTILINE),
}


def extract_identifiers(letter: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for key, rx in _RX.items():
        vals = [m.group(1) if rx.groups else m.group(0) for m in rx.finditer(letter)]
        out[key] = [v.strip().upper() if key != "patient_name" else v.strip() for v in vals]
    return out


def check_identifiers(case: Case, letter: str) -> CheckResult:
    res = CheckResult("identifiers_match", True, CRITICAL)
    expected = {
        "claim_id": case.denial.claim_id, "member_id": case.chart.member_id,
        "cpt": case.denial.cpt, "icd10": case.denial.icd10,
        "patient_name": case.chart.patient_name,
    }
    found = extract_identifiers(letter)
    for key, want in expected.items():
        vals = found[key]
        want_n = want.upper() if key != "patient_name" else want
        if not vals:
            res.findings.append(f"{key} not found in the letter (expected {want})")
        for v in vals:
            if v != want_n:
                res.findings.append(f"{key} is {v}, expected {want}")
    res.findings = sorted(set(res.findings))
    res.passed = not res.findings
    return res


# ---------------------------------------------------------------- 5. required elements

_OVERTURN = re.compile(r"\b(overturn|reverse (?:the|this) denial|reversal of (?:the|this) denial)",
                       re.IGNORECASE)


def _parse_date(s: str) -> date | None:
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def check_required_elements(case: Case, letter: str) -> CheckResult:
    res = CheckResult("required_elements", True, MAJOR)
    secs = sections(letter)
    if not _OVERTURN.search(letter):
        res.findings.append("no explicit request to overturn/reverse the denial")
    if not bullets(secs.get("enclosures", "")):
        res.findings.append("no '## Enclosures' list")
    if not (re.search(r"\bSincerely\b", letter, re.IGNORECASE)
            and re.search(r"\bNPI\s*[:#]?\s*\S+", letter)):
        res.findings.append("no signature block with provider NPI")
    m = re.search(r"^Date:\s*(\S+)", letter, re.MULTILINE)
    filed = _parse_date(m.group(1)) if m else None
    deadline = _parse_date(case.denial.appeal_deadline)
    if filed is None:
        res.findings.append("no parseable 'Date: YYYY-MM-DD' line")
    elif deadline and filed > deadline:
        res.findings.append(
            f"letter dated {filed} is after the appeal deadline {case.denial.appeal_deadline}")
    res.passed = not res.findings
    return res


# ---------------------------------------------------------------- run all

CHECKS = (check_citations, check_facts, check_denial_reason, check_identifiers,
          check_required_elements)
CHECK_NAMES = ("citations", "facts_in_chart", "denial_reason_addressed", "identifiers_match",
               "required_elements")


def run_checks(case: Case, letter: str) -> list[CheckResult]:
    return [fn(case, letter) for fn in CHECKS]
