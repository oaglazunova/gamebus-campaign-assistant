from __future__ import annotations


OUTCOME_TERMS = [
    "lose weight",
    "loose weight",
    "weight loss",
    "obesity",
    "bmi",
    "health outcome",
    "outcome",
    "effective",
    "effectiveness",
    "will it work",
    "will it help",
    "help people",
    "impact",
    "improve health",
]

BCT_TERMS = [
    "bct",
    "bcts",
    "behavior change technique",
    "behaviour change technique",
    "technique",
    "techniques",
]

TTM_TERMS = [
    "ttm",
    "transtheoretical",
    "stage of change",
    "stages of change",
    "precontemplation",
    "contemplation",
    "preparation",
    "action",
    "maintenance",
    "relapse",
]

COM_B_TERMS = [
    "com-b",
    "comb",
    "capability",
    "opportunity",
    "motivation",
]

DESIGN_QUALITY_TERMS = [
    "good campaign",
    "is it good",
    "better campaign",
    "too complicated",
    "complicated",
    "too complex",
    "complex",
    "burden",
    "user burden",
    "participant burden",
    "engagement",
    "adherence",
    "improve the campaign",
    "improve this campaign",
]


def normalize_question(question: str) -> str:
    return " ".join(str(question or "").lower().strip().split())


def contains_any(question: str, terms: list[str]) -> bool:
    q = normalize_question(question)
    return any(term in q for term in terms)


def is_outcome_question(question: str) -> bool:
    return contains_any(question, OUTCOME_TERMS)


def is_bct_question(question: str) -> bool:
    return contains_any(question, BCT_TERMS)


def is_ttm_question(question: str) -> bool:
    return contains_any(question, TTM_TERMS)


def is_com_b_question(question: str) -> bool:
    return contains_any(question, COM_B_TERMS)


def is_design_quality_question(question: str) -> bool:
    return contains_any(question, DESIGN_QUALITY_TERMS)


def is_theory_or_design_question(question: str) -> bool:
    return (
        is_outcome_question(question)
        or is_bct_question(question)
        or is_ttm_question(question)
        or is_com_b_question(question)
        or is_design_quality_question(question)
        or contains_any(question, ["theory", "theoretical", "intervention"])
    )