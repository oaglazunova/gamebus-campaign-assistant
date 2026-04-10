from campaign_assistant.ui.chat import (
    answer_question,
    build_issue_markdown_list,
    format_issue,
    issues_for_check,
)


def sample_result(checks_run=None):
    return {
        "file_name": "campaign.xlsx",
        "checks_run": checks_run or ["ttm", "consistency", "reachability"],
        "summary": {
            "total_issues": 3,
            "failed_checks": ["ttm", "consistency"],
            "passed_checks": ["reachability"],
            "errored_checks": [],
            "issue_count_by_check": {
                "ttm": 2,
                "consistency": 1,
                "reachability": 0,
            },
        },
        "waves": [
            {"name": "Wave 1", "active_now": True},
            {"name": "Wave 2", "active_now": False},
        ],
        "issues_by_check": {
            "ttm": [
                {
                    "check": "ttm",
                    "severity": "high",
                    "active_wave": True,
                    "visualization_id": 1,
                    "visualization": "TTM Levels",
                    "challenge_id": 101,
                    "challenge": "Skilled",
                    "wave_id": 1,
                    "message": "Wrong TTM successor.",
                    "url": "https://example.com/1",
                },
                {
                    "check": "ttm",
                    "severity": "high",
                    "active_wave": False,
                    "visualization_id": 1,
                    "visualization": "TTM Levels",
                    "challenge_id": 102,
                    "challenge": "Expert",
                    "wave_id": 2,
                    "message": "Wrong relapse target.",
                    "url": "https://example.com/2",
                },
            ],
            "consistency": [
                {
                    "check": "consistency",
                    "severity": "high",
                    "active_wave": True,
                    "visualization_id": 2,
                    "visualization": "Points",
                    "challenge_id": 201,
                    "challenge": "Gatekeeper",
                    "wave_id": 1,
                    "message": "Inconsistent successor.",
                    "url": "https://example.com/3",
                }
            ],
            "reachability": [],
        },
        "prioritized_issues": [
            {
                "check": "ttm",
                "severity": "high",
                "active_wave": True,
                "visualization_id": 1,
                "visualization": "TTM Levels",
                "challenge_id": 101,
                "challenge": "Skilled",
                "wave_id": 1,
                "message": "Wrong TTM successor.",
                "url": "https://example.com/1",
            },
            {
                "check": "consistency",
                "severity": "high",
                "active_wave": True,
                "visualization_id": 2,
                "visualization": "Points",
                "challenge_id": 201,
                "challenge": "Gatekeeper",
                "wave_id": 1,
                "message": "Inconsistent successor.",
                "url": "https://example.com/3",
            },
        ],
    }


def test_format_issue_includes_key_fields():
    issue = sample_result()["issues_by_check"]["ttm"][0]

    text = format_issue(issue)

    assert "TTM Levels" in text
    assert "Skilled" in text
    assert "Wrong TTM successor." in text
    assert "Open in GameBus" in text


def test_issues_for_check_returns_expected_group():
    result = sample_result()

    ttm_issues = issues_for_check(result, "ttm")
    reachability_issues = issues_for_check(result, "reachability")

    assert len(ttm_issues) == 2
    assert reachability_issues == []


def test_build_issue_markdown_list_truncates_and_adds_suggestion_for_multi_check():
    issues = sample_result()["issues_by_check"]["ttm"]

    text = build_issue_markdown_list(
        issues,
        single_check_selected=False,
        max_items=1,
    )

    assert "Wrong TTM successor." in text
    assert "1 more" in text
    assert "use the download button in the sidebar" in text
    assert "select only **one check** in the sidebar" in text


def test_build_issue_markdown_list_shows_all_when_single_check_selected():
    issues = sample_result(checks_run=["ttm"])["issues_by_check"]["ttm"]

    text = build_issue_markdown_list(
        issues,
        single_check_selected=True,
    )

    assert "Wrong TTM successor." in text
    assert "Wrong relapse target." in text
    assert "more issue(s)" not in text


def test_answer_question_summary():
    result = sample_result()

    text = answer_question("Summarize the issues", result)

    assert "3" in text
    assert "ttm" in text
    assert "consistency" in text


def test_answer_question_failed_checks():
    result = sample_result()

    text = answer_question("Which checks failed?", result)

    assert "ttm" in text
    assert "consistency" in text


def test_answer_question_ttm_issues():
    result = sample_result()

    text = answer_question("Show TTM issues", result)

    assert "TTM structure" in text
    assert "Wrong TTM successor." in text


def test_answer_question_fix_first():
    result = sample_result()

    text = answer_question("What should I fix first?", result)

    assert "highest-priority" in text.lower()
    assert "Wrong TTM successor." in text


def test_answer_question_explain_ttm():
    result = sample_result()

    text = answer_question("Explain TTM", result)

    assert "Newbie" in text or "newbie" in text
    assert "Grandmaster" in text or "grandmaster" in text