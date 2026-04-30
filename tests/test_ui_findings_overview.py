from campaign_assistant.ui.chat import _check_summary_rows


def test_check_summary_rows_only_returns_checks_with_findings_or_errors():
	result = {
		"issues_by_check": {
			"reachability": [
				{
					"severity": "high",
					"active_wave": True,
				}
			],
			"secrets": [],
		},
		"summary": {
			"issue_count_by_check": {
				"reachability": 1,
				"secrets": 0,
				"ttm": 0,
			},
			"failed_checks": ["reachability"],
			"errored_checks": ["ttm"],
		},
	}

	rows = _check_summary_rows(result)
	by_check = {row["check"]: row for row in rows}

	assert "reachability" in by_check
	assert by_check["reachability"]["status"] == "Failed"
	assert by_check["reachability"]["issues"] == 1
	assert by_check["reachability"]["active_wave"] == 1
	assert by_check["reachability"]["high"] == 1

	assert "ttm" in by_check
	assert by_check["ttm"]["status"] == "Errored"

	assert "secrets" not in by_check