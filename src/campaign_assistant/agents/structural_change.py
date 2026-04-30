from __future__ import annotations

from typing import Any

from campaign_assistant.agents.base import BaseAgent
from campaign_assistant.orchestration.models import AgentContext, AgentResponse
from campaign_assistant.privacy import PrivacyService
from campaign_assistant.validators import ValidationContext, build_default_validator_registry


def _empty_result(selected_checks: list[str]) -> dict[str, Any]:
    return {
        "file_name": "",
        "analyzed_at": "",
        "checks_run": list(selected_checks),
        "summary": {
            "total_issues": 0,
            "passed_checks": [],
            "failed_checks": [],
            "errored_checks": [],
            "issue_count_by_check": {name: 0 for name in selected_checks},
        },
        "waves": [],
        "issues_by_check": {name: [] for name in selected_checks},
        "prioritized_issues": [],
        "notes": [],
        "excel_report_path": None,
    }


def _merge_checker_payload(base: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    if not payload:
        return base

    if not base.get("file_name"):
        for key in ["file_name", "analyzed_at", "waves", "excel_report_path"]:
            if key in payload:
                base[key] = payload.get(key)

    base["checks_run"] = list(dict.fromkeys((base.get("checks_run") or []) + (payload.get("checks_run") or [])))

    base_summary = base.setdefault("summary", {})
    payload_summary = payload.get("summary", {}) or {}

    for key in ["passed_checks", "failed_checks", "errored_checks"]:
        merged = list(dict.fromkeys((base_summary.get(key) or []) + (payload_summary.get(key) or [])))
        base_summary[key] = merged

    counts = dict(base_summary.get("issue_count_by_check") or {})
    for name, value in (payload_summary.get("issue_count_by_check") or {}).items():
        counts[name] = counts.get(name, 0) + int(value or 0)
    base_summary["issue_count_by_check"] = counts

    issues_by_check = base.setdefault("issues_by_check", {})
    for name, items in (payload.get("issues_by_check") or {}).items():
        issues_by_check.setdefault(name, [])
        issues_by_check[name].extend(items)

    prioritized = base.setdefault("prioritized_issues", [])
    prioritized.extend(payload.get("prioritized_issues") or [])
    prioritized.sort(
        key=lambda item: (
            3 if item.get("severity") == "high" else 2 if item.get("severity") == "medium" else 1,
            1 if item.get("active_wave") else 0,
        ),
        reverse=True,
    )
    base["prioritized_issues"] = prioritized[:25]

    notes = base.setdefault("notes", [])
    notes.extend(payload.get("notes") or [])

    total_issues = sum(len(items) for items in issues_by_check.values())
    base_summary["total_issues"] = total_issues
    return base


class StructuralChangeAgent(BaseAgent):
    name = "structural_change_agent"

    def __init__(self) -> None:
        self.registry = build_default_validator_registry()
        self.privacy_service = PrivacyService()

    def run(self, context: AgentContext) -> AgentResponse:
        run_info = (
            self.privacy_service.start_agent_run(self.name, context)
            if "privacy_state" in context.shared
            else {}
        )
        agent_run_id = run_info.get("agent_run_id")

        validation_context = ValidationContext(
            file_path=context.file_path,
            selected_checks=context.selected_checks,
            export_excel=context.export_excel,
            analysis_profile=context.analysis_profile,
            point_rules=context.point_rules,
            task_roles=context.task_roles,
            metadata_bundle=context.shared.get("metadata_bundle"),
            capability_summary=context.shared.get("capability_summary", {}),
        )

        result = _empty_result(context.selected_checks)
        validator_names: list[str] = []

        for validator in self.registry.resolve(validation_context):
            validator_names.append(validator.name)
            validator_result = validator.run(validation_context)
            payload = validator_result.payload or {}

            if validator.name in {"point_gatekeeping", "gatekeeping_semantics"}:
                result["point_gatekeeping"] = payload
            elif isinstance(payload, dict) and "summary" in payload and "issues_by_check" in payload:
                result = _merge_checker_payload(result, payload)

            if validator_result.notes:
                result.setdefault("notes", []).extend(validator_result.notes)

        result.setdefault("point_gatekeeping", {"summary": {"challenge_findings": 0}, "findings": []})
        context.shared["result"] = result

        summary = result.get("summary", {})
        failed_checks = summary.get("failed_checks", [])
        total_issues = summary.get("total_issues", 0)
        pg_summary = (result.get("point_gatekeeping", {}) or {}).get("summary", {})
        pg_findings = pg_summary.get("challenge_findings", 0)

        if failed_checks:
            text = (
                f"Structural analysis found {total_issues} issue(s). "
                f"Failed checks: {', '.join(failed_checks)}."
            )
        else:
            text = "Structural analysis found no failed checks."

        if pg_findings:
            text += f" Point/gatekeeping analysis highlighted {pg_findings} challenge(s) that may require attention."

        payload = {
            "result_summary": summary,
            "excel_report_path": result.get("excel_report_path"),
            "point_gatekeeping_summary": pg_summary,
            "validator_names": validator_names,
        }

        self.privacy_service.record_agent_outcome(
            agent_name=self.name,
            context=context,
            agent_run_id=agent_run_id,
            success=True,
            payload=payload,
            warnings=[],
            notes=list(result.get("notes", []) or []),
        )

        return AgentResponse(
            agent_name=self.name,
            success=True,
            summary=text,
            payload=payload,
        )