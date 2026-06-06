from __future__ import annotations

from dataclasses import dataclass

from campaign_assistant.agents.question_types import is_theory_or_design_question


@dataclass(frozen=True)
class RoutedIntent:
    intent: str
    agent_name: str
    reason: str


THEORY_KEYWORDS = [
    "bct",
    "behaviour change",
    "behavior change",
    "behavior-change",
    "com-b",
    "comb",
    "capability",
    "opportunity",
    "motivation",
    "ttm",
    "transtheoretical",
    "stage of change",
    "stages of change",
    "self-efficacy",
    "theory",
    "theoretical",
    "intervention function",
    "behaviour change wheel",
    "behavior change wheel",
    "good campaign",
    "complicated",
    "too complicated",
    "complex",
    "too complex",
    "burden",
    "user burden",
    "participant burden",
    "lose weight",
    "loose weight",
    "weight loss",
    "obesity",
    "effective",
    "effectiveness",
    "help people",
    "health outcome",
    "outcome",
    "adherence",
    "engagement",
]

CAMPAIGN_SUPPORT_KEYWORDS = [
    "finding",
    "findings",
    "issue",
    "issues",
    "error",
    "warning",
    "failed",
    "check",
    "checks",
    "validator",
    "validation",
    "explain",
    "meaning",
    "why",
    "inspect",
    "fix",
    "repair",
    "improve",
    "priority",
    "prioritize",
    "first",
    "summary",
    "summarize",
    "campaign structure",
    "structure",
    "challenge",
    "level",
    "task",
    "transition",
    "points",
    "target points",
    "reachability",
]


def _normalize(text: str) -> str:
    return " ".join(text.lower().strip().split())


def _contains_any(text: str, keywords: list[str]) -> str | None:
    for keyword in keywords:
        if keyword in text:
            return keyword
    return None


class IntentRouter:
    """
    Rules-based router for the single Assistant chat.

    Precedence:
    1. theory support
    2. campaign/finding support
    3. campaign support fallback
    """

    def route(self, question: str) -> RoutedIntent:
        q = _normalize(question)

        if is_theory_or_design_question(question):
            return RoutedIntent(
                intent="theory_support",
                agent_name="theory_support_agent",
                reason="Matched theory/design/outcome question type.",
            )

        theory_keyword = _contains_any(q, THEORY_KEYWORDS)
        if theory_keyword:
            return RoutedIntent(
                intent="theory_support",
                agent_name="theory_support_agent",
                reason=f"Matched theory keyword: {theory_keyword}",
            )

        campaign_keyword = _contains_any(q, CAMPAIGN_SUPPORT_KEYWORDS)
        if campaign_keyword:
            return RoutedIntent(
                intent="campaign_support",
                agent_name="campaign_support_agent",
                reason=f"Matched campaign-support keyword: {campaign_keyword}",
            )

        return RoutedIntent(
            intent="campaign_support",
            agent_name="campaign_support_agent",
            reason="Default route for campaign-analysis questions.",
        )
