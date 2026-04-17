from __future__ import annotations

from pathlib import Path

import pandas as pd

from campaign_assistant.metadata.models import CampaignCapabilities, MetadataBundle


def _safe_read_sheet(file_path: str | Path, sheet_name: str):
    try:
        return pd.read_excel(file_path, sheet_name=sheet_name)
    except Exception:
        return None


def load_inferred_metadata(file_path: str | Path) -> MetadataBundle:
    """
    Infer campaign capabilities from the workbook structure only.

    This is intentionally conservative.
    We infer only what is reasonably likely from the export, and leave the rest as None.
    """
    bundle = MetadataBundle()
    capabilities = CampaignCapabilities()

    challenges = _safe_read_sheet(file_path, "challenges")
    tasks = _safe_read_sheet(file_path, "tasks")
    waves = _safe_read_sheet(file_path, "waves")
    groups = _safe_read_sheet(file_path, "groups")

    # Wave/group-specific logic
    if waves is not None:
        capabilities.uses_wave_specific_logic = True
        bundle.sources["uses_wave_specific_logic"] = "inferred"
    else:
        capabilities.uses_wave_specific_logic = None
        bundle.missing.append("Could not infer wave-specific logic because no 'waves' sheet was found.")

    if groups is not None:
        capabilities.uses_group_specific_logic = True
        bundle.sources["uses_group_specific_logic"] = "inferred"
    else:
        capabilities.uses_group_specific_logic = None
        bundle.missing.append("Could not infer group-specific logic because no 'groups' sheet was found.")

    # Progression logic
    if challenges is not None:
        challenge_cols = {str(c).strip().lower() for c in challenges.columns}

        has_success = "success_next" in challenge_cols
        has_failure = "failure_next" in challenge_cols
        has_target = "target" in challenge_cols

        if has_success or has_failure:
            capabilities.uses_progression = True
            bundle.sources["uses_progression"] = "inferred"
            bundle.notes.append("Workbook structure suggests challenge transitions / progression.")
        elif has_target:
            capabilities.uses_progression = None
            bundle.notes.append("Workbook has challenge targets but no explicit transition columns were detected.")
        else:
            capabilities.uses_progression = False
            bundle.sources["uses_progression"] = "inferred"

    else:
        capabilities.uses_progression = None
        bundle.missing.append("Could not infer progression because no 'challenges' sheet was found.")

    # Point-related logic
    if tasks is not None:
        task_cols = {str(c).strip().lower() for c in tasks.columns}
        if "points" in task_cols:
            bundle.notes.append("Workbook contains task points.")
        else:
            bundle.missing.append("No 'points' column found in 'tasks' sheet.")

    else:
        bundle.missing.append("Could not inspect tasks because no 'tasks' sheet was found.")

    # These should not be guessed from workbook structure alone
    capabilities.uses_gatekeeping = None
    capabilities.uses_maintenance_tasks = None
    capabilities.uses_ttm = None
    capabilities.uses_bct_mapping = None
    capabilities.uses_comb_mapping = None

    bundle.capabilities = capabilities
    return bundle