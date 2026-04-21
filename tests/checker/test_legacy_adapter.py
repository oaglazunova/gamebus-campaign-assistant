from __future__ import annotations

from campaign_assistant.checker.legacy_adapter import LegacyCheckAdapter
from campaign_assistant.checker.schema import TTMSTRUCTURE


class FakeChecker:
    def __init__(self):
        self.called = []

    def checkTTMStructure(self):
        self.called.append("ttm")


def test_legacy_adapter_exposes_only_remaining_legacy_checks():
    adapter = LegacyCheckAdapter(FakeChecker())

    runners = adapter.runners()

    assert set(runners.keys()) == {TTMSTRUCTURE}


def test_legacy_adapter_runs_ttm():
    checker = FakeChecker()
    adapter = LegacyCheckAdapter(checker)

    adapter.runners()[TTMSTRUCTURE]()

    assert checker.called == ["ttm"]