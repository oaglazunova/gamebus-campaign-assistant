from __future__ import annotations

from pathlib import Path

from campaign_assistant.agents.base import BaseAgent
from campaign_assistant.orchestration.models import AgentContext, AgentResponse


class PrivacyGuardianAgent(BaseAgent):
    """
    Minimal first version of the privacy guardian.

    Right now it:
    - records which files are allowed for downstream agents
    - records a placeholder redaction policy
    - stores this in the shared context for traceability

    Later it can:
    - redact fields before passing data to the ContentFixerAgent
    - enforce per-agent access policies
    - block unsafe requests
    """

    name = "privacy_guardian"

    def run(self, context: AgentContext) -> AgentResponse:
        campaign_path = Path(context.file_path).resolve()

        access_policy = {
            "structural_change_agent": {
                "allowed_paths": [str(campaign_path)],
                "redactions": [],
            },
            # Placeholder for later agents:
            "theory_grounding_agent": {
                "allowed_paths": [str(campaign_path)],
                "redactions": [],
            },
            "content_fixer_agent": {
                "allowed_paths": [str(campaign_path)],
                "redactions": [
                    "redact_user_identifiers_before_content_fixing"
                ],
            },
        }

        context.shared["privacy"] = access_policy

        return AgentResponse(
            agent_name=self.name,
            success=True,
            summary=(
                "Privacy policy initialized for this request. "
                "Structural analysis has full access to the campaign file; "
                "future content-fixing runs must apply redaction rules."
            ),
            payload={"access_policy": access_policy},
        )