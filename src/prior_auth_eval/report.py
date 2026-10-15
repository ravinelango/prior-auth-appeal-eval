"""Run checks over a case set, roll up a go/no-go style decision, render markdown."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .checks import CHECK_NAMES, CRITICAL, CheckResult, run_checks
from .drafters import Drafter
from .schema import Case, CaseSet


@dataclass
class CaseEval:
    case: Case
    letter: str
    results: list[CheckResult]

    @property
    def failed(self) -> list[CheckResult]:
        return [r for r in self.results if not r.passed]

    @property
    def status(self) -> str:
        if not self.failed:
            return "PASS"
        return "FAIL" if any(r.severity == CRITICAL for r in self.failed) else "FAIL (minor)"


def evaluate(cases: CaseSet, drafter: Drafter) -> list[CaseEval]:
    out = []
    for c in cases.cases:
        letter = drafter.draft(c)
        out.append(CaseEval(c, letter, run_checks(c, letter)))
    return out


def decision(evals: list[CaseEval]) -> tuple[str, list[str]]:
    """NO-GO if any critical check fails on any case; GO WITH CONDITIONS if only required
    elements fail; GO otherwise. A GO means the deterministic floor passed, not that the
    letters are good."""
    reasons = [f"{e.case.id}: {r.name} failed" for e in evals for r in e.failed
               if r.severity == CRITICAL]
    if reasons:
        return "NO-GO", reasons
    minor = [f"{e.case.id}: {r.name} failed" for e in evals for r in e.failed]
    return ("GO WITH CONDITIONS", minor) if minor else ("GO", [])


def _mark(ok: bool) -> str:
    return "pass" if ok else "FAIL"


def render(cases: CaseSet, evals: list[CaseEval], drafter: Drafter, dataset: str) -> str:
    verdict, reasons = decision(evals)
    n = len(evals)
    lines = ["# Prior-auth appeal evaluation report", "",
             f"- Dataset: `{dataset}` ({n} cases)",
             f"- Drafter: `{drafter.name}`",
             f"- Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"]
    if cases.label.upper().startswith("SYNTHETIC"):
        lines += ["", "> **Synthetic demo.** Cases are invented and the mock drafter replays "
                  "fixed reference letters, so this report shows the format and that the "
                  "checkers fire on seeded flaws. It is not a measurement of any model."]
    lines += ["", f"## Decision: **{verdict}**", ""]
    if reasons:
        lines += [f"- {r}" for r in reasons] + [""]
    lines += ["_Deterministic checks are a floor, not a replacement for human review. "
              "A GO does not mean the letters are good. Not medical or legal advice._", "",
              "## Failures by check", "", "| Check | Severity | Cases failed |", "|---|---|---|"]
    for name in CHECK_NAMES:
        sample = next(r for e in evals for r in e.results if r.name == name)
        failed = sum(1 for e in evals for r in e.results if r.name == name and not r.passed)
        lines.append(f"| {name} | {sample.severity} | {failed}/{n} |")
    lines += ["", "## Per-case results", "",
              "| Case | Service | " + " | ".join(CHECK_NAMES) + " | Status |",
              "|---|---|" + "---|" * len(CHECK_NAMES) + "---|"]
    for e in evals:
        by = {r.name: r.passed for r in e.results}
        lines.append(f"| {e.case.id} | CPT {e.case.denial.cpt} | "
                     + " | ".join(_mark(by[nm]) for nm in CHECK_NAMES) + f" | {e.status} |")
    bad = [e for e in evals if e.failed]
    lines += ["", "## Findings", ""]
    if not bad:
        lines.append("No findings.")
    for e in bad:
        lines.append(f"### {e.case.id}: {e.case.title}")
        for r in e.failed:
            lines += [f"- **{r.name}** ({r.severity})"] + [f"  - {f}" for f in r.findings]
        lines.append("")
    seeded = [(e, getattr(drafter, "seeded_flaws", None)) for e in evals]
    if all(fn is not None for _, fn in seeded):
        lines += ["## Checker validation (seeded flaws, mock drafter only)", "",
                  "| Case | Seeded flaws | Checks that failed | Match |", "|---|---|---|---|"]
        hits = 0
        for e, fn in seeded:
            want = sorted(fn(e.case))
            got = sorted(r.name for r in e.failed)
            hits += want == got
            lines.append(f"| {e.case.id} | {', '.join(want) or '-'} | {', '.join(got) or '-'} | "
                         f"{'yes' if want == got else 'NO'} |")
        lines += ["", f"{hits}/{n} cases matched. This validates the checkers against flaws "
                  "written by the same author; it says nothing about real model output.", ""]
    return "\n".join(lines).rstrip() + "\n"
