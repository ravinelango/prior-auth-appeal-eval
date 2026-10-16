"""Unit tests for the OpenAI-compatible drafter adapter.

No network and no real SDK: a fake ``openai`` module is injected into sys.modules so we
can check the request the adapter sends and that the completion text is returned as the
letter.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from prior_auth_eval.drafters import OpenAIDrafter, build_prompt, get_drafter
from prior_auth_eval.schema import load_cases

CASES = load_cases(Path(__file__).parents[1] / "examples" / "synthetic_cases.json")


class _Recorder:
    def __init__(self, reply):
        self.reply = reply
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.reply


@pytest.fixture
def fake_openai(monkeypatch):
    recorder = _Recorder(None)
    clients = []

    class FakeOpenAI:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.chat = types.SimpleNamespace(completions=recorder)
            clients.append(self)

    mod = types.ModuleType("openai")
    mod.OpenAI = FakeOpenAI
    monkeypatch.setitem(sys.modules, "openai", mod)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)

    def set_reply(text):
        msg = types.SimpleNamespace(content=text)
        recorder.reply = types.SimpleNamespace(choices=[types.SimpleNamespace(message=msg)])

    recorder.set_reply = set_reply
    recorder.clients = clients
    return recorder


def test_openai_adapter_sends_prompt_and_returns_letter(fake_openai):
    letter = "Date: 2026-01-15\nRE: Appeal of denial, claim SYN-CLM-1\nSincerely, Dr X, NPI 1"
    fake_openai.set_reply(letter)
    case = CASES.cases[0]
    drafter = OpenAIDrafter("gpt-test")

    assert drafter.name == "openai:gpt-test"
    assert drafter.draft(case) == letter

    call = fake_openai.calls[0]
    assert call["model"] == "gpt-test"
    assert call["temperature"] == 0.0
    content = call["messages"][0]["content"]
    assert content == build_prompt(case)
    assert "Use ONLY the facts" in content
    assert case.chart.patient_name in content
    assert case.denial.claim_id in content


def test_openai_adapter_uses_base_url_and_default_model(fake_openai, monkeypatch):
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.test/v1")
    fake_openai.set_reply("ok letter")
    drafter = get_drafter("openai")
    assert drafter.name == "openai:gpt-4o-mini"
    assert drafter.draft(CASES.cases[0]) == "ok letter"
    assert fake_openai.clients[0].kwargs == {"base_url": "https://example.test/v1"}
    assert fake_openai.calls[0]["model"] == "gpt-4o-mini"


def test_openai_adapter_empty_content_is_error(fake_openai):
    fake_openai.set_reply("   ")
    with pytest.raises(ValueError, match="empty completion"):
        OpenAIDrafter("gpt-test").draft(CASES.cases[0])


def test_openai_missing_key_fails_fast(fake_openai, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY")
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        get_drafter("openai:gpt-test")


def test_get_drafter_openai_specs(fake_openai):
    fake_openai.set_reply("x")
    assert get_drafter("openai").name == "openai:gpt-4o-mini"
    assert get_drafter("openai:my-model").name == "openai:my-model"
