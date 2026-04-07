from __future__ import annotations

import importlib.util
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

# ---------------------------------------------------------
# Constants: keep the same names as the legacy checker uses
# ---------------------------------------------------------
CONSISTENCY = "consistency"
VISUALIZATIONINTERN = "visualizationintern"
REACHABILITY = "reachability"
TARGETPOINTSREACHABLE = "targetpointsreachable"
SECRETS = "secrets"
SPELLCHECKER = "spellchecker"
TTMSTRUCTURE = "ttm"

DEFAULT_CHECKS = [
    REACHABILITY,
    CONSISTENCY,
    VISUALIZATIONINTERN,
    TARGETPOINTSREACHABLE,
    SECRETS,
    TTMSTRUCTURE,
]

SEVERITY_BY_CHECK = {
    TTMSTRUCTURE: "high",
    TARGETPOINTSREACHABLE: "high",
    REACHABILITY: "high",
    CONSISTENCY: "high",
    VISUALIZATIONINTERN: "medium",
    SECRETS: "medium",
    SPELLCHECKER: "low",
}

SEVERITY_SCORE = {"high": 300, "medium": 200, "low": 100}

# ---------------------------------------------------------
# Load the legacy checker dynamically from the same folder
# ---------------------------------------------------------
HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
LEGACY_FILE = PROJECT_ROOT / "legacy_checker" / "gamebus_campaign_checker.py"

spec = importlib.util.spec_from_file_location("legacy_checker", LEGACY_FILE)
legacy_checker = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
spec.loader.exec_module(legacy_checker)

CampaignChecker = legacy_checker.CampaignChecker


# ---------------------------------------------------------
# Runtime patches for a few legacy checker quirks
# We do this here so the original checker file can stay
# untouched.
# ---------------------------------------------------------
def _patch_legacy_checker() -> None:
    # Some legacy code calls addErrors instead of addError.
    if not hasattr(CampaignChecker, "addErrors"):
        CampaignChecker.addErrors = CampaignChecker.addError

    def reachable_challenges_intern(self, challenge, visitedids=None):
        if visitedids is None:
            visitedids = []
        if challenge is None:
            return [], visitedids

        cid = challenge["id"]
        if cid in visitedids:
            return [], visitedids

        visitedids = [*visitedids, cid]

        if self.isChallengeTerminalLevel(challenge):
            return [challenge], visitedids

        result = []
        nexts = [
            self.getChallengeSuccessChallenge(challenge),
            self.getChallengeFailureChallenge(challenge),
        ]
        nexts = [n for n in nexts if n is not None and n["id"] not in visitedids]

        for c in nexts:
            res, visitedids = reachable_challenges_intern(self, c, visitedids)
            result.extend(res)

        return result, visitedids

    def reachable(self, fromchallenge, tochallenge, successonly=True, visitedids=None):
        if visitedids is None:
            visitedids = []
        if fromchallenge is None or tochallenge is None:
            return False
        if self.challengeEqual(fromchallenge, tochallenge):
            return True

        visitedids = [*visitedids, fromchallenge["id"]]

        nexts = []
        if not self.isChallengeTerminalLevel(fromchallenge):
            nexts.append(self.getChallengeSuccessChallenge(fromchallenge))
        if not successonly:
            nexts.append(self.getChallengeFailureChallenge(fromchallenge))

        nexts = [n for n in nexts if n is not None and n["id"] not in visitedids]

        return any(
            reachable(self, c, tochallenge, successonly=successonly, visitedids=visitedids)
            for c in nexts
        )

    CampaignChecker.reachableChallengesIntern = reachable_challenges_intern
    CampaignChecker.reachable = reachable


_patch_legacy_checker()


# ---------------------------------------------------------
# Normalized issue model
# ---------------------------------------------------------
@dataclass
class Issue:
    check: str
    severity: str
    active_wave: bool
    visualization_id: Any
    visualization: str
    challenge_id: Any
    challenge: str
    wave_id: Any
    message: str
    url: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check": self.check,
            "severity": self.severity,
            "active_wave": self.active_wave,
            "visualization_id": self.visualization_id,
            "visualization": self.visualization,
            "challenge_id": self.challenge_id,
            "challenge": self.challenge,
            "wave_id": self.wave_id,
            "message": self.message,
            "url": self.url,
        }


# ---------------------------------------------------------
# Small helpers
# ---------------------------------------------------------
def _is_nan(value: Any) -> bool:
    try:
        return bool(pd.isna(value))
    except Exception:
        return False


def _clean_scalar(value: Any) -> Any:
    if _is_nan(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value


def _get_now_timestamp() -> pd.Timestamp:
    return pd.Timestamp.now().tz_localize(None)


def _active_wave_ids(checker: CampaignChecker) -> set:
    waves = checker.gc.get("waves")
    if waves is None or waves.empty:
        return set()

    now = _get_now_timestamp()
    active = set()

    for _, row in waves.iterrows():
        start = row.get("start")
        end = row.get("end")
        if pd.notna(start) and pd.notna(end) and start <= now <= end:
            active.add(row["id"])

    return active


def _issue_from_legacy(check_name: str, checker: CampaignChecker, issue: Dict[str, Any], active_wave_ids: set) -> Issue:
    vis = issue["visualization"]
    ch = issue["challenge"]

    vis_id = _clean_scalar(vis.get("id")) if hasattr(vis, "get") else None
    vis_desc = _clean_scalar(vis.get("description")) if hasattr(vis, "get") else ""
    wave_id = _clean_scalar(vis.get("wave")) if hasattr(vis, "get") else None
    ch_id = _clean_scalar(ch.get("id")) if hasattr(ch, "get") else None
    ch_name = _clean_scalar(ch.get("name")) if hasattr(ch, "get") else ""

    active_wave = wave_id in active_wave_ids if wave_id is not None else False
    severity = SEVERITY_BY_CHECK.get(check_name, "medium")
    url = checker.getChallengeEditURL(vis, ch)

    return Issue(
        check=check_name,
        severity=severity,
        active_wave=active_wave,
        visualization_id=vis_id,
        visualization=str(vis_desc or ""),
        challenge_id=ch_id,
        challenge=str(ch_name or ""),
        wave_id=wave_id,
        message=str(issue["error"]),
        url=url,
    )


def _priority_score(issue: Issue) -> int:
    score = SEVERITY_SCORE[issue.severity]
    if issue.active_wave:
        score += 50
    return score


def export_issues_to_excel(issues: List[Issue], output_path: str | Path) -> str:
    output_path = str(output_path)
    rows = [i.to_dict() for i in issues]
    df = pd.DataFrame(rows)

    if df.empty:
        df = pd.DataFrame(columns=[
            "check",
            "severity",
            "active_wave",
            "visualization_id",
            "visualization",
            "challenge_id",
            "challenge",
            "wave_id",
            "message",
            "url",
        ])

    with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Issues", index=False)
        worksheet = writer.sheets["Issues"]
        worksheet.autofit()

    return output_path


# ---------------------------------------------------------
# Main function that the Streamlit app will call
# ---------------------------------------------------------
def run_campaign_checks(file_path: str | Path, checks: Optional[List[str]] = None, export_excel: bool = False) -> Dict[str, Any]:
    checks = checks or DEFAULT_CHECKS
    checker = CampaignChecker(str(file_path))
    active_wave_ids = _active_wave_ids(checker)

    method_map = {
        REACHABILITY: checker.checkInitialAndTerminalReachability,
        CONSISTENCY: checker.checkIntialandTerminalLevelConsistentSuccessors,
        VISUALIZATIONINTERN: checker.checkAllReachableChallengesAreInSameVisualizationAndLabel,
        TARGETPOINTSREACHABLE: checker.checkChallengeTargetPointsCanBeReached,
        SECRETS: lambda: checker.checkTasksHaveSecrets(False),
        TTMSTRUCTURE: checker.checkTTMstructure,
        SPELLCHECKER: checker.spellcheckTaskAndChallenges,
    }

    check_status = {}
    notes = []

    for check_name in checks:
        fn = method_map[check_name]
        try:
            fn()
            check_status[check_name] = checker.checkResult(check_name)
        except Exception as exc:
            check_status[check_name] = "Error"
            notes.append(f"Check '{check_name}' crashed: {exc}")

    issues: List[Issue] = []
    for check_name, raw_issues in checker.errors.items():
        if check_name not in checks:
            continue
        for raw in raw_issues:
            issues.append(_issue_from_legacy(check_name, checker, raw, active_wave_ids))

    issues.sort(key=_priority_score, reverse=True)

    issues_by_check: Dict[str, List[Dict[str, Any]]] = {c: [] for c in checks}
    for issue in issues:
        issues_by_check.setdefault(issue.check, []).append(issue.to_dict())

    passed_checks = [name for name, status in check_status.items() if status == "Passed"]
    failed_checks = [name for name, status in check_status.items() if status == "Failed"]
    errored_checks = [name for name, status in check_status.items() if status == "Error"]

    excel_report_path = None
    if export_excel:
        output_dir = Path(tempfile.gettempdir()) / "gamebus_campaign_assistant"
        output_dir.mkdir(parents=True, exist_ok=True)
        excel_report_path = output_dir / f"issues-{Path(file_path).stem}.xlsx"
        export_issues_to_excel(issues, excel_report_path)
        excel_report_path = str(excel_report_path)

    waves_df = checker.gc.get("waves", pd.DataFrame())
    waves = []
    if not waves_df.empty:
        for _, row in waves_df.iterrows():
            wave_id = _clean_scalar(row.get("id"))
            waves.append({
                "id": wave_id,
                "name": _clean_scalar(row.get("name")),
                "start": _clean_scalar(row.get("start")),
                "end": _clean_scalar(row.get("end")),
                "active_now": wave_id in active_wave_ids,
            })

    return {
        "file_name": Path(file_path).name,
        "analyzed_at": datetime.now().isoformat(timespec="seconds"),
        "checks_run": checks,
        "summary": {
            "total_issues": len(issues),
            "passed_checks": passed_checks,
            "failed_checks": failed_checks,
            "errored_checks": errored_checks,
            "issue_count_by_check": {name: len(issues_by_check.get(name, [])) for name in checks},
        },
        "waves": waves,
        "issues_by_check": issues_by_check,
        "prioritized_issues": [issue.to_dict() for issue in issues[:25]],
        "notes": notes,
        "excel_report_path": excel_report_path,
    }


def summarize_result(result: Dict[str, Any]) -> str:
    s = result["summary"]
    total = s["total_issues"]
    failed = s["failed_checks"]
    passed = s["passed_checks"]
    active_waves = [w["name"] for w in result.get("waves", []) if w.get("active_now")]

    lines = [f"I checked **{result['file_name']}**."]
    lines.append(f"I found **{total} issue(s)**.")

    if failed:
        lines.append("Failed checks: " + ", ".join(f"`{x}`" for x in failed) + ".")
    if passed:
        lines.append("Passed checks: " + ", ".join(f"`{x}`" for x in passed) + ".")
    if active_waves:
        lines.append("Active wave(s) right now: " + ", ".join(f"`{x}`" for x in active_waves) + ".")

    return "\n\n".join(lines)


def explain_ttm() -> str:
    return (
        "The current TTM check assumes this stage structure: "
        "Newbie → Rookie → Amateur → Proficient → Skilled → Expert → Master → Grandmaster, "
        "with relapse / 'at risk' levels around Skilled, Expert, and Master. "
        "In plain language: forward progression should go to the next level on success, "
        "while failure should either keep the user at the same level or send them to the correct at-risk / previous level, depending on where they are in the structure."
    )