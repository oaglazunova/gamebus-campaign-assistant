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
