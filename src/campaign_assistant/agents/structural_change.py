from __future__ import annotations

from campaign_assistant.agents.base import BaseAgent
from campaign_assistant.checker.wrapper import run_campaign_checks
from campaign_assistant.orchestration.models import AgentContext, AgentResponse
from campaign_assistant.reasoning import PointGatekeepingService


class StructuralChangeAgent(BaseAgent):
    """
    Agent backed by the existing checker plus structural intervention reasoning.

    Responsibilities now:
    - run the legacy checker through the wrapper
    - return normalized campaign checking results
    - run point/gatekeeping reasoning
    - act as the future home for:
      - campaign comparison
      - richer change history analysis
      - stronger progression reasoning
    """

    name = "structural_change_agent"

    def __init__(self) -> None:
        self.point_service = PointGatekeepingService()

    def run(self, context: AgentContext) -> AgentResponse:
        result = run_campaign_checks(
            file_path=context.file_path,
            checks=context.selected_checks,
            export_excel=context.export_excel,
        )

        point_gatekeeping = self.point_service.analyze(
            campaign_file=context.file_path,
            point_rules=context.point_rules,
            task_roles=context.task_roles,
        )

        result["point_gatekeeping"] = point_gatekeeping
        context.shared["result"] = result

        summary = result.get("summary", {})
        failed_checks = summary.get("failed_checks", [])
        total_issues = summary.get("total_issues", 0)

        pg_summary = point_gatekeeping.get("summary", {})
        pg_findings = pg_summary.get("challenge_findings", 0)

        if failed_checks:
            text = (
                f"Structural analysis found {total_issues} issue(s). "
                f"Failed checks: {', '.join(failed_checks)}."
            )
        else:
            text = "Structural analysis found no failed checks."

        if pg_findings:
            text += f" Point/gatekeeping analysis highlighted {pg_findings} challenge(s) that may require attention."

        return AgentResponse(
            agent_name=self.name,
            success=True,
            summary=text,
            payload={
                "result_summary": summary,
                "excel_report_path": result.get("excel_report_path"),
                "point_gatekeeping_summary": pg_summary,
            },
        )