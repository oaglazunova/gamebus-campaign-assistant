from __future__ import annotations

import re

from typing import Any
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
    "self-determination",
    "self determination",
    "sdt",
    "autonomy",
    "competence",
    "relatedness",
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
    "prioritization",
    "prioritisation",
    "prioritized",
    "prioritised",
    "highest-priority",
    "highest priority",
    "top-priority",
    "top priority",
    "overview",
    "main issue patterns",
]

FOLLOW_UP_KEYWORDS = [
    "this",
    "it",
    "that",
    "shorter",
    "simpler",
    "rephrase",
    "explain more",
    "what does this mean",
    "why",
]

EXPLICIT_CAMPAIGN_KEYWORDS = [
    "finding",
    "findings",
    "issue",
    "issues",
    "check",
    "checks",
    "fix",
    "repair",
    "priority",
    "challenge",
    "level",
    "task",
    "transition",
    "points",
    "reachability",
    "campaign structure",
]


def _normalize(text: str) -> str:
    return " ".join(text.lower().strip().split())


def _contains_any(text: str, keywords: list[str]) -> str | None:
    for keyword in keywords:
        if keyword in text:
            return keyword
    return None

_CAMPAIGN_OVERRIDE_KEYWORDS = [
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
    "inspect",
    "fix",
    "repair",
    "priority",
    "prioritize",
    "campaign structure",
    "challenge",
    "level",
    "task",
    "transition",
    "points",
    "target points",
    "reachability",
]


def _contains_phrase(text: str, phrase: str) -> bool:
    pattern = rf"(?<!\w){re.escape(phrase)}(?!\w)"
    return re.search(pattern, text) is not None


def _is_short_follow_up(question: str) -> bool:
    normalized = _normalize(question)

    if not normalized or len(normalized.split()) > 12:
        return False

    return any(
        _contains_phrase(normalized, phrase)
        for phrase in FOLLOW_UP_KEYWORDS
    )


def _previous_agent_name(
    conversation_history: list[dict[str, Any]] | None,
) -> str | None:
    for message in reversed(conversation_history or []):
        if message.get("role") != "assistant":
            continue

        agent_name = str(message.get("agent_name") or "")

        if agent_name in {
            "campaign_support_agent",
            "theory_support_agent",
        }:
            return agent_name

    return None


class IntentRouter:
    """
    Route questions to campaign or theory support.

    Explicit questions take precedence over conversation history. Short,
    ambiguous follow-ups remain with the previously responding agent.
    """

    def route(
        self,
        question: str,
        *,
        conversation_history: list[dict[str, Any]] | None = None,
    ) -> RoutedIntent:
        normalized = _normalize(question)

        if is_theory_or_design_question(question):
            return RoutedIntent(
                intent="theory_support",
                agent_name="theory_support_agent",
                reason="Matched theory/design/outcome question type.",
            )

        theory_keyword = _contains_any(
            normalized,
            THEORY_KEYWORDS,
        )

        if theory_keyword:
            return RoutedIntent(
                intent="theory_support",
                agent_name="theory_support_agent",
                reason=f"Matched theory keyword: {theory_keyword}",
            )

        campaign_override = _contains_any(
            normalized,
            _CAMPAIGN_OVERRIDE_KEYWORDS,
        )

        if campaign_override:
            return RoutedIntent(
                intent="campaign_support",
                agent_name="campaign_support_agent",
                reason=(
                    "Matched explicit campaign-support keyword: "
                    f"{campaign_override}"
                ),
            )

        previous_agent = _previous_agent_name(
            conversation_history
        )

        if previous_agent and _is_short_follow_up(question):
            intent = (
                "theory_support"
                if previous_agent == "theory_support_agent"
                else "campaign_support"
            )

            return RoutedIntent(
                intent=intent,
                agent_name=previous_agent,
                reason=(
                    "Short follow-up retained the previously "
                    "responding agent."
                ),
            )

        campaign_keyword = _contains_any(
            normalized,
            CAMPAIGN_SUPPORT_KEYWORDS,
        )

        if campaign_keyword:
            return RoutedIntent(
                intent="campaign_support",
                agent_name="campaign_support_agent",
                reason=(
                    "Matched campaign-support keyword: "
                    f"{campaign_keyword}"
                ),
            )

        return RoutedIntent(
            intent="unknown",
            agent_name="unknown",
            reason=(
                "No campaign, checker, finding, GameBus, "
                "or theory keyword matched."
            ),
        )