from __future__ import annotations

from campaign_assistant.agents.ttm_grounding import TTMGroundingAgent
from campaign_assistant.orchestration.models import AgentContext, AgentResponse


class TheoryGroundingAgent(TTMGroundingAgent):
    """
    Backward-compatible alias for pre-Release-2 imports.

    New code should import and instantiate TTMGroundingAgent instead. Keeping this
    thin subclass prevents older tests/UI helpers from breaking while the public
    naming is migrated away from generic "theory grounding".
    """

    name = "theory_grounding_agent"

    def run(self, context: AgentContext) -> AgentResponse:
        response = super().run(context)
        if response.summary.startswith("TTM grounding skipped"):
            summary = "Theory grounding skipped because TTM is not enabled for this campaign."
        elif response.summary.startswith("TTM grounding completed"):
            summary = "Theory grounding completed in TTM mode."
        else:
            summary = response.summary

        return AgentResponse(
            agent_name=response.agent_name,
            success=response.success,
            summary=summary,
            payload=response.payload,
            warnings=response.warnings,
        )
