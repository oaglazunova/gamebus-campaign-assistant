from __future__ import annotations

from campaign_assistant.diagram import build_campaign_flow_svg
from campaign_assistant.diagram.flow_diagram import (
    _build_component_layouts,
    _extract_edges,
    _extract_nodes,
    _group_nodes_by_track,
    _is_failure_transition,
    _is_success_like_transition,
)


def test_diagram_generates_svg(minimal_analysis_result: dict) -> None:
    svg = build_campaign_flow_svg(minimal_analysis_result["campaign_snapshot"])

    assert svg.startswith("<svg")
    assert "Beginner" in svg
    assert "Balanced eater" in svg
    assert "Food master" in svg
    assert "Direct progression" in svg
    assert "Failure transition" in svg
    assert (
        "Alternative success / loop / return"
        in svg
)


def test_diagram_main_progression_is_based_on_formal_success_edges(
    minimal_analysis_result: dict,
) -> None:
    snapshot = minimal_analysis_result["campaign_snapshot"]

    nodes = _extract_nodes(snapshot)
    visible_node_ids = {node.id for node in nodes}
    edges = _extract_edges(snapshot, visible_node_ids)
    grouped = _group_nodes_by_track(nodes)
    component_layouts = _build_component_layouts(
        grouped=grouped,
        edges=edges,
    )

    formal_success_pairs = {
        (edge.source, edge.target)
        for edge in edges
        if _is_success_like_transition(edge.transition_type)
        and not _is_failure_transition(edge.transition_type)
        and edge.source != edge.target
    }

    adjacent_spine_pairs = {
        pair
        for layout in component_layouts
        for pair in zip(
            layout.spine_ids,
            layout.spine_ids[1:],
        )
    }

    main_edges = (
            adjacent_spine_pairs
            & formal_success_pairs
    )

    assert ("1", "2") in main_edges
    assert ("2", "3") in main_edges
    assert main_edges.issubset(formal_success_pairs)


def test_reverse_attached_unreachable_branch_is_placed_near_its_targets() -> None:
    snapshot = {
        "visualizations": [
            {
                "id": 10,
                "name": "Progression",
            },
        ],
        "challenges": [
            {
                "id": 1,
                "name": "Beginner",
                "visualization_id": 10,
                "is_initial_level": True,
            },
            {
                "id": 2,
                "name": "Proficient",
                "visualization_id": 10,
                "is_initial_level": False,
            },
            {
                "id": 3,
                "name": "Skilled",
                "visualization_id": 10,
                "is_initial_level": False,
            },
            {
                "id": 99,
                "name": "Skilled at risk",
                "visualization_id": 10,
                "is_initial_level": False,
            },
        ],
        "tasks": [],
        "transitions": [
            {
                "source_challenge_id": 1,
                "target_challenge_id": 2,
                "transition_type": "success",
            },
            {
                "source_challenge_id": 2,
                "target_challenge_id": 3,
                "transition_type": "success",
            },
            # Challenge 99 has no incoming transition, so it is unreachable.
            # It nevertheless points back to two neighbouring progression levels.
            {
                "source_challenge_id": 99,
                "target_challenge_id": 3,
                "transition_type": "success",
            },
            {
                "source_challenge_id": 99,
                "target_challenge_id": 2,
                "transition_type": "failure",
            },
        ],
    }

    nodes = _extract_nodes(snapshot)
    edges = _extract_edges(
        snapshot,
        {node.id for node in nodes},
    )
    grouped = _group_nodes_by_track(nodes)

    layouts = _build_component_layouts(
        grouped=grouped,
        edges=edges,
    )

    placements = {
        node.id: (column, lane)
        for layout in layouts
        for node, column, lane in layout.placements
    }

    assert placements["1"] == (0, 0)
    assert placements["2"] == (2, 0)
    assert placements["3"] == (4, 0)

    # The unreachable branch should be displayed next to the levels it
    # references, rather than being pushed to the beginning of the row.
    assert placements["99"] == (3, 1)