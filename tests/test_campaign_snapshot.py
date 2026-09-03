from __future__ import annotations

import pandas as pd

from campaign_assistant.agents.context_builder import build_llm_context
from campaign_assistant.checker.campaign_snapshot import build_campaign_snapshot


def _write_large_campaign_export(path) -> None:
    challenge_count = 85
    task_count = 95

    campaigns = pd.DataFrame([
        {"id": 557, "name": "Large campaign"},
    ])

    waves = pd.DataFrame([
        {"id": 1, "name": "Wave 1"},
    ])

    visualizations = pd.DataFrame([
        {"id": 10, "name": "Progression", "wave": 1},
    ])

    challenges = pd.DataFrame(
        [
            {
                "id": challenge_id,
                "name": f"Level {challenge_id}",
                "visualizations": 10,
                "target": 10,
                "is_initial_level": challenge_id == 1,
                "success_next": (
                    challenge_id + 1
                    if challenge_id < challenge_count
                    else None
                ),
            }
            for challenge_id in range(1, challenge_count + 1)
        ]
    )

    tasks = pd.DataFrame(
        [
            {
                "id": 1000 + index,
                "name": f"Task {index}",
                "challenge": (index % challenge_count) + 1,
                "points": 10,
            }
            for index in range(task_count)
        ]
    )

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        campaigns.to_excel(writer, sheet_name="campaigns", index=False)
        waves.to_excel(writer, sheet_name="waves", index=False)
        visualizations.to_excel(
            writer,
            sheet_name="visualizations",
            index=False,
        )
        challenges.to_excel(writer, sheet_name="challenges", index=False)
        tasks.to_excel(writer, sheet_name="tasks", index=False)


def test_campaign_snapshot_is_not_truncated_at_80_rows(tmp_path) -> None:
    export_path = tmp_path / "large_campaign.xlsx"
    _write_large_campaign_export(export_path)

    snapshot = build_campaign_snapshot(export_path)

    assert snapshot["counts"]["challenges"] == 85
    assert snapshot["counts"]["tasks"] == 95

    assert len(snapshot["challenges"]) == 85
    assert len(snapshot["tasks"]) == 95
    assert len(snapshot["transitions"]) == 84


def test_llm_context_stays_compact_when_snapshot_is_complete(
    tmp_path,
) -> None:
    export_path = tmp_path / "large_campaign.xlsx"
    _write_large_campaign_export(export_path)

    snapshot = build_campaign_snapshot(export_path)

    context = build_llm_context(
        {
            "campaign_snapshot": snapshot,
            "summary": {},
            "checks_run": [],
        },
        max_challenges=12,
        max_tasks=15,
    )

    structure = context["campaign_structure"]

    assert len(structure["challenges"]) == 12
    assert len(structure["tasks"]) == 15
    assert len(structure["task_summary_by_challenge"]) <= 12

    # Counts still describe the complete campaign.
    assert structure["counts"]["challenges"] == 85
    assert structure["counts"]["tasks"] == 95
