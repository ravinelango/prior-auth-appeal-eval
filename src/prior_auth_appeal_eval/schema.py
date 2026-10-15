"""Case schema for synthetic prior-auth denial cases, with a strict loader."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

CASE_ID = re.compile(r"^PA-\d{3}$")
FACT_ID = re.compile(r"^F\d+$")
REQUIRED_KEYS = (
    "case_id",
    "synthetic",
    "patient",
    "request",
    "denial",
    "chart_facts",
    "policy_ids",
    "required_elements",
)


class CaseError(ValueError):
    """A case file is malformed."""


@dataclass(frozen=True)
class Patient:
    name: str
    dob: str
    member_id: str


@dataclass(frozen=True)
class Request:
    cpt: tuple[str, ...]
    icd10: tuple[str, ...]


@dataclass(frozen=True)
class Denial:
    reason_code: str
    reason_text: str
    cited_policy: str


@dataclass(frozen=True)
class ChartFact:
    fact_id: str
    text: str


@dataclass(frozen=True)
class Case:
    case_id: str
    patient: Patient
    request: Request
    denial: Denial
    chart_facts: tuple[ChartFact, ...]
    policy_ids: tuple[str, ...]
    required_elements: tuple[str, ...]

    def fact(self, fact_id: str) -> ChartFact | None:
        return next((f for f in self.chart_facts if f.fact_id == fact_id), None)


def parse_case(data: dict) -> Case:
    missing = [k for k in REQUIRED_KEYS if k not in data]
    if missing:
        raise CaseError(f"missing keys: {', '.join(missing)}")
    if data["synthetic"] is not True:
        raise CaseError("cases must be marked synthetic: true")
    if not CASE_ID.match(data["case_id"]):
        raise CaseError(f"bad case_id {data['case_id']!r}")

    facts = tuple(ChartFact(f["id"], f["text"]) for f in data["chart_facts"])
    ids = [f.fact_id for f in facts]
    if not facts:
        raise CaseError("chart_facts is empty")
    if len(set(ids)) != len(ids) or not all(FACT_ID.match(i) for i in ids):
        raise CaseError(f"fact ids must be unique F<n>: {ids}")

    denial = Denial(**data["denial"])
    policy_ids = tuple(data["policy_ids"])
    if denial.cited_policy not in policy_ids:
        raise CaseError("denial.cited_policy must be one of policy_ids")

    return Case(
        case_id=data["case_id"],
        patient=Patient(**data["patient"]),
        request=Request(tuple(data["request"]["cpt"]), tuple(data["request"]["icd10"])),
        denial=denial,
        chart_facts=facts,
        policy_ids=policy_ids,
        required_elements=tuple(data["required_elements"]),
    )


def load_case(path: str | Path) -> Case:
    with open(path, encoding="utf-8") as fh:
        return parse_case(json.load(fh))


def load_policies(path: str | Path) -> dict[str, dict]:
    """Load the policy set; each policy maps criterion ids (C1, C2, ...) to text."""
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)["policies"]


def load_cases(directory: str | Path) -> list[Case]:
    """Load every PA-*.json case and check its policies exist in policies.json."""
    directory = Path(directory)
    policies = load_policies(directory / "policies.json")
    cases = [load_case(p) for p in sorted(directory.glob("PA-*.json"))]
    for case in cases:
        unknown = [p for p in case.policy_ids if p not in policies]
        if unknown:
            raise CaseError(f"{case.case_id}: unknown policies {unknown}")
    return cases
