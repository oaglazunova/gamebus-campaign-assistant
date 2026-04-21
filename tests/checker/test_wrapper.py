from __future__ import annotations

from pathlib import Path

import pandas as pd

from campaign_assistant.checker.schema import (
	CONSISTENCY,
	REACHABILITY,
	SECRETS,
	SPELLCHECKER,
	TARGETPOINTSREACHABLE,
	TTMSTRUCTURE,
	VISUALIZATIONINTERN,
)
from campaign_assistant.checker.wrapper import run_campaign_checks



def _native_ttm_crash(*args, **kwargs):
    raise RuntimeError("Boom")


def _native_ttm_pass():
    return {"status": "Passed", "issues": [], "notes": []}


def _native_ttm_fail_active():
    from campaign_assistant.checker.schema import Issue, TTMSTRUCTURE

    return {
        "status": "Failed",
        "issues": [
            Issue(
                check=TTMSTRUCTURE,
                severity="high",
                active_wave=True,
                visualization_id=11,
                visualization="TTM Levels",
                challenge_id=101,
                challenge="Skilled",
                wave_id=1,
                message="Wrong TTM successor.",
                url="https://example.com/vis/11/challenge/101",
            )
        ],
        "notes": [],
    }


def _native_targetpoints_pass():
	return {"status": "Passed", "issues": [], "notes": []}


def _native_targetpoints_fail_inactive():
	from campaign_assistant.checker.schema import Issue, TARGETPOINTSREACHABLE

	return {
		"status": "Failed",
		"issues": [
			Issue(
				check=TARGETPOINTSREACHABLE,
				severity="high",
				active_wave=False,
				visualization_id=66,
				visualization="Target Points Viz",
				challenge_id=666,
				challenge="Challenge Target",
				wave_id=2,
				message="Challenge target points (100.0) cannot be reached with tasks (max reachable is 60.0)",
				url="https://example.com/targetpoints",
			)
		],
		"notes": [],
	}



def _native_spellchecker_pass():
	return {"status": "Passed", "issues": [], "notes": []}


def _native_spellchecker_fail_active():
	from campaign_assistant.checker.schema import Issue, SPELLCHECKER

	return {
		"status": "Failed",
		"issues": [
			Issue(
				check=SPELLCHECKER,
				severity="low",
				active_wave=True,
				visualization_id=55,
				visualization="Spellchecker Viz",
				challenge_id=555,
				challenge="Challenge Spell",
				wave_id=1,
				message="Name of task is faulty 'Wrng Wrd'. Proposed correction is \n'Correct Word'",
				url="https://example.com/spellchecker",
			)
		],
		"notes": [],
	}

def _native_secrets_pass():
	return {"status": "Passed", "issues": [], "notes": []}


def _native_secrets_fail_active():
	from campaign_assistant.checker.schema import Issue, SECRETS

	return {
		"status": "Failed",
		"issues": [
			Issue(
				check=SECRETS,
				severity="medium",
				active_wave=True,
				visualization_id=44,
				visualization="Secrets Viz",
				challenge_id=444,
				challenge="Challenge Secret",
				wave_id=1,
				message="Task 'Drink Water' has no secret. Proposing [SECRET, EQUAL, Drink-Water] at column 'conditions' in row=0 (name=Drink Water)",
				url="https://example.com/secrets",
			)
		],
		"notes": [],
	}


def _native_visualizationintern_pass():
	return {"status": "Passed", "issues": [], "notes": []}


def _native_visualizationintern_fail_active():
	from campaign_assistant.checker.schema import Issue, VISUALIZATIONINTERN

	return {
		"status": "Failed",
		"issues": [
			Issue(
				check=VISUALIZATIONINTERN,
				severity="high",
				active_wave=True,
				visualization_id=33,
				visualization="Visualization Intern Viz",
				challenge_id=321,
				challenge="Cross Visualization Terminal",
				wave_id=1,
				message="Reachable Challenge from some initial level is not in same visualization or not with same label:\n"
						"Initial challenge visualization = '100'; reachable challenge visualization = '200'\n"
						"Initial challenge labels = 'A'; reachable challenge labels = 'A'\n",
				url="https://example.com/visualizationintern",
			)
		],
		"notes": [],
	}


def _native_consistency_pass():
	return {"status": "Passed", "issues": [], "notes": []}


def _native_consistency_fail_active():
	from campaign_assistant.checker.schema import CONSISTENCY, Issue

	return {
		"status": "Failed",
		"issues": [
			Issue(
				check=CONSISTENCY,
				severity="high",
				active_wave=True,
				visualization_id=22,
				visualization="Consistency Viz",
				challenge_id=123,
				challenge="Broken Initial",
				wave_id=1,
				message="Initial challenge does not lead to itself on failure 999",
				url="https://example.com/consistency",
			)
		],
		"notes": [],
	}


def _native_reachability_pass():
	return {"status": "Passed", "issues": [], "notes": []}


def _native_reachability_fail_active():
	from campaign_assistant.checker.schema import Issue, REACHABILITY

	return {
		"status": "Failed",
		"issues": [
			Issue(
				check=REACHABILITY,
				severity="high",
				active_wave=True,
				visualization_id=11,
				visualization="Reachability Viz",
				challenge_id=999,
				challenge="Broken Start",
				wave_id=1,
				message="Initial Challenge without terminal challenge",
				url="https://example.com/reachability",
			)
		],
		"notes": [],
	}

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

	def checkTargetPointsReachable(self):
		return self.checkChallengeTargetPointsCanBeReached()

	def checkTasksHaveSecrets(self, _generate: bool):
		return None

	def checkTTMstructure(self):
		return None

	def checkTTMStructure(self):
		return self.checkTTMstructure()

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
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_reachability_tables",
		lambda *args, **kwargs: _native_reachability_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_consistency_tables",
		lambda *args, **kwargs: _native_consistency_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_visualizationintern_tables",
		lambda *args, **kwargs: _native_visualizationintern_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_secrets_tables",
		lambda *args, **kwargs: _native_secrets_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_spellchecker_tables",
		lambda *args, **kwargs: _native_spellchecker_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_targetpointsreachable_tables",
		lambda *args, **kwargs: _native_targetpoints_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_ttm_tables",
		lambda *args, **kwargs: _native_ttm_pass(),
	)

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

	assert summary["total_issues"] == 0
	assert TTMSTRUCTURE in summary["passed_checks"]
	assert TARGETPOINTSREACHABLE in summary["passed_checks"]
	assert REACHABILITY in summary["passed_checks"]
	assert CONSISTENCY in summary["passed_checks"]

	assert len(result["issues_by_check"][TTMSTRUCTURE]) == 0
	assert len(result["issues_by_check"][TARGETPOINTSREACHABLE]) == 0



def test_prioritized_issues_put_active_high_severity_first(monkeypatch, tmp_path):
	monkeypatch.setattr("campaign_assistant.checker.wrapper.CampaignChecker", FakeChecker)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_reachability_tables",
		lambda *args, **kwargs: _native_reachability_fail_active(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_consistency_tables",
		lambda *args, **kwargs: _native_consistency_fail_active(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_visualizationintern_tables",
		lambda *args, **kwargs: _native_visualizationintern_fail_active(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_secrets_tables",
		lambda *args, **kwargs: _native_secrets_fail_active(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_spellchecker_tables",
		lambda *args, **kwargs: _native_spellchecker_fail_active(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_targetpointsreachable_tables",
		lambda *args, **kwargs: _native_targetpoints_fail_inactive(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_ttm_tables",
		lambda *args, **kwargs: _native_ttm_fail_active(),
	)

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
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_reachability_tables",
		lambda *args, **kwargs: _native_reachability_fail_active(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_consistency_tables",
		lambda *args, **kwargs: _native_consistency_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_visualizationintern_tables",
		lambda *args, **kwargs: _native_visualizationintern_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_secrets_tables",
		lambda *args, **kwargs: _native_secrets_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_spellchecker_tables",
		lambda *args, **kwargs: _native_spellchecker_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_targetpointsreachable_tables",
		lambda *args, **kwargs: _native_targetpoints_fail_inactive(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_ttm_tables",
		lambda *args, **kwargs: _native_ttm_pass(),
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

	# Verify legacy format
	df = pd.read_excel(report_path, sheet_name="Errors")
	assert list(df.columns) == ["Kind", "Visualization", "Challenge", "Error", "URL"]
	assert len(df) == 1
	assert df.iloc[0]["Kind"] == TARGETPOINTSREACHABLE
	assert df.iloc[0]["Visualization"] == "Target Points Viz"
	assert df.iloc[0]["Challenge"] == "Challenge Target"
	assert "cannot be reached with tasks" in df.iloc[0]["Error"]
	assert "https://example.com/targetpoints" in df.iloc[0]["URL"]





def test_crashing_check_is_reported_as_error(monkeypatch, tmp_path):
	monkeypatch.setattr("campaign_assistant.checker.wrapper.CampaignChecker", CrashingChecker)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_reachability_tables",
		lambda *args, **kwargs: _native_reachability_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_consistency_tables",
		lambda *args, **kwargs: _native_consistency_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_visualizationintern_tables",
		lambda *args, **kwargs: _native_visualizationintern_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_secrets_tables",
		lambda *args, **kwargs: _native_secrets_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_spellchecker_tables",
		lambda *args, **kwargs: _native_spellchecker_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_targetpointsreachable_tables",
		lambda *args, **kwargs: _native_targetpoints_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_ttm_tables",
		_native_ttm_crash,
	)

	result = run_campaign_checks(
		file_path=tmp_path / "campaign.xlsx",
		checks=[TTMSTRUCTURE],
		export_excel=False,
	)

	summary = result["summary"]
	assert TTMSTRUCTURE in summary["errored_checks"]
	assert result["notes"]
	assert "crashed" in result["notes"][0].lower()


class ReachabilityMustNotBeCalledChecker(FakeChecker):
	def checkInitialAndTerminalReachability(self):
		raise AssertionError("legacy reachability should not be called")


def test_wrapper_uses_native_reachability_path(monkeypatch, tmp_path):
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.CampaignChecker",
		ReachabilityMustNotBeCalledChecker,
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_reachability_tables",
		lambda *args, **kwargs: _native_reachability_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_consistency_tables",
		lambda *args, **kwargs: _native_consistency_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_visualizationintern_tables",
		lambda *args, **kwargs: _native_visualizationintern_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_secrets_tables",
		lambda *args, **kwargs: _native_secrets_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_spellchecker_tables",
		lambda *args, **kwargs: _native_spellchecker_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_targetpointsreachable_tables",
		lambda *args, **kwargs: _native_targetpoints_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_ttm_tables",
		lambda *args, **kwargs: _native_ttm_fail_active(),
	)

	result = run_campaign_checks(
		file_path=tmp_path / "campaign.xlsx",
		checks=[REACHABILITY, TTMSTRUCTURE],
		export_excel=False,
	)

	summary = result["summary"]
	assert REACHABILITY in summary["passed_checks"]
	assert TTMSTRUCTURE in summary["failed_checks"]


class ConsistencyMustNotBeCalledChecker(FakeChecker):
	def checkIntialandTerminalLevelConsistentSuccessors(self):
		raise AssertionError("legacy consistency should not be called")


def test_wrapper_uses_native_consistency_path(monkeypatch, tmp_path):
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.CampaignChecker",
		ConsistencyMustNotBeCalledChecker,
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_reachability_tables",
		lambda *args, **kwargs: _native_reachability_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_consistency_tables",
		lambda *args, **kwargs: _native_consistency_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_visualizationintern_tables",
		lambda *args, **kwargs: _native_visualizationintern_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_secrets_tables",
		lambda *args, **kwargs: _native_secrets_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_spellchecker_tables",
		lambda *args, **kwargs: _native_spellchecker_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_targetpointsreachable_tables",
		lambda *args, **kwargs: _native_targetpoints_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_ttm_tables",
		lambda *args, **kwargs: _native_ttm_fail_active(),
	)

	result = run_campaign_checks(
		file_path=tmp_path / "campaign.xlsx",
		checks=[CONSISTENCY, TTMSTRUCTURE],
		export_excel=False,
	)

	summary = result["summary"]
	assert CONSISTENCY in summary["passed_checks"]
	assert TTMSTRUCTURE in summary["failed_checks"]


class VisualizationInternMustNotBeCalledChecker(FakeChecker):
	def checkAllReachableChallengesAreInSameVisualizationAndLabel(self):
		raise AssertionError("legacy visualizationintern should not be called")


def test_wrapper_uses_native_visualizationintern_path(monkeypatch, tmp_path):
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.CampaignChecker",
		VisualizationInternMustNotBeCalledChecker,
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_reachability_tables",
		lambda *args, **kwargs: _native_reachability_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_consistency_tables",
		lambda *args, **kwargs: _native_consistency_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_visualizationintern_tables",
		lambda *args, **kwargs: _native_visualizationintern_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_secrets_tables",
		lambda *args, **kwargs: _native_secrets_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_spellchecker_tables",
		lambda *args, **kwargs: _native_spellchecker_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_targetpointsreachable_tables",
		lambda *args, **kwargs: _native_targetpoints_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_ttm_tables",
		lambda *args, **kwargs: _native_ttm_fail_active(),
	)

	result = run_campaign_checks(
		file_path=tmp_path / "campaign.xlsx",
		checks=[VISUALIZATIONINTERN, TTMSTRUCTURE],
		export_excel=False,
	)

	summary = result["summary"]
	assert VISUALIZATIONINTERN in summary["passed_checks"]
	assert TTMSTRUCTURE in summary["failed_checks"]


class SecretsMustNotBeCalledChecker(FakeChecker):
	def checkTasksHaveSecrets(self, _fixemptysecrets):
		raise AssertionError("legacy secrets should not be called")


def test_wrapper_uses_native_secrets_path(monkeypatch, tmp_path):
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.CampaignChecker",
		SecretsMustNotBeCalledChecker,
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_reachability_tables",
		lambda *args, **kwargs: _native_reachability_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_consistency_tables",
		lambda *args, **kwargs: _native_consistency_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_visualizationintern_tables",
		lambda *args, **kwargs: _native_visualizationintern_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_secrets_tables",
		lambda *args, **kwargs: _native_secrets_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_spellchecker_tables",
		lambda *args, **kwargs: _native_spellchecker_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_targetpointsreachable_tables",
		lambda *args, **kwargs: _native_targetpoints_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_ttm_tables",
		lambda *args, **kwargs: _native_ttm_fail_active(),
	)

	result = run_campaign_checks(
		file_path=tmp_path / "campaign.xlsx",
		checks=[SECRETS, TTMSTRUCTURE],
		export_excel=False,
	)

	summary = result["summary"]
	assert SECRETS in summary["passed_checks"]
	assert TTMSTRUCTURE in summary["failed_checks"]


class SpellcheckerMustNotBeCalledChecker(FakeChecker):
	def spellcheckTaskAndChallenges(self):
		raise AssertionError("legacy spellchecker should not be called")


def test_wrapper_uses_native_spellchecker_path(monkeypatch, tmp_path):
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.CampaignChecker",
		SpellcheckerMustNotBeCalledChecker,
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_reachability_tables",
		lambda *args, **kwargs: _native_reachability_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_consistency_tables",
		lambda *args, **kwargs: _native_consistency_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_visualizationintern_tables",
		lambda *args, **kwargs: _native_visualizationintern_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_secrets_tables",
		lambda *args, **kwargs: _native_secrets_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_spellchecker_tables",
		lambda *args, **kwargs: _native_spellchecker_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_targetpointsreachable_tables",
		lambda *args, **kwargs: _native_targetpoints_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_ttm_tables",
		lambda *args, **kwargs: _native_ttm_fail_active(),
	)

	result = run_campaign_checks(
		file_path=tmp_path / "campaign.xlsx",
		checks=[SPELLCHECKER, TTMSTRUCTURE],
		export_excel=False,
	)

	summary = result["summary"]
	assert SPELLCHECKER in summary["passed_checks"]
	assert TTMSTRUCTURE in summary["failed_checks"]



class RemainingLegacyChecksChecker(FakeChecker):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.called_targetpoints = False
		self.called_ttm = False

	def checkChallengeTargetPointsCanBeReached(self):
		self.called_targetpoints = True
		return super().checkChallengeTargetPointsCanBeReached()

	def checkTargetPointsReachable(self):
		self.called_targetpoints = True
		return super().checkTargetPointsReachable()

	def checkTTMstructure(self):
		self.called_ttm = True
		return super().checkTTMstructure()

	def checkTTMStructure(self):
		self.called_ttm = True
		return super().checkTTMStructure()



class RemainingLegacyTTMOnlyChecker(FakeChecker):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.called_ttm = False

	def checkTTMstructure(self):
		self.called_ttm = True
		return super().checkTTMstructure()

	def checkTTMStructure(self):
		self.called_ttm = True
		return super().checkTTMStructure()




class TargetPointsMustNotBeCalledChecker(FakeChecker):
	def checkChallengeTargetPointsCanBeReached(self):
		raise AssertionError("legacy targetpointsreachable should not be called")

	def checkTargetPointsReachable(self):
		raise AssertionError("legacy targetpointsreachable alias should not be called")


def test_wrapper_uses_native_targetpointsreachable_path(monkeypatch, tmp_path):
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.CampaignChecker",
		TargetPointsMustNotBeCalledChecker,
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_reachability_tables",
		lambda *args, **kwargs: _native_reachability_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_consistency_tables",
		lambda *args, **kwargs: _native_consistency_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_visualizationintern_tables",
		lambda *args, **kwargs: _native_visualizationintern_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_secrets_tables",
		lambda *args, **kwargs: _native_secrets_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_spellchecker_tables",
		lambda *args, **kwargs: _native_spellchecker_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_targetpointsreachable_tables",
		lambda *args, **kwargs: _native_targetpoints_pass(),
	)
	monkeypatch.setattr(
		"campaign_assistant.checker.wrapper.run_native_ttm_tables",
		lambda *args, **kwargs: _native_ttm_fail_active(),
	)

	result = run_campaign_checks(
		file_path=tmp_path / "campaign.xlsx",
		checks=[TARGETPOINTSREACHABLE, TTMSTRUCTURE],
		export_excel=False,
	)

	summary = result["summary"]
	assert TARGETPOINTSREACHABLE in summary["passed_checks"]
	assert TTMSTRUCTURE in summary["failed_checks"]


class TTMMustNotBeCalledChecker(FakeChecker):
    def checkTTMstructure(self):
        raise AssertionError("legacy ttm should not be called")

    def checkTTMStructure(self):
        raise AssertionError("legacy ttm alias should not be called")


def test_wrapper_uses_native_ttm_path(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "campaign_assistant.checker.wrapper.CampaignChecker",
        TTMMustNotBeCalledChecker,
    )
    monkeypatch.setattr(
        "campaign_assistant.checker.wrapper.run_native_reachability_tables",
        lambda *args, **kwargs: _native_reachability_pass(),
    )
    monkeypatch.setattr(
        "campaign_assistant.checker.wrapper.run_native_consistency_tables",
        lambda *args, **kwargs: _native_consistency_pass(),
    )
    monkeypatch.setattr(
        "campaign_assistant.checker.wrapper.run_native_visualizationintern_tables",
        lambda *args, **kwargs: _native_visualizationintern_pass(),
    )
    monkeypatch.setattr(
        "campaign_assistant.checker.wrapper.run_native_secrets_tables",
        lambda *args, **kwargs: _native_secrets_pass(),
    )
    monkeypatch.setattr(
        "campaign_assistant.checker.wrapper.run_native_spellchecker_tables",
        lambda *args, **kwargs: _native_spellchecker_pass(),
    )
    monkeypatch.setattr(
        "campaign_assistant.checker.wrapper.run_native_targetpointsreachable_tables",
        lambda *args, **kwargs: _native_targetpoints_pass(),
    )
    monkeypatch.setattr(
        "campaign_assistant.checker.wrapper.run_native_ttm_tables",
        lambda *args, **kwargs: _native_ttm_fail_active(),
    )

    result = run_campaign_checks(
        file_path=tmp_path / "campaign.xlsx",
        checks=[TARGETPOINTSREACHABLE, TTMSTRUCTURE],
        export_excel=False,
    )

    summary = result["summary"]
    assert TARGETPOINTSREACHABLE in summary["passed_checks"]
    assert TTMSTRUCTURE in summary["failed_checks"]
