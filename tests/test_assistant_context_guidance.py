from campaign_assistant.agents.context_builder import (
    build_llm_context,
    format_llm_context_markdown,
)


def test_llm_context_includes_deterministic_fix_guidance(minimal_analysis_result: dict):
    result = minimal_analysis_result.copy()
    result["summary"] = dict(minimal_analysis_result["summary"])
    result["summary"]["total_issues"] = 1
    result["summary"]["failed_checks"] = ["reachability"]
    result["summary"]["passed_checks"] = []
    result["summary"]["issue_count_by_check"] = {"reachability": 1}
    result["summary"]["severity_counts"] = {"high": 1}
    result["prioritized_issues"] = [
        {
            "check": "reachability",
            "severity": "high",
            "message": "Terminal Challenge not reachable from any initial challenge",
            "title": "Terminal Challenge not reachable from any initial challenge",
            "visualization": "Achtsamkeit",
            "visualization_id": 3477,
            "challenge": "[Grandmaster] Tagebuch führen",
            "challenge_id": 14549,
            "wave_id": 846,
            "url": "https://campaigns.healthyw8.gamebus.eu/editor/for/456/3477/challenges/14549",
        }
    ]

    context = build_llm_context(result)
    finding = context["top_findings"][0]

    assert "deterministic_gamebus_fix_guidance" in finding
    assert (
        "Connect this terminal level to an initial success path"
        in finding["deterministic_gamebus_fix_guidance"]
    )
    assert "Next level when target is met on time" in finding["deterministic_gamebus_fix_guidance"]


def test_formatted_context_renders_deterministic_fix_guidance(minimal_analysis_result: dict):
    result = minimal_analysis_result.copy()
    result["summary"] = dict(minimal_analysis_result["summary"])
    result["summary"]["total_issues"] = 1
    result["summary"]["failed_checks"] = ["reachability"]
    result["summary"]["passed_checks"] = []
    result["summary"]["issue_count_by_check"] = {"reachability": 1}
    result["summary"]["severity_counts"] = {"high": 1}
    result["prioritized_issues"] = [
        {
            "check": "reachability",
            "severity": "high",
            "message": "Terminal Challenge not reachable from any initial challenge",
            "title": "Terminal Challenge not reachable from any initial challenge",
            "visualization": "Achtsamkeit",
            "challenge": "[Grandmaster] Tagebuch führen",
            "challenge_id": 14549,
            "wave_id": 846,
        }
    ]

    context = build_llm_context(result)
    markdown = format_llm_context_markdown(context)

    assert "Deterministic GameBus Studio fix guidance" in markdown
    assert "Connect this terminal level to an initial success path" in markdown
    assert "Next level when target is met on time" in markdown

from campaign_assistant.agents.context_builder import (
    build_llm_context,
    format_llm_context_markdown,
)


def _result_with_terminal_reachability_issue(base: dict) -> dict:
    result = base.copy()
    result["summary"] = dict(base["summary"])
    result["summary"]["total_issues"] = 1
    result["summary"]["failed_checks"] = ["reachability"]
    result["summary"]["passed_checks"] = []
    result["summary"]["issue_count_by_check"] = {"reachability": 1}
    result["summary"]["severity_counts"] = {"high": 1}
    result["prioritized_issues"] = [
        {
            "check": "reachability",
            "severity": "high",
            "message": "Terminal Challenge not reachable from any initial challenge",
            "title": "Terminal Challenge not reachable from any initial challenge",
            "visualization": "Achtsamkeit",
            "visualization_id": 3477,
            "challenge": "[Grandmaster] Tagebuch führen",
            "challenge_id": 14549,
            "wave_id": 846,
            "priority_score": 300,
            "priority_rationale": "severity high = 300; active wave boost = 0",
            "url": "https://campaigns.healthyw8.gamebus.eu/editor/for/456/3477/challenges/14549",
        }
    ]
    return result


def test_llm_context_includes_deterministic_fix_guidance(minimal_analysis_result: dict):
    result = _result_with_terminal_reachability_issue(minimal_analysis_result)

    context = build_llm_context(result)
    finding = context["top_findings"][0]

    assert "deterministic_gamebus_fix_guidance" in finding
    assert (
        "Connect this terminal level to an initial success path"
        in finding["deterministic_gamebus_fix_guidance"]
    )
    assert "Next level when target is met on time" in finding["deterministic_gamebus_fix_guidance"]


def test_llm_context_includes_gamebus_studio_source_facts(minimal_analysis_result: dict):
    result = _result_with_terminal_reachability_issue(minimal_analysis_result)

    context = build_llm_context(result)
    finding = context["top_findings"][0]

    assert "gamebus_studio_source_facts" in finding
    assert "Level settings" in finding["gamebus_studio_source_facts"]
    assert "success_next" in finding["gamebus_studio_source_facts"]


def test_formatted_context_renders_guidance_and_source_facts(minimal_analysis_result: dict):
    result = _result_with_terminal_reachability_issue(minimal_analysis_result)

    context = build_llm_context(result)
    markdown = format_llm_context_markdown(context)

    assert "Deterministic GameBus Studio fix guidance" in markdown
    assert "Connect this terminal level to an initial success path" in markdown
    assert "GameBus Studio source facts" in markdown
    assert "success_next" in markdown
    assert "GameBus Studio URL" in markdown