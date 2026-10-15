"""Case schema for synthetic prior-authorization denial cases.

A case bundles everything a drafter is allowed to use:
  - the denial (letter text, reason code, unmet policy criteria, dates, identifiers)
  - the patient chart (the ONLY source of clinical facts)
  - the provided policy/criteria set (the ONLY citable policies)
and, optionally, reference drafts used by the offline mock drafter.

All shipped data is synthetic. Identifiers use the SYN- prefix so they cannot be mistaken
for real member, claim or policy numbers.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Criterion:
    id: str  # e.g. "SYN-LCD-1001-C2"
    text: str


@dataclass(frozen=True)
class Policy:
    id: str  # e.g. "SYN-LCD-1001"
    title: str
    criteria: tuple[Criterion, ...]


@dataclass(frozen=True)
class ChartFact:
    id: str
    date: str  # YYYY-MM-DD
    text: str


@dataclass(frozen=True)
class Chart:
    patient_id: str
    patient_name: str
    dob: str
    member_id: str
    provider_name: str
    facts: tuple[ChartFact, ...]


@dataclass(frozen=True)
class Denial:
    claim_id: str
    cpt: str
    icd10: str
    reason_code: str  # synthetic payer code, e.g. "SYN-D01"
    reason_text: str
    unmet_criteria: tuple[str, ...]  # criterion ids the payer says are not met
    reason_terms: tuple[str, ...]  # terms an adequate response should engage with
    applicable_policy: str  # policy id that governs this denial
    denial_date: str
    appeal_deadline: str
    letter_text: str


@dataclass(frozen=True)
class ReferenceDraft:
    text: str
    seeded_flaws: tuple[str, ...] = ()  # check names this draft is built to fail


@dataclass(frozen=True)
class Case:
    id: str
    title: str
    denial: Denial
    chart: Chart
    policies: tuple[Policy, ...]
    reference_drafts: dict[str, ReferenceDraft] = field(default_factory=dict)

    def policy(self, policy_id: str) -> Policy | None:
        return next((p for p in self.policies if p.id == policy_id), None)

    def criterion_ids(self) -> set[str]:
        return {c.id for p in self.policies for c in p.criteria}


@dataclass(frozen=True)
class CaseSet:
    label: str
    cases: tuple[Case, ...]


def _req(d: dict, keys: tuple[str, ...], where: str) -> None:
    missing = [k for k in keys if k not in d or d[k] in (None, "", [])]
    if missing:
        raise ValueError(f"{where}: missing {', '.join(missing)}")


def parse_case(d: dict) -> Case:
    cid = str(d.get("id", "?"))
    _req(d, ("id", "title", "denial", "chart", "policies"), f"case {cid}")
    dn, ch = d["denial"], d["chart"]
    _req(dn, ("claim_id", "cpt", "icd10", "reason_code", "reason_text", "unmet_criteria",
              "reason_terms", "applicable_policy", "denial_date", "appeal_deadline",
              "letter_text"), f"case {cid} denial")
    _req(ch, ("patient_id", "patient_name", "dob", "member_id", "provider_name", "facts"),
         f"case {cid} chart")
    policies = tuple(
        Policy(p["id"], p["title"], tuple(Criterion(c["id"], c["text"]) for c in p["criteria"]))
        for p in d["policies"]
    )
    case = Case(
        id=cid,
        title=str(d["title"]),
        denial=Denial(
            claim_id=dn["claim_id"], cpt=str(dn["cpt"]), icd10=dn["icd10"],
            reason_code=dn["reason_code"], reason_text=dn["reason_text"],
            unmet_criteria=tuple(dn["unmet_criteria"]), reason_terms=tuple(dn["reason_terms"]),
            applicable_policy=dn["applicable_policy"], denial_date=dn["denial_date"],
            appeal_deadline=dn["appeal_deadline"], letter_text=dn["letter_text"],
        ),
        chart=Chart(
            patient_id=ch["patient_id"], patient_name=ch["patient_name"], dob=ch["dob"],
            member_id=ch["member_id"], provider_name=ch["provider_name"],
            facts=tuple(ChartFact(f["id"], f["date"], f["text"]) for f in ch["facts"]),
        ),
        policies=policies,
        reference_drafts={
            k: ReferenceDraft(v["text"], tuple(v.get("seeded_flaws", [])))
            for k, v in d.get("reference_drafts", {}).items()
        },
    )
    if case.policy(case.denial.applicable_policy) is None:
        raise ValueError(f"case {cid}: applicable_policy not in the provided policy set")
    unknown = set(case.denial.unmet_criteria) - case.criterion_ids()
    if unknown:
        raise ValueError(f"case {cid}: unmet criteria not in policy set: {sorted(unknown)}")
    return case


def load_cases(path: str | Path) -> CaseSet:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    cases = tuple(parse_case(d) for d in data["cases"])
    ids = [c.id for c in cases]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        raise ValueError(f"duplicate case ids: {dupes}")
    if not cases:
        raise ValueError("no cases found")
    return CaseSet(label=str(data.get("label", "")), cases=cases)
