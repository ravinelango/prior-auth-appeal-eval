import json
from pathlib import Path

import pytest

from prior_auth_eval.cli import main
from prior_auth_eval.drafters import FilesDrafter, MockDrafter, build_prompt, get_drafter
from prior_auth_eval.report import decision, evaluate, render
from prior_auth_eval.schema import load_cases

EX = Path(__file__).parents[1] / "examples" / "synthetic_cases.json"
CASES = load_cases(EX)


def test_get_drafter():
    assert get_drafter("mock").name == "mock:good"
    assert get_drafter("mock:flawed").name == "mock:flawed"
    assert get_drafter("files:/tmp").name == "files:/tmp"
    with pytest.raises(ValueError):
        get_drafter("gpt")


def test_prompt_contains_only_case_material():
    p = build_prompt(CASES.cases[0])
    assert "SYN-LCD-1001-C2" in p and "Use ONLY the facts" in p and "26 weeks" not in p


def test_files_drafter_reads_and_reports_missing(tmp_path):
    case = CASES.cases[0]
    with pytest.raises(FileNotFoundError):
        FilesDrafter(str(tmp_path)).draft(case)
    (tmp_path / f"{case.id}.txt").write_text("hello")
    assert FilesDrafter(str(tmp_path)).draft(case) == "hello"


def test_good_run_is_go_and_flawed_run_is_no_go():
    assert decision(evaluate(CASES, MockDrafter("good")))[0] == "GO"
    verdict, reasons = decision(evaluate(CASES, MockDrafter("flawed")))
    assert verdict == "NO-GO" and any("PA-001: citations" in r for r in reasons)


def test_only_required_elements_failing_is_go_with_conditions():
    evals = evaluate(CASES, MockDrafter("good"))
    case = CASES.cases[8]
    flawed = evaluate(type(CASES)("SYNTHETIC", (case,)), MockDrafter("flawed"))
    assert decision(flawed)[0] == "GO WITH CONDITIONS"
    assert decision(evals)[0] == "GO"


def test_report_content():
    md = render(CASES, evaluate(CASES, MockDrafter("flawed")), MockDrafter("flawed"), "x.json")
    assert "Synthetic demo" in md and "Decision: **NO-GO**" in md
    assert "Checker validation" in md and "10/10 cases matched" in md
    assert "not medical or legal advice" in md.lower()


def test_cli_end_to_end(tmp_path):
    out, js = tmp_path / "r.md", tmp_path / "r.json"
    assert main(["run", "--cases", str(EX), "--drafter", "mock:good", "--out", str(out),
                 "--json", str(js), "--strict"]) == 0
    assert "Decision: **GO**" in out.read_text()
    data = json.loads(js.read_text())
    assert data["synthetic"] is True and len(data["cases"]) == 10
    assert main(["run", "--cases", str(EX), "--drafter", "mock:flawed", "--strict",
                 "--out", str(out)]) == 1


def test_cli_validate_check_prompt(tmp_path, capsys):
    assert main(["validate", "--cases", str(EX)]) == 0
    letter = tmp_path / "l.txt"
    letter.write_text(CASES.cases[0].reference_drafts["flawed"].text)
    assert main(["check", "--cases", str(EX), "--case-id", "PA-001", "--letter", str(letter)]) == 1
    assert "FAIL  citations" in capsys.readouterr().out
    assert main(["prompt", "--cases", str(EX), "--case-id", "PA-002"]) == 0
    assert main(["check", "--cases", str(EX), "--case-id", "NOPE", "--letter", str(letter)]) == 2
