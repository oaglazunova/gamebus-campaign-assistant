from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from campaign_assistant.checker.schema import (
    CAMPAIGNMETADATA,
    Issue,
)
from campaign_assistant.checker.table_utils import (
    _clean_scalar,
    _get_table,
)


def _has_text(value: Any) -> bool:
    value = _clean_scalar(value)

    if value is None:
        return False

    return bool(str(value).strip())


def run_native_campaignmetadata_tables(
    tables: Mapping[str, pd.DataFrame],
    now: pd.Timestamp | None = None,
) -> dict[str, Any]:
    campaigns_df = _get_table(tables, "campaigns")

    if campaigns_df.empty:
        return {
            "status": "Error",
            "issues": [],
            "notes": [
                "Campaign metadata completeness could not be evaluated "
                "because the campaigns sheet contains no campaign row."
            ],
        }

    issues: list[Issue] = []

    for _, row in campaigns_df.iterrows():
        campaign = row.to_dict()

        if _has_text(campaign.get("description")):
            continue

        campaign_name = str(
            _clean_scalar(campaign.get("name"))
            or _clean_scalar(campaign.get("abbreviation"))
            or "this campaign"
        )

        issues.append(
            Issue(
                check=CAMPAIGNMETADATA,
                severity="low",
                active_wave=False,
                visualization_id=None,
                visualization="",
                challenge_id=None,
                challenge="",
                wave_id=None,
                title="Campaign description is missing",
                message=(
                    f"Campaign '{campaign_name}' has no description. "
                    "Add a short description explaining the campaign's "
                    "purpose and target population. Where relevant, include "
                    "context such as the target age group, country or setting, "
                    "language, campaign objective, and important design "
                    "assumptions. These are examples of useful metadata, not "
                    "required individual fields. Keeping this context with "
                    "the campaign can support later review, comparison, "
                    "adaptation, automated analysis, and content generation."
                ),
                url="",
            )
        )

    return {
        "status": "Failed" if issues else "Passed",
        "issues": issues,
        "notes": [],
    }


def load_campaignmetadata_tables(
    file_path: str | Path,
) -> dict[str, pd.DataFrame]:
    return {
        "campaigns": pd.read_excel(
            file_path,
            sheet_name="campaigns",
        ),
    }


def run_native_campaignmetadata_check(
    file_path: str | Path,
    now: pd.Timestamp | None = None,
) -> dict[str, Any]:
    tables = load_campaignmetadata_tables(file_path)

    return run_native_campaignmetadata_tables(
        tables,
        now=now,
    )