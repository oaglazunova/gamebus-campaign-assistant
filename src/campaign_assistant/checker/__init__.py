from campaign_assistant.checker.explainers import explain_ttm, summarize_result
from campaign_assistant.checker.schema import (
    ALL_CHECKS,
    CAPABILITY_GATED_CHECKS,
    CONSISTENCY,
    DEFAULT_CHECKS,
    FAMILY_SPECIFIC_CHECKS,
    FRIENDLY_CHECK_NAMES,
    REACHABILITY,
    SECRETS,
    SPELLCHECKER,
    TARGETPOINTSREACHABLE,
    TTMSTRUCTURE,
    UNIVERSAL_CHECKS,
    VISUALIZATIONINTERN,
)


def run_campaign_checks(*args, **kwargs):
    from campaign_assistant.checker.wrapper import run_campaign_checks as _run_campaign_checks
    return _run_campaign_checks(*args, **kwargs)


def export_issues_to_excel(*args, **kwargs):
    from campaign_assistant.checker.wrapper import export_issues_to_excel as _export_issues_to_excel
    return _export_issues_to_excel(*args, **kwargs)


__all__ = [
    "ALL_CHECKS",
    "CONSISTENCY",
    "DEFAULT_CHECKS",
    "FRIENDLY_CHECK_NAMES",
    "UNIVERSAL_CHECKS",
    "CAPABILITY_GATED_CHECKS",
    "FAMILY_SPECIFIC_CHECKS",
    "REACHABILITY",
    "SECRETS",
    "SPELLCHECKER",
    "TARGETPOINTSREACHABLE",
    "TTMSTRUCTURE",
    "VISUALIZATIONINTERN",
    "run_campaign_checks",
    "export_issues_to_excel",
    "summarize_result",
    "explain_ttm",
]