from __future__ import annotations

from collections import defaultdict
from typing import Any


def _issue_family(proposal: dict[str, Any]) -> str:
    action_type = str(proposal.get("action_type") or "").strip().lower()

    mapping = {
        "annotate_gatekeeper": "missing_explicit_gatekeeper",
        "strengthen_gatekeeping": "gatekeeping_not_required_by_points",
        "annotate_maintenance_tasks": "missing_explicit_maintenance",
        "set_target_points": "missing_target_points",
        "lower_target_points": "unreachable_target_points",
        "manual_ttm_review": "ttm_manual_review",
    }
    return mapping.get(action_type, action_type or "other")


def _group_key(proposal: dict[str, Any]) -> tuple[str, str, str]:
    return (
        _issue_family(proposal),
        str(proposal.get("category") or ""),
        str(proposal.get("severity") or ""),
    )


def _group_status(statuses: list[str]) -> str:
    unique = sorted(set(statuses))
    if len(unique) == 1:
        return unique[0]
    return "mixed"


def _family_label(issue_family: str) -> str:
    labels = {
        "missing_explicit_gatekeeper": "Missing explicit gatekeeper annotation",
        "gatekeeping_not_required_by_points": "Gatekeeping not required by current point logic",
        "missing_explicit_maintenance": "Missing explicit maintenance annotation",
        "missing_target_points": "Missing target points",
        "unreachable_target_points": "Unreachable target points",
        "ttm_manual_review": "TTM manual review required",
    }
    return labels.get(issue_family, issue_family.replace("_", " ").strip().capitalize())


def _build_group_summary(
    *,
    issue_family: str,
    member_count: int,
    challenge_names: list[str],
) -> str:
    label = _family_label(issue_family)

    unique_challenges = [c for c in challenge_names if c]
    unique_challenges = sorted(set(unique_challenges))

    if issue_family == "ttm_manual_review":
        return f"{label} ({member_count} proposal(s))"

    if len(unique_challenges) == 1:
        return f"{label} in {unique_challenges[0]} ({member_count} proposal(s))"

    if len(unique_challenges) > 1:
        return f"{label} across {len(unique_challenges)} challenges ({member_count} proposal(s))"

    return f"{label} ({member_count} proposal(s))"


def build_proposal_groups(proposals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Build UI-oriented grouped proposal rows.

    New behavior:
    - group by issue family + category + severity
    - preserve raw proposal IDs for execution
    - expose a human-readable summary for the UI
    """
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for proposal in proposals:
        grouped[_group_key(proposal)].append(proposal)

    output: list[dict[str, Any]] = []

    for idx, (key, members) in enumerate(sorted(grouped.items(), key=lambda x: x[0]), start=1):
        issue_family, category, severity = key

        member_ids = [str(m.get("proposal_id")) for m in members if m.get("proposal_id")]
        statuses = [str(m.get("status", "proposed")) for m in members]
        challenge_names = [str(m.get("challenge_name") or "General") for m in members]

        rationales = []
        seen_rationales = set()
        for m in members:
            rationale = str(m.get("rationale", "") or "").strip()
            if rationale and rationale not in seen_rationales:
                rationales.append(rationale)
                seen_rationales.add(rationale)

        notes = []
        seen_notes = set()
        for m in members:
            note = str(m.get("notes", "") or "").strip()
            if note and note not in seen_notes:
                notes.append(note)
                seen_notes.add(note)

        output.append(
            {
                "group_id": f"group-{idx}",
                "issue_family": issue_family,
                "issue_label": _family_label(issue_family),
                "summary": _build_group_summary(
                    issue_family=issue_family,
                    member_count=len(members),
                    challenge_names=challenge_names,
                ),
                "category": category,
                "severity": severity,
                "status": _group_status(statuses),
                "member_count": len(members),
                "member_proposal_ids": member_ids,
                "challenge_names": sorted(set(challenge_names)),
                "rationales": rationales,
                "notes": notes,
                "members": members,
            }
        )

    return output