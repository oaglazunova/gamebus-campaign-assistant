from __future__ import annotations

from campaign_assistant.agents.intent_router import IntentRouter


def test_router_sends_checker_questions_to_campaign_support() -> None:
    router = IntentRouter()

    route = router.route("What should I inspect first?")

    assert route.intent == "campaign_support"
    assert route.agent_name == "campaign_support_agent"


def test_router_sends_theory_questions_to_theory_support() -> None:
    router = IntentRouter()

    for question in [
        "Will it help people lose weight?",
        "What BCT can be applied?",
        "Does this campaign follow TTM?",
        "Is this campaign too complicated?",
    ]:
        route = router.route(question)

        assert route.intent == "theory_support"
        assert route.agent_name == "theory_support_agent"
