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
they will also flag some legitimate paraphrases. The extra-PHI check is a pattern floor for
SSNs, phone numbers, emails and street addresses not found in the source material; it is not a
full minimum-necessary review. Human review is still required.
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


_SPELLED = {w: str(i) for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
    "fifteen sixteen seventeen eighteen nineteen twenty".split())}
_SPELLED.update({"thirty": "30", "forty": "40", "fifty": "50", "sixty": "60", "ninety": "90"})
# Only count a spelled-out number when it quantifies something ("nine weeks", "two visits"),
# so "one of the criteria" or "no one" does not read as the number 1.
_SPELLED_QTY = re.compile(
    r"\b(" + "|".join(_SPELLED) + r")(?:[ -]+)(?=(?:days?|weeks?|months?|years?|sessions?|"
    r"visits?|doses?|times|trials?|courses?|cycles?|episodes?|medications?|attempts?)\b)",
    re.IGNORECASE)


def _numbers(text: str) -> set[str]:
    dates = set(_DATE.findall(text))
    rest = _DATE.sub(" ", text)
    rest = _SPELLED_QTY.sub(lambda m: f" {_SPELLED[m.group(1).lower()]} ", rest)
    return dates | set(_NUM.findall(rest))


def _words(text: str) -> set[str]:
    return {w for w in _WORD.findall(_DATE.sub(" ", text).lower()) if w not in _STOP}


_NEG_CUE = re.compile(
    r"\b(?:no|not|never|denies|denied|without|absence|negative|free of|"
    r"unremarkable for)\b",
    re.IGNORECASE,
)


def _negated_words(text: str) -> set[str]:
    """Content words that sit in a short window after a negation cue.

    Used to catch polarity flips (chart: "not on anticoagulants"; letter: "on anticoagulants").
    The window stops at the next sentence boundary and is capped so distant positives are ignored.
    """
    out: set[str] = set()
    for m in _NEG_CUE.finditer(text):
        window = re.split(r"[.;\n]", text[m.end():m.end() + 70], maxsplit=1)[0]
        out |= _words(window)
    return out


# Words where a one-word swap changes the clinical meaning (whose history, which side). A single
# swapped word stays under UNSEEN_RATIO, so these must appear in the chart verbatim.
_PINNED = re.compile(
    r"\b(mother|father|sister|brother|daughter|son|aunt|uncle|niece|nephew|cousin|"
    r"grandmother|grandfather|maternal|paternal|sibling|left|right|bilateral|unilateral)s?\b",
    re.IGNORECASE,
)


def _pinned_terms(text: str) -> set[str]:
    return {m.group(1).lower() for m in _PINNED.finditer(text)}


# Cues that a procedure or test is only intended, not done. A term the chart mentions only in
# such a window must not appear in the letter as something that already happened.
_PLAN_CUE = re.compile(
    r"\b(?:plan|plans|planned|planning|possible|possibly|consider|considering|scheduled|"
    r"pending|proposed|recommended|requested|candidate for|referred for)\b",
    re.IGNORECASE,
)


def _plan_spans(text: str) -> list[tuple[int, int]]:
    spans = []
    for m in _PLAN_CUE.finditer(text):
        window = re.split(r"[.;\n]", text[m.end():m.end() + 70], maxsplit=1)[0]
        spans.append((m.start(), m.end() + len(window)))
    return spans


def _split_planned(text: str) -> tuple[set[str], set[str]]:
    """(words inside a planning window, words outside every planning window)."""
    spans = _plan_spans(text)
    inside = set().union(*(_words(text[a:b]) for a, b in spans)) if spans else set()
    masked = list(text)
    for a, b in spans:
        masked[a:b] = " " * (b - a)
    return inside, _words("".join(masked))


# A dated bullet that closely paraphrases one chart fact should carry that fact's date. Below
# this Jaccard word overlap the bullet is treated as a summary of several facts and not checked.
DATE_MATCH_MIN = 0.5


def _misdated(facts, bullet: str) -> tuple[str, str] | None:
    """(bullet date, expected date) when a bullet's date belongs to a different chart fact."""
    dates = set(_DATE.findall(bullet))
    words = _words(bullet)
    if not dates or not words:
        return None
    scored = []
    for f in facts:
        fw = _words(f.text)
        # A fact's own visit date and any date written in its text ("since 2025-11-20") count.
        scored.append((len(words & fw) / len(words | fw) if fw else 0.0,
                       {f.date, *_DATE.findall(f.text)}))
    best = max(s for s, _ in scored)
    if best < DATE_MATCH_MIN:
        return None
    expected = set().union(*(ds for s, ds in scored if s >= best - 1e-9))
    if dates & expected:
        return None
    return sorted(dates)[0], ", ".join(sorted(expected))


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
    # A term only counts as chart-negated if no chart fact also asserts it. Otherwise
    # "No personal history of cancer" would flag every family-history mention of cancer.
    chart_asserted = set().union(*(_words(f.text) - _negated_words(f.text)
                                   for f in case.chart.facts))
    chart_negated = _negated_words(chart_text) - chart_asserted
    chart_pinned = _pinned_terms(chart_text)
    planned, done = set(), set()
    for f in case.chart.facts:
        inside, outside = _split_planned(f.text)
        planned |= inside
        done |= outside
    chart_planned_only = planned - done
    for b in bullets(block):
        bad_nums = sorted(n for n in _numbers(b) if n not in chart_nums)
        words = _words(b)
        unseen = sorted(w for w in words if w not in chart_words)
        ratio = len(unseen) / len(words) if words else 0.0
        bullet_negated = _negated_words(b)
        flipped = sorted(w for w in words if w in chart_negated and w not in bullet_negated)
        swapped = sorted(_pinned_terms(b) - chart_pinned)
        as_done = sorted(_split_planned(b)[1] & chart_planned_only)
        misdated = _misdated(case.chart.facts, b)
        if bad_nums:
            res.findings.append(f"number(s) not in chart {bad_nums}: \"{b}\"")
        elif flipped:
            res.findings.append(
                f"possible negation flip of chart-negated term(s) {flipped}: \"{b}\"")
        elif swapped:
            res.findings.append(
                f"relative/laterality term(s) not in chart {swapped}: \"{b}\"")
        elif as_done:
            res.findings.append(
                f"chart only plans {as_done}; letter states it as done: \"{b}\"")
        elif misdated:
            res.findings.append(
                f"dated {misdated[0]} but the matching chart fact is dated {misdated[1]}: \"{b}\"")
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


# ---------------------------------------------------------------- 6. extra PHI

_PHI_RX = {
    "SSN": re.compile(r"(?<![\w-])\d{3}-\d{2}-\d{4}(?![\w-])"),
    "phone number": re.compile(
        r"(?<![\w-])(?:\+?1[-. ]?)?(?:\(\d{3}\)\s?|\d{3}[-. ])\d{3}[-. ]\d{4}(?![\w-])"),
    "email address": re.compile(r"\b[\w.+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+\b"),
    "street address": re.compile(
        r"\b\d{1,6}\s+(?:[A-Z][A-Za-z'-]*\.?\s+){1,4}"
        r"(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Court|Ct|Place|Pl|"
        r"Way|Terrace|Circle|Parkway|Pkwy|Highway|Hwy)\b\.?"),
}


def _phi_key(kind: str, value: str) -> str:
    if kind in ("SSN", "phone number"):
        digits = re.sub(r"\D", "", value)
        return digits[-10:] if kind == "phone number" else digits
    return re.sub(r"\s+", " ", value.strip().rstrip(".")).lower()


def check_extra_phi(case: Case, letter: str) -> CheckResult:
    """Minimum-necessary floor: flag SSNs, phone numbers, emails and street addresses that the
    letter adds but that appear nowhere in the chart or the denial letter.

    Identifiers that are in the source material are allowed (the appeal may need them); this
    only catches over-sharing of identifiers the drafter invented or pulled from elsewhere.
    """
    res = CheckResult("extra_phi", True, MAJOR)
    ch = case.chart
    source = " \n".join([*(f.text for f in ch.facts), case.denial.letter_text,
                         ch.patient_name, ch.dob, ch.member_id, ch.provider_name])
    for kind, rx in _PHI_RX.items():
        allowed = {_phi_key(kind, m.group(0)) for m in rx.finditer(source)}
        for m in rx.finditer(letter):
            if _phi_key(kind, m.group(0)) not in allowed:
                res.findings.append(
                    f"{kind} '{m.group(0).strip()}' is not in the chart or denial letter "
                    "(minimum necessary)")
    res.findings = sorted(set(res.findings))
    res.passed = not res.findings
    return res


# ---------------------------------------------------------------- run all

CHECKS = (check_citations, check_facts, check_denial_reason, check_identifiers,
          check_required_elements, check_extra_phi)
CHECK_NAMES = ("citations", "facts_in_chart", "denial_reason_addressed", "identifiers_match",
               "required_elements", "extra_phi")


def run_checks(case: Case, letter: str) -> list[CheckResult]:
    return [fn(case, letter) for fn in CHECKS]
