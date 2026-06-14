from __future__ import annotations

from campaign_assistant.agents.intent_router import IntentRouter


def test_router_sends_checker_questions_to_campaign_support() -> None:
    router = IntentRouter()

    for question in [
        "What should I inspect first?",
        "What is the campaign structure?",
        "How is prioritization calculated?",
        "What do the checks check?",
    ]:
        route = router.route(question)
        assert route.intent == "campaign_support"
        assert route.agent_name == "campaign_support_agent"


def test_router_sends_theory_questions_to_theory_support() -> None:
    router = IntentRouter()

    for question in [
        "Will it help people lose weight?",
        "What BCT can be applied?",
        "Does this campaign follow TTM?",
        "Is this campaign too complicated?",
        "How theory-grounded is this campaign?",
        "Does this campaign follow a behavior theory?",
        "Is this campaign SDT-aligned?",
        "How can I make this campaign autonomy-supportive?",
    ]:
        route = router.route(question)
        assert route.intent == "theory_support"
        assert route.agent_name == "theory_support_agent"
