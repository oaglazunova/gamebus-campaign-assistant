from __future__ import annotations


def test_core_imports() -> None:
    from campaign_assistant.app import main
    from campaign_assistant.agents import (
        AssistantCoordinator,
        CampaignSupportAgent,
        IntentRouter,
        TheorySupportAgent,
    )
    from campaign_assistant.diagram import build_campaign_flow_svg
    from campaign_assistant.llm import create_llm_client

    assert main is not None
    assert AssistantCoordinator is not None
    assert CampaignSupportAgent is not None
    assert IntentRouter is not None
    assert TheorySupportAgent is not None
    assert build_campaign_flow_svg is not None
    assert create_llm_client is not None
