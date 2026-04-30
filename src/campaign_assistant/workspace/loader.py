from __future__ import annotations

import csv
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from campaign_assistant.session_logging import utc_now_iso


@dataclass(slots=True)
class WorkspaceBundle:
    workspace_id: str
    root_dir: Path
    snapshot_id: str
    snapshot_path: Path
    workspace_meta: dict[str, Any]
    analysis_profile: dict[str, Any]
    point_rules: dict[str, Any]
    task_roles: list[dict[str, str]]
    evidence_index: dict[str, Any]


def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-{2,}", "-", value)
    return value.strip("-") or "campaign"


def _app_home() -> Path:
    root = Path.home() / ".gamebus_campaign_assistant"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _workspaces_home() -> Path:
    root = _app_home() / "workspaces"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return data or {}


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, sort_keys=False, allow_unicode=True)


def _read_task_roles_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        return [dict(row) for row in reader]


def _write_default_task_roles_csv(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["task_id", "task_name", "role", "notes"],
        )
        writer.writeheader()


def _default_workspace_meta(workspace_id: str, campaign_name: str) -> dict[str, Any]:
    now = utc_now_iso()
    return {
        "workspace_id": workspace_id,
        "name": campaign_name,
        "description": f"Workspace for {campaign_name}",
        "created_at": now,
        "updated_at": now,
        "campaign_identity": {
            "external_name": campaign_name,
            "gamebus_campaign_id": None,
            "country": None,
            "subgroup": None,
            "trial": None,
        },
        "defaults": {
            "latest_snapshot_id": None,
            "analysis_profile_version": 1,
            "language": "en",
        },
        "status": {
            "active": True,
            "archived": False,
        },
    }


def _default_analysis_profile(campaign_name: str) -> dict[str, Any]:
    return {
        "profile_version": 1,
        "name": f"{campaign_name} profile",
        "profile_notes": [
            "This default profile is created automatically.",
            "Review and adapt it before relying on theory- or point-sensitive checks.",
            "The current default assumes the long-term trial style and can be changed per campaign.",
        ],
        "intervention_model": {
            "uses_ttm": True,
            "uses_relapse_levels": True,
            "uses_gatekeeping": True,
            "uses_maintenance_tasks": True,
            "uses_bct_mapping": False,
            "uses_comb_mapping": False,
        },
        "checking_scope": {
            "structural_checks": True,
            "theory_checks": True,
            "point_gatekeeping_checks": True,
            "content_fix_suggestions": True,
            "comparison_checks": True,
        },
        "subgroup_unit": {
            "primary_axes": [
                "age_group",
                "country",
                "treatment_group",
                "wave",
            ],
            "subgroup_relevance_required": True,
        },
        "ttm": {
            "structure_file": "evidence/theory/ttm_structure.pdf",
            "operational_mode": "explicit_profile",
            "stage_model": "classic_ttm",
            "stages": [
                "precontemplation",
                "contemplation",
                "preparation",
                "action",
                "maintenance",
            ],
            "level_structure_mode": "campaign_specific",
        },
        "gatekeeping": {
            "explicit_task_role_required": False,
            "infer_if_missing": True,
            "role_file": "task_roles.csv",
            "must_require_gatekeeper_for_progression": True,
        },
        "maintenance": {
            "explicit_task_role_required": False,
            "infer_if_missing": True,
            "at_risk_levels_should_use_maintenance_tasks_only": True,
        },
        "points": {
            "rule_file": "point_rules.yaml",
            "strict_reachability_check": True,
            "suggest_fixes": True,
        },
        "theory_grounding": {
            "mapped_interventions_file": "evidence/theory/intervention_mapping.xlsx",
            "bct_mode": "explanation",
            "comb_mode": "explanation",
            "ttm_mode": "operational_check",
        },
        "privacy": {
            "campaign_file_access": "allowed",
            "workshop_transcripts_access": "restricted",
            "historical_outcomes_access": "aggregate_only",
            "redact_sensitive_fields_before_content_fixer": True,
        },
        "execution_preferences": {
            "role_annotation_target": "task_roles_csv",
        },
    }


def _default_point_rules() -> dict[str, Any]:
    return {
        "rule_version": 1,
        "name": "Default point and gatekeeping rules",
        "rule_notes": [
            "This file should be reviewed with campaign organizers.",
            "Rules may differ by trial or pilot.",
        ],
        "general": {
            "target_points_must_be_reachable": True,
            "progression_should_require_gatekeeper": True,
            "suggest_corrections": True,
        },
        "gatekeeping": {
            "required_for_level_progression": True,
            "infer_from": [
                "point_weight",
                "repetition_constraints",
                "target_threshold_dependency",
            ],
            "explicit_role_preferred": True,
        },
        "maintenance": {
            "at_risk_return_should_depend_on_maintenance_tasks": True,
            "maintenance_only_max_points_should_be_checked": True,
            "maintenance_return_threshold_policy": "custom",
        },
        "relapse": {
            "at_risk_levels_enabled": True,
            "return_to_main_path_requires_maintenance_threshold": True,
            "fallback_to_previous_level_if_threshold_not_met": True,
        },
        "warnings": {
            "raise_if_level_reachable_without_gatekeeper": True,
            "raise_if_target_points_exceed_theoretical_max": True,
            "raise_if_task_text_conflicts_with_configuration": True,
        },
    }


def _default_evidence_index() -> dict[str, Any]:
    return {
        "evidence": {
            "templates": [],
            "theory": [],
            "workshops": [],
            "outcomes": [],
            "misc": [],
        }
    }


def _ensure_workspace_dirs(root: Path) -> None:
    for rel in [
        "snapshots",
        "evidence/templates",
        "evidence/workshops",
        "evidence/theory",
        "evidence/outcomes",
        "evidence/misc",
        "outputs/reports",
        "outputs/patches",
        "outputs/comparisons",
        "traces",
        "sessions",
    ]:
        (root / rel).mkdir(parents=True, exist_ok=True)


def _ensure_workspace_files(root: Path, workspace_id: str, campaign_name: str) -> None:
    workspace_yaml = root / "workspace.yaml"
    analysis_profile_yaml = root / "analysis_profile.yaml"
    point_rules_yaml = root / "point_rules.yaml"
    task_roles_csv = root / "task_roles.csv"
    evidence_index_yaml = root / "evidence_index.yaml"

    if not workspace_yaml.exists():
        _write_yaml(workspace_yaml, _default_workspace_meta(workspace_id, campaign_name))

    if not analysis_profile_yaml.exists():
        _write_yaml(analysis_profile_yaml, _default_analysis_profile(campaign_name))

    if not point_rules_yaml.exists():
        _write_yaml(point_rules_yaml, _default_point_rules())

    if not task_roles_csv.exists():
        _write_default_task_roles_csv(task_roles_csv)

    if not evidence_index_yaml.exists():
        _write_yaml(evidence_index_yaml, _default_evidence_index())


def _create_snapshot(root: Path, campaign_file: Path) -> tuple[str, Path]:
    snapshot_id = utc_now_iso().replace(":", "-").replace(".", "-")
    snapshot_dir = root / "snapshots" / snapshot_id
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    snapshot_path = snapshot_dir / "campaign.xlsx"
    shutil.copy2(campaign_file, snapshot_path)

    metadata = {
        "snapshot_id": snapshot_id,
        "uploaded_at": utc_now_iso(),
        "source": "manual_upload",
        "original_filename": campaign_file.name,
        "original_path": str(campaign_file),
    }
    _write_yaml(snapshot_dir / "metadata.yaml", metadata)

    return snapshot_id, snapshot_path


def _update_workspace_latest_snapshot(root: Path, snapshot_id: str) -> dict[str, Any]:
    workspace_yaml = root / "workspace.yaml"
    workspace_meta = _read_yaml(workspace_yaml)
    workspace_meta.setdefault("defaults", {})
    workspace_meta["defaults"]["latest_snapshot_id"] = snapshot_id
    workspace_meta["updated_at"] = utc_now_iso()
    _write_yaml(workspace_yaml, workspace_meta)
    return workspace_meta


def get_or_create_workspace_for_campaign(
    campaign_file: str | Path,
    workspace_id: str | None = None,
) -> WorkspaceBundle:
    campaign_path = Path(campaign_file).resolve()
    campaign_name = campaign_path.stem
    workspace_id = workspace_id or _slugify(campaign_name)

    root = _workspaces_home() / workspace_id
    root.mkdir(parents=True, exist_ok=True)

    _ensure_workspace_dirs(root)
    _ensure_workspace_files(root, workspace_id, campaign_name)

    snapshot_id, snapshot_path = _create_snapshot(root, campaign_path)
    workspace_meta = _update_workspace_latest_snapshot(root, snapshot_id)

    analysis_profile = _read_yaml(root / "analysis_profile.yaml")
    point_rules = _read_yaml(root / "point_rules.yaml")
    task_roles = _read_task_roles_csv(root / "task_roles.csv")
    evidence_index = _read_yaml(root / "evidence_index.yaml")

    return WorkspaceBundle(
        workspace_id=workspace_id,
        root_dir=root,
        snapshot_id=snapshot_id,
        snapshot_path=snapshot_path,
        workspace_meta=workspace_meta,
        analysis_profile=analysis_profile,
        point_rules=point_rules,
        task_roles=task_roles,
        evidence_index=evidence_index,
    )