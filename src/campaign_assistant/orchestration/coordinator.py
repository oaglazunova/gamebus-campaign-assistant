from __future__ import annotations

import uuid
from pathlib import Path

from campaign_assistant.checker.wrapper import run_campaign_checks
from campaign_assistant.session_logging import SessionLogger


class CampaignAnalysisCoordinator:
    """
    Coordinator for deterministic campaign analysis.

    Paper-release scope:
    - automatic analysis runs only export-based deterministic checks;
    - LLM support will be added later as user-triggered chat support;
    - no metadata, sidecars, workspace readiness, or patch generation are used here.
    """

    def __init__(self, logger: SessionLogger | None = None):
        self.logger = logger

    def analyze_campaign(
        self,
        *,
        file_path,
        selected_checks: list[str],
        export_excel: bool,
        user_prompt: str | None = None,
        workspace_id: str | None = None,
    ) -> dict:
        request_id = uuid.uuid4().hex
        file_path = Path(file_path)

        if self.logger is not None:
            self.logger.log(
                "coordinator_started",
                {
                    "request_id": request_id,
                    "file_path": str(file_path),
                    "selected_checks": selected_checks,
                    "export_excel": export_excel,
                },
            )

        result = run_campaign_checks(
            file_path=file_path,
            checks=selected_checks,
            export_excel=export_excel,
        )

        assistant_meta = result.setdefault("assistant_meta", {})
        assistant_meta.update(
            {
                "request_id": request_id,
                "selected_checks": list(selected_checks),
                "agents_run": ["checker_agent"],
                "agent_trace": [
                    {
                        "step": 1,
                        "agent_name": "checker_agent",
                        "status": "success",
                        "summary": (
                            f"Ran {len(selected_checks)} deterministic export-based check(s)."
                        ),
                        "payload_keys": [
                            "summary",
                            "issues_by_check",
                            "prioritized_issues",
                        ],
                        "warnings": [],
                    }
                ],
            }
        )

        if self.logger is not None:
            self.logger.log(
                "coordinator_completed",
                {
                    "request_id": request_id,
                    "total_issues": result.get("summary", {}).get("total_issues", 0),
                    "failed_checks": result.get("summary", {}).get("failed_checks", []),
                },
            )

        return result