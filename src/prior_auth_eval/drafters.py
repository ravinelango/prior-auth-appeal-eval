"""Pluggable appeal drafters.

A drafter takes a Case and returns the appeal letter text. The mock drafter replays the
reference drafts shipped with each case, so the whole pipeline runs offline and
deterministically. ``openai[:MODEL]`` posts to an OpenAI-compatible chat endpoint when you
have a key; ``files:DIR`` reads letters you produced elsewhere.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol

from .schema import Case

PROMPT = """You are drafting a prior-authorization appeal letter for the provider.
Use ONLY the facts in the chart and ONLY the policies in the provided policy set.
Do not invent clinical facts, policy numbers or criteria.
Include only the identifiers the appeal needs (minimum necessary): no SSNs, phone numbers,
email addresses or street addresses that are not in the chart or denial letter.

Denial letter:
{denial}

Patient chart (the only source of clinical facts):
{chart}

Provided policies (the only citable policies):
{policies}

Format exactly:
Date: YYYY-MM-DD
RE: Appeal of denial, claim <claim id>
Patient: <name> | Member ID: <member id> | DOB: <dob>
Requested service: CPT <code> | Diagnosis: ICD-10 <code>

## Response to denial reason
(cite each unmet criterion id; answer the stated denial reason directly)
## Clinical summary
(one "- " bullet per clinical assertion, taken from the chart)
## Policy basis
(cite provided policy ids; end with an explicit request to overturn the denial)
## Enclosures
(- bullets)

Sincerely,
<clinician>, NPI <number>
"""


class Drafter(Protocol):
    name: str

    def draft(self, case: Case) -> str: ...


def build_prompt(case: Case) -> str:
    chart = "\n".join(f"- {f.date}: {f.text}" for f in case.chart.facts)
    pols = "\n".join(
        f"{p.id} {p.title}\n" + "\n".join(f"  {c.id}: {c.text}" for c in p.criteria)
        for p in case.policies)
    header = (f"Patient: {case.chart.patient_name} | Member ID: {case.chart.member_id} | "
              f"DOB: {case.chart.dob} | Provider: {case.chart.provider_name} | "
              f"Claim {case.denial.claim_id} | CPT {case.denial.cpt} | ICD-10 {case.denial.icd10} "
              f"| Appeal deadline {case.denial.appeal_deadline}")
    return PROMPT.format(denial=f"{header}\n{case.denial.letter_text}", chart=chart, policies=pols)


class MockDrafter:
    """Replays a case's reference draft ('good' or 'flawed'). Not a model."""

    def __init__(self, variant: str = "good"):
        if variant not in ("good", "flawed"):
            raise ValueError("mock variant must be 'good' or 'flawed'")
        self.variant = variant
        self.name = f"mock:{variant}"

    def draft(self, case: Case) -> str:
        return case.reference_drafts[self.variant].text

    def seeded_flaws(self, case: Case) -> tuple[str, ...]:
        return case.reference_drafts[self.variant].seeded_flaws


class FilesDrafter:
    """Reads <DIR>/<case id>.txt, e.g. letters you generated with a real model elsewhere."""

    def __init__(self, directory: str):
        self.dir = Path(directory)
        self.name = f"files:{directory}"

    def draft(self, case: Case) -> str:
        path = self.dir / f"{case.id}.txt"
        if not path.exists():
            raise FileNotFoundError(f"no draft for {case.id}: expected {path}")
        return path.read_text(encoding="utf-8")


class OpenAIDrafter:
    """Posts chat completions to an OpenAI-compatible API.

    Needs ``OPENAI_API_KEY``. Optional ``OPENAI_BASE_URL`` points at a compatible
    endpoint (Azure OpenAI proxy, local server, etc.). The ``openai`` package is an
    optional dependency (``pip install -e '.[openai]'``).
    """

    DEFAULT_MODEL = "gpt-4o-mini"

    def __init__(self, model: str = DEFAULT_MODEL, temperature: float = 0.0):
        from openai import OpenAI  # optional dependency

        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not set")
        kwargs: dict[str, str] = {}
        base = os.environ.get("OPENAI_BASE_URL")
        if base:
            kwargs["base_url"] = base
        self.client = OpenAI(**kwargs)
        self.model = model
        self.temperature = temperature
        self.name = f"openai:{model}"

    def draft(self, case: Case) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            messages=[{"role": "user", "content": build_prompt(case)}],
        )
        text = (resp.choices[0].message.content or "").strip()
        if not text:
            raise ValueError(f"{self.name}: empty completion content")
        return text


def get_drafter(spec: str) -> Drafter:
    """spec: 'mock[:good|flawed]', 'files:DIR', or 'openai[:MODEL]'."""
    kind, _, arg = spec.partition(":")
    if kind == "mock":
        return MockDrafter(arg or "good")
    if kind == "files" and arg:
        return FilesDrafter(arg)
    if kind == "openai":
        return OpenAIDrafter(arg or OpenAIDrafter.DEFAULT_MODEL)
    raise ValueError(
        f"unknown drafter {spec!r} (use mock:good, mock:flawed, files:DIR or openai[:MODEL])"
    )
