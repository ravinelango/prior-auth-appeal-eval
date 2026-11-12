"""pae: evaluate prior-authorization appeal drafts against synthetic denial cases."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .checks import run_checks
from .drafters import build_prompt, get_drafter
from .report import decision, evaluate, render
from .schema import load_cases

# Judgment criteria the deterministic checks cannot score; humans label them so an
# LLM judge can later be calibrated against those labels with judge-calibration-kit.
JUDGE_CRITERIA = (
    (
        "persuasive",
        "The letter makes a clear, specific case that the request meets the cited coverage "
        "criteria, in a tone a payer reviewer would take seriously.",
    ),
    (
        "complete",
        "The letter covers every element the denial and the cited criteria call for, so a "
        "reviewer would not need to ask for anything else.",
    ),
)


def write_label_sheet(path: Path, evals, dataset_label: str) -> int:
    """Write one jck `criteria` row per letter with every label left blank.

    jck rejects blank labels, so the sheet cannot be calibrated until a human fills each
    label with pass or fail. The deterministic check status rides along for context only.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# {dataset_label}",
        "# Labeling sheet from `pae run --label-sheet`. Fill every criteria[].label with pass or"
        " fail, then: jck run --data THIS_FILE --judge ...",
    ]
    for e in evals:
        row = {
            "id": e.case.id,
            "input": build_prompt(e.case),
            "output": e.letter,
            "deterministic_status": e.status,
            "criteria": [{"name": n, "rubric": r, "label": ""} for n, r in JUDGE_CRITERIA],
        }
        lines.append(json.dumps(row, ensure_ascii=False))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(evals)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="pae", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate", help="check a cases file")
    v.add_argument("--cases", required=True, type=Path)
    r = sub.add_parser("run", help="draft every case, run the checks, write a report")
    r.add_argument("--cases", required=True, type=Path)
    r.add_argument("--drafter", default="mock:good", help="mock:good | mock:flawed | files:DIR")
    r.add_argument("--out", type=Path, help="markdown report path (default: stdout)")
    r.add_argument("--json", type=Path, help="optional machine-readable summary")
    r.add_argument("--strict", action="store_true", help="exit 1 unless the decision is GO")
    r.add_argument(
        "--label-sheet",
        type=Path,
        help="write a judge-calibration-kit JSONL labeling sheet (blank human labels)",
    )
    c = sub.add_parser("check", help="check one letter file against one case")
    c.add_argument("--cases", required=True, type=Path)
    c.add_argument("--case-id", required=True)
    c.add_argument("--letter", required=True, type=Path)
    pr = sub.add_parser("prompt", help="print the drafting prompt for a case")
    pr.add_argument("--cases", required=True, type=Path)
    pr.add_argument("--case-id", required=True)
    a = p.parse_args(argv)

    cases = load_cases(a.cases)
    if a.cmd == "validate":
        print(f"OK: {len(cases.cases)} cases")
        return 0
    if a.cmd in ("check", "prompt"):
        case = next((x for x in cases.cases if x.id == a.case_id), None)
        if case is None:
            print(f"unknown case id {a.case_id}", file=sys.stderr)
            return 2
        if a.cmd == "prompt":
            print(build_prompt(case))
            return 0
        results = run_checks(case, a.letter.read_text(encoding="utf-8"))
        for res in results:
            print(f"{'pass' if res.passed else 'FAIL'}  {res.name}")
            for f in res.findings:
                print(f"      {f}")
        return 0 if all(res.passed for res in results) else 1

    drafter = get_drafter(a.drafter)
    evals = evaluate(cases, drafter)
    verdict, reasons = decision(evals)
    md = render(cases, evals, drafter, a.cases.name)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(md, encoding="utf-8")
        print(f"wrote {a.out}")
    else:
        sys.stdout.write(md)
    if a.label_sheet:
        n = write_label_sheet(a.label_sheet, evals, cases.label)
        print(f"wrote {a.label_sheet} ({n} letters, labels blank)")
    if a.json:
        a.json.write_text(
            json.dumps(
                {
                    "drafter": drafter.name,
                    "decision": verdict,
                    "reasons": reasons,
                    "synthetic": cases.label.upper().startswith("SYNTHETIC"),
                    "cases": [
                        {"id": e.case.id, "status": e.status, "failed": [x.name for x in e.failed]}
                        for e in evals
                    ],
                },
                indent=2,
            )
        )
    print(f"decision: {verdict}", file=sys.stderr)
    return 1 if a.strict and verdict != "GO" else 0


if __name__ == "__main__":
    raise SystemExit(main())
