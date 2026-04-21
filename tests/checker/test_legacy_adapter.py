from __future__ import annotations

from campaign_assistant.checker.legacy_adapter import LegacyCheckAdapter


class FakeChecker:
    pass


def test_legacy_adapter_exposes_no_legacy_check_runners():
    adapter = LegacyCheckAdapter(FakeChecker())

    runners = adapter.runners()

    assert runners == {}