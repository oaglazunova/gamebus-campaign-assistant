from __future__ import annotations

import pandas as pd

from campaign_assistant.checker.native_campaignmetadata import (
    run_native_campaignmetadata_tables,
)
from campaign_assistant.checker.schema import (
    CAMPAIGNMETADATA,
)


def _tables(
    description,
) -> dict[str, pd.DataFrame]:
    return {
        "campaigns": pd.DataFrame(
            [
                {
                    "id": 557,
                    "abbreviation": "HW8",
                    "name": "Example campaign",
                    "description": description,
                }
            ]
        ),
    }


def test_missing_campaign_description_is_reported() -> None:
    result = run_native_campaignmetadata_tables(
        _tables(None)
    )

    assert result["status"] == "Failed"
    assert len(result["issues"]) == 1

    issue = result["issues"][0]

    assert issue.check == CAMPAIGNMETADATA
    assert issue.severity == "low"
    assert issue.active_wave is False
    assert issue.title == "Campaign description is missing"

    assert "target age group" in issue.message
    assert "country or setting" in issue.message
    assert "language" in issue.message
    assert "content generation" in issue.message

    assert issue.visualization_id is None
    assert issue.challenge_id is None
    assert issue.wave_id is None


def test_whitespace_only_campaign_description_is_reported() -> None:
    result = run_native_campaignmetadata_tables(
        _tables("   \n\t ")
    )

    assert result["status"] == "Failed"
    assert len(result["issues"]) == 1


def test_existing_campaign_description_passes() -> None:
    result = run_native_campaignmetadata_tables(
        _tables(
            "A Danish English-language campaign for children "
            "supporting healthy lifestyle behaviours."
        )
    )

    assert result["status"] == "Passed"
    assert result["issues"] == []


def test_empty_campaigns_sheet_returns_error() -> None:
    result = run_native_campaignmetadata_tables(
        {
            "campaigns": pd.DataFrame(
                columns=[
                    "id",
                    "name",
                    "description",
                ]
            )
        }
    )

    assert result["status"] == "Error"
    assert result["issues"] == []
    assert result["notes"]