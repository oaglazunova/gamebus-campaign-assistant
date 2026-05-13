from __future__ import annotations

import pandas as pd

from campaign_assistant.checker.preflight import probe_targetpoints_applicability


def test_probe_targetpoints_applicability_disables_when_only_structure_exists(tmp_path):
    file_path = tmp_path / "campaign.xlsx"

    with pd.ExcelWriter(file_path) as writer:
        pd.DataFrame(
            [{"challenge": 1, "points": None, "max_times_fired": None, "min_days_between_fire": None}]
        ).to_excel(writer, sheet_name="tasks", index=False)
        pd.DataFrame(
            [{"id": 1, "visualizations": 100, "target": None, "evaluate_fail_every_x_minutes": None}]
        ).to_excel(writer, sheet_name="challenges", index=False)
        pd.DataFrame(
            [{"id": 100, "campaign": 1, "description": "V1", "wave": 10}]
        ).to_excel(writer, sheet_name="visualizations", index=False)
        pd.DataFrame(
            [{"id": 10, "start": pd.Timestamp("2025-01-01"), "end": pd.Timestamp("2025-12-31")}]
        ).to_excel(writer, sheet_name="waves", index=False)

    enabled, reason = probe_targetpoints_applicability(file_path)

    assert enabled is False
    assert "Disabled" in reason


def test_probe_targetpoints_applicability_enables_when_one_computable_chain_exists(tmp_path):
    file_path = tmp_path / "campaign.xlsx"

    with pd.ExcelWriter(file_path) as writer:
        pd.DataFrame(
            [{"challenge": 1, "points": 10, "max_times_fired": 2, "min_days_between_fire": 1}]
        ).to_excel(writer, sheet_name="tasks", index=False)
        pd.DataFrame(
            [{"id": 1, "visualizations": 100, "target": 50, "evaluate_fail_every_x_minutes": 4320}]
        ).to_excel(writer, sheet_name="challenges", index=False)
        pd.DataFrame(
            [{"id": 100, "campaign": 1, "description": "V1", "wave": 10}]
        ).to_excel(writer, sheet_name="visualizations", index=False)
        pd.DataFrame(
            [{"id": 10, "start": pd.Timestamp("2025-01-01"), "end": pd.Timestamp("2025-12-31")}]
        ).to_excel(writer, sheet_name="waves", index=False)

    enabled, reason = probe_targetpoints_applicability(file_path)

    assert enabled is True
    assert "Enabled" in reason