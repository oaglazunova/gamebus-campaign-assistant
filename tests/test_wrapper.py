from __future__ import annotations

from pathlib import Path

import pandas as pd

from campaign_assistant.checker.schema import (
    CONSISTENCY,
    REACHABILITY,
    TARGETPOINTSREACHABLE,
    TTMSTRUCTURE,
)
from campaign_assistant.checker.wrapper import run_campaign_checks


class FakeChecker:
    def __init__(self, file_path: str) -> None:
        self.file_path = file_path
        self.gc = {
            "waves": pd.DataFrame(
                [
                    {
                        "id": 1,
                        "name": "Wave 1",
                        "start": pd.Timestamp("2025-01-01"),
                        "end": pd.Timestamp("2027-01-01"),
                    },
                    {
                        "id": 2,
                        "name": "Wave 2",
                        "start": pd.Timestamp("2020-01-01"),
                        "end": pd.Timestamp("2020-12-31"),
                    },
                ]
            )
        }
        self.errors = {
            TTMSTRUCTURE: [
                {
                    "visualization": {"id": 11, "description": "TTM Levels", "wave": 1},
                    "challenge": {"id": 101, "name": "Skilled"},
                    "error": "Wrong TTM successor.",
                }
            ],
            TARGETPOINTSREACHABLE: [
                {
                    "visualization": {"id": 22, "description": "Points", "wave": 2},
                    "challenge": {"id": 202, "name": "Gatekeeper"},
                    "error": "Target points cannot be reached.",
                }
            ],
            REACHABILITY: [],
            CONSISTENCY: [],
        }
        self._status = {
            TTMSTRUCTURE: "Failed",
            TARGETPOINTSREACHABLE: "Failed",
            REACHABILITY: "Passed",
            CONSISTENCY: "Passed",
        }

    def checkInitialAndTerminalReachability(self):
        return None

    def checkIntialandTerminalLevelConsistentSuccessors(self):
        return None

    def checkAllReachableChallengesAreInSameVisualizationAndLabel(self):
        return None

    def checkChallengeTargetPointsCanBeReached(self):
        return None

    def checkTasksHaveSecrets(self, _generate: bool):
        return None

    def checkTTMstructure(self):
        return None

    def spellcheckTaskAndChallenges(self):
        return None

    def checkResult(self, check_name: str) -> str:
        return self._status.get(check_name, "Passed")

    def getChallengeEditURL(self, vis, ch) -> str:
        return f"https://example.com/vis/{vis.get('id')}/challenge/{ch.get('id')}"


class CrashingChecker(FakeChecker):
    def checkTTMstructure(self):
        raise RuntimeError("Boom")


def test_run_campaign_checks_returns_expected_structure(monkeypatch, tmp_path):
    monkeypatch.setattr("campaign_assistant.checker.wrapper.CampaignChecker", FakeChecker)

    result = run_campaign_checks(
        file_path=tmp_path / "campaign.xlsx",
        checks=[REACHABILITY, CONSISTENCY, TARGETPOINTSREACHABLE, TTMSTRUCTURE],
        export_excel=False,
    )

    assert result["file_name"] == "campaign.xlsx"
    assert "summary" in result
    assert "issues_by_check" in result
    assert "prioritized_issues" in result
    assert "waves" in result

    summary = result["summary"]
    assert summary["total_issues"] == 2
    assert TTMSTRUCTURE in summary["failed_checks"]
    assert TARGETPOINTSREACHABLE in summary["failed_checks"]
    assert REACHABILITY in summary["passed_checks"]
    assert CONSISTENCY in summary["passed_checks"]

    assert len(result["issues_by_check"][TTMSTRUCTURE]) == 1
    assert len(result["issues_by_check"][TARGETPOINTSREACHABLE]) == 1


def test_prioritized_issues_put_active_high_severity_first(monkeypatch, tmp_path):
    monkeypatch.setattr("campaign_assistant.checker.wrapper.CampaignChecker", FakeChecker)

    result = run_campaign_checks(
        file_path=tmp_path / "campaign.xlsx",
        checks=[TARGETPOINTSREACHABLE, TTMSTRUCTURE],
        export_excel=False,
    )

    prioritized = result["prioritized_issues"]
    assert len(prioritized) == 2

    assert prioritized[0]["check"] == TTMSTRUCTURE
    assert prioritized[0]["active_wave"] is True
    assert prioritized[1]["check"] == TARGETPOINTSREACHABLE


def test_export_excel_creates_report(monkeypatch, tmp_path):
    monkeypatch.setattr("campaign_assistant.checker.wrapper.CampaignChecker", FakeChecker)
    monkeypatch.setattr(
        "campaign_assistant.checker.wrapper.tempfile.gettempdir",
        lambda: str(tmp_path),
    )

    result = run_campaign_checks(
        file_path=tmp_path / "campaign.xlsx",
        checks=[TARGETPOINTSREACHABLE, TTMSTRUCTURE],
        export_excel=True,
    )

    report_path = result["excel_report_path"]
    assert report_path is not None
    assert Path(report_path).exists()
    assert Path(report_path).suffix == ".xlsx"


def test_crashing_check_is_reported_as_error(monkeypatch, tmp_path):
    monkeypatch.setattr("campaign_assistant.checker.wrapper.CampaignChecker", CrashingChecker)

    result = run_campaign_checks(
        file_path=tmp_path / "campaign.xlsx",
        checks=[TTMSTRUCTURE],
        export_excel=False,
    )

    summary = result["summary"]
    assert TTMSTRUCTURE in summary["errored_checks"]
    assert result["notes"]
    assert "crashed" in result["notes"][0].lower()