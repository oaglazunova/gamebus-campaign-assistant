from __future__ import annotations

from campaign_assistant.agents.base import BaseAgent
from campaign_assistant.orchestration.models import AgentContext, AgentResponse
from campaign_assistant.privacy import PrivacyService


class PrivacyGuardianAgent(BaseAgent):
    """
    Phase 2 privacy boundary bootstrap.

    This agent:
    - inventories workspace assets
    - assigns coarse sensitivity labels
    - defines per-agent access policy
    - stores:
        * compatibility access policy
        * rich privacy_state
        * compact privacy_report
    """

    name = "privacy_guardian"

    def __init__(self) -> None:
        self.service = PrivacyService()

    def run(self, context: AgentContext) -> AgentResponse:
        privacy_state_obj = self.service.build_privacy_state(context)
        privacy_state = privacy_state_obj.to_dict()
        access_policy = self.service.to_compatibility_access_policy(privacy_state_obj)
        privacy_report = self.service.build_privacy_report(privacy_state)

        context.shared["privacy"] = access_policy
        context.shared["privacy_state"] = privacy_state
        context.shared["privacy_report"] = privacy_report

        summary = (
            "Privacy policy initialized for this request. "
            f"Detected {privacy_state['summary'].get('asset_count', 0)} workspace asset(s); "
            f"{len(privacy_state['summary'].get('raw_workbook_allowed_agents', []))} agent(s) may access the raw workbook, "
            f"and {len(privacy_state['summary'].get('sanitized_only_agents', []))} agent(s) are restricted to derived/sanitized context."
        )

        return AgentResponse(
            agent_name=self.name,
            success=True,
            summary=summary,
            payload={
                "access_policy": access_policy,
                "privacy_summary": privacy_state["summary"],
                "privacy_report": privacy_report,
            },
        )