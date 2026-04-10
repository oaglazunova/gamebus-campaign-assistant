from campaign_assistant.checker.explainers import explain_ttm, summarize_result


def test_summarize_result_includes_basic_counts():
    result = {
        "file_name": "campaign.xlsx",
        "summary": {
            "total_issues": 3,
            "failed_checks": ["ttm", "consistency"],
            "passed_checks": ["reachability"],
            "errored_checks": [],
        },
        "waves": [
            {"name": "Wave 1", "active_now": True},
            {"name": "Wave 2", "active_now": False},
        ],
    }

    text = summarize_result(result)

    assert "campaign.xlsx" in text
    assert "3" in text
    assert "ttm" in text
    assert "consistency" in text
    assert "reachability" in text
    assert "Wave 1" in text


def test_summarize_result_handles_no_failed_checks():
    result = {
        "file_name": "clean.xlsx",
        "summary": {
            "total_issues": 0,
            "failed_checks": [],
            "passed_checks": ["reachability", "consistency"],
            "errored_checks": [],
        },
        "waves": [],
    }

    text = summarize_result(result)

    assert "clean.xlsx" in text
    assert "0" in text
    assert "No failed checks were detected" in text
    assert "reachability" in text
    assert "consistency" in text


def test_summarize_result_excludes_excel_link():
    result = {
        "file_name": "campaign.xlsx",
        "summary": {
            "total_issues": 3,
            "failed_checks": ["ttm"],
            "passed_checks": [],
            "errored_checks": [],
        },
        "excel_report_path": "/tmp/issues.xlsx",
    }

    text = summarize_result(result)
    assert "Download Excel Report" not in text
    assert "/tmp/issues.xlsx" not in text


def test_explain_ttm_mentions_progression_and_relapse():
    text = explain_ttm().lower()

    assert "newbie" in text
    assert "rookie" in text
    assert "grandmaster" in text
    assert "relapse" in text or "at-risk" in text
    assert "progression" in text or "next level" in text