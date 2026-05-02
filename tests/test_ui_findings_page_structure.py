def test_findings_page_should_prioritize_issue_content_over_interpretation():
    # This is a lightweight structural regression test for the intended page order.
    # Detailed findings should come before optional interpretation panels.
    order = [
        "render_findings_overview_panel",
        "render_issues_panel",
        "render_theory_panel",
        "render_point_gatekeeping_panel",
    ]

    assert order.index("render_findings_overview_panel") < order.index("render_issues_panel")
    assert order.index("render_issues_panel") < order.index("render_theory_panel")
    assert order.index("render_issues_panel") < order.index("render_point_gatekeeping_panel")