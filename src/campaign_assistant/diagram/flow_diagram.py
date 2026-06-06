from __future__ import annotations

import html
from collections import defaultdict
from dataclasses import dataclass
from typing import Any


_BOX_COLOR = "#e85d24"

_SECONDARY_EDGE_COLORS = [
    "#2E86AB",
    "#A23B72",
    "#3D9970",
    "#8E44AD",
    "#B9770E",
    "#C0392B",
    "#1F618D",
    "#7D6608",
]





@dataclass
class DiagramNode:
    id: str
    label: str
    track_id: str
    task_count: int | None = None
    target_points: int | float | str | None = None
    is_initial: bool = False


@dataclass
class DiagramEdge:
    source: str
    target: str
    transition_type: str


def _is_failure_transition(transition_type: str) -> bool:
    return "failure" in _text(transition_type).lower()


def _is_success_like_transition(transition_type: str) -> bool:
    text = _text(transition_type).lower()
    return (
        "success" in text
        or "standard" in text
        or "transition" in text
        or text == ""
    )


def _stable_edge_color(edge: DiagramEdge) -> str:
    key = f"{edge.source}->{edge.target}:{edge.transition_type}"
    index = sum(ord(char) for char in key) % len(_SECONDARY_EDGE_COLORS)
    return _SECONDARY_EDGE_COLORS[index]


def _as_list(value: Any) -> list[Any]:
    return list(value or []) if isinstance(value, list) else []


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, dict) else {}


def _text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip() or default


def _shorten(text: str, max_chars: int = 28) -> str:
    text = _text(text)
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def _two_line_label(text: str, *, line_chars: int = 18) -> tuple[str, str | None]:
    text = " ".join(_text(text).split())

    if len(text) <= line_chars:
        return text, None

    # Prefer splitting on spaces.
    split_at = text.rfind(" ", 0, line_chars + 1)
    if split_at <= 0:
        split_at = line_chars

    first = text[:split_at].strip()
    rest = text[split_at:].strip()

    if len(rest) <= line_chars:
        return first, rest

    return first, rest[: line_chars - 3].rstrip() + "..."


def _wrap_text_lines(
    text: str,
    *,
    line_chars: int = 24,
    max_lines: int = 3,
) -> list[str]:
    text = " ".join(_text(text).split())

    if not text:
        return [""]

    lines: list[str] = []
    remaining = text

    while remaining and len(lines) < max_lines:
        if len(remaining) <= line_chars:
            lines.append(remaining)
            remaining = ""
            break

        split_at = remaining.rfind(" ", 0, line_chars + 1)
        if split_at <= 0:
            split_at = line_chars

        lines.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()

    if remaining and lines:
        last = lines[-1]
        available = max(line_chars - 3, 1)

        if len(last) > available:
            lines[-1] = last[:available].rstrip() + "..."
        else:
            extra = " " + remaining
            combined = last + extra

            if len(combined) <= line_chars:
                lines[-1] = combined
            else:
                lines[-1] = combined[:available].rstrip() + "..."

    return lines or [""]


def _boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value

    text = str(value).strip().lower()
    return text in {"true", "1", "yes", "y"}


def _challenge_task_counts(snapshot: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)

    for task in _as_list(snapshot.get("tasks")):
        if not isinstance(task, dict):
            continue

        challenge_id = task.get("challenge_id")
        if challenge_id is not None:
            counts[str(challenge_id)] += 1

    return dict(counts)


def _visualization_labels(snapshot: dict[str, Any]) -> dict[str, str]:
    labels: dict[str, str] = {}

    for item in _as_list(snapshot.get("visualizations")):
        if not isinstance(item, dict):
            continue

        visualization_id = item.get("id")
        if visualization_id is None:
            continue

        labels[str(visualization_id)] = _text(
            item.get("name"),
            default=f"Visualization {visualization_id}",
        )

    return labels


def _extract_nodes(snapshot: dict[str, Any]) -> list[DiagramNode]:
    task_counts = _challenge_task_counts(snapshot)
    nodes: list[DiagramNode] = []

    for challenge in _as_list(snapshot.get("challenges")):
        if not isinstance(challenge, dict):
            continue

        challenge_id = challenge.get("id")
        if challenge_id is None:
            continue

        visualization_id = challenge.get("visualization_id")
        track_id = _text(visualization_id, default="unknown")

        label = _text(challenge.get("name"), default=f"Challenge {challenge_id}")

        nodes.append(
            DiagramNode(
                id=str(challenge_id),
                label=label,
                track_id=track_id,
                task_count=task_counts.get(str(challenge_id), 0),
                target_points=challenge.get("target_points"),
                is_initial=_boolish(challenge.get("is_initial_level")),
            )
        )

    return nodes


def _extract_edges(snapshot: dict[str, Any], visible_node_ids: set[str]) -> list[DiagramEdge]:
    edges: list[DiagramEdge] = []

    for transition in _as_list(snapshot.get("transitions")):
        if not isinstance(transition, dict):
            continue

        source = transition.get("source_challenge_id")
        target = transition.get("target_challenge_id")
        transition_type = _text(transition.get("transition_type"), default="transition")

        if source is None or target is None:
            continue

        source_id = str(source)
        target_id = str(target)

        if source_id not in visible_node_ids or target_id not in visible_node_ids:
            continue

        edges.append(
            DiagramEdge(
                source=source_id,
                target=target_id,
                transition_type=transition_type,
            )
        )

    return edges


def _node_sort_key(node: DiagramNode) -> tuple[str, int | str]:
    try:
        numeric_id = int(float(node.id))
        return (node.track_id, numeric_id)
    except Exception:
        return (node.track_id, node.id)


def _group_nodes_by_track(nodes: list[DiagramNode]) -> dict[str, list[DiagramNode]]:
    grouped: dict[str, list[DiagramNode]] = defaultdict(list)

    for node in sorted(nodes, key=_node_sort_key):
        grouped[node.track_id].append(node)

    return dict(grouped)


def _node_numeric_order(node_id: str) -> int | str:
    try:
        return int(float(node_id))
    except Exception:
        return node_id


def _success_edges_for_nodes(
    *,
    node_ids: set[str],
    edges: list[DiagramEdge],
) -> dict[str, str]:
    """
    Return formal success/standard transition map inside one node set.

    Expected normal case:
    source challenge -> success_next challenge

    Self-loops are ignored for row ordering because they do not move the user
    to a next level.
    """
    success_map: dict[str, str] = {}

    for edge in edges:
        if edge.source not in node_ids or edge.target not in node_ids:
            continue

        if edge.source == edge.target:
            continue

        if not _is_success_like_transition(edge.transition_type):
            continue

        if _is_failure_transition(edge.transition_type):
            continue

        # Keep the first formal success-like transition if duplicates exist.
        success_map.setdefault(edge.source, edge.target)

    return success_map


def _order_component_by_success_progression(
    *,
    component_nodes: list[DiagramNode],
    edges: list[DiagramEdge],
) -> list[DiagramNode]:
    """
    Order one connected component by formal success/standard progression.

    Starts from initial levels if available. If no initial level is marked,
    starts from nodes with no incoming success edge. If that is also ambiguous,
    falls back to numeric/id order.
    """
    if not component_nodes:
        return []

    node_by_id = {node.id: node for node in component_nodes}
    node_ids = set(node_by_id)

    success_map = _success_edges_for_nodes(
        node_ids=node_ids,
        edges=edges,
    )

    incoming_success_targets = set(success_map.values())

    initial_starts = [
        node.id for node in component_nodes
        if node.is_initial and node.id in node_ids
    ]

    no_incoming_starts = [
        node.id for node in component_nodes
        if node.id not in incoming_success_targets
    ]

    if initial_starts:
        starts = sorted(initial_starts, key=_node_numeric_order)
    elif no_incoming_starts:
        starts = sorted(no_incoming_starts, key=_node_numeric_order)
    else:
        starts = [sorted(node_ids, key=_node_numeric_order)[0]]

    ordered_ids: list[str] = []
    seen: set[str] = set()

    def follow_success_chain(start_id: str) -> None:
        current = start_id
        local_seen: set[str] = set()

        while current in node_ids and current not in seen:
            if current in local_seen:
                break

            local_seen.add(current)
            seen.add(current)
            ordered_ids.append(current)

            next_id = success_map.get(current)
            if not next_id or next_id == current:
                break

            current = next_id

    for start_id in starts:
        follow_success_chain(start_id)

    # Add remaining nodes deterministically. This covers branches, broken chains,
    # cycles, and unusual exports without losing nodes.
    for node_id in sorted(node_ids, key=_node_numeric_order):
        if node_id not in seen:
            follow_success_chain(node_id)

    return [node_by_id[node_id] for node_id in ordered_ids if node_id in node_by_id]



def _split_track_into_components(
    *,
    track_nodes: list[DiagramNode],
    edges: list[DiagramEdge],
) -> list[list[DiagramNode]]:
    """
    Split one visualization track into disconnected horizontal subtracks.

    This avoids forcing separate progressions within the same visualization onto
    one unreadable row.
    """
    node_by_id = {node.id: node for node in track_nodes}
    node_ids = set(node_by_id)

    adjacency: dict[str, set[str]] = {node_id: set() for node_id in node_ids}

    for edge in edges:
        if edge.source not in node_ids or edge.target not in node_ids:
            continue

        adjacency[edge.source].add(edge.target)
        adjacency[edge.target].add(edge.source)

    components: list[list[DiagramNode]] = []
    visited: set[str] = set()

    for node in sorted(track_nodes, key=lambda item: _node_numeric_order(item.id)):
        if node.id in visited:
            continue

        stack = [node.id]
        component_ids: set[str] = set()

        while stack:
            current = stack.pop()
            if current in visited:
                continue

            visited.add(current)
            component_ids.add(current)

            for neighbour in adjacency.get(current, set()):
                if neighbour not in visited:
                    stack.append(neighbour)

        component_nodes = [
            node_by_id[node_id]
            for node_id in sorted(component_ids, key=_node_numeric_order)
        ]

        ordered_component_nodes = _order_component_by_success_progression(
            component_nodes=component_nodes,
            edges=edges,
        )

        components.append(ordered_component_nodes)

    return components


def _build_track_rows(
    *,
    grouped: dict[str, list[DiagramNode]],
    edges: list[DiagramEdge],
) -> list[tuple[str, int, list[DiagramNode]]]:
    """
    Return rows as (track_id, subtrack_index, nodes).

    One visualization can produce multiple subtracks if it contains disconnected
    level progressions.
    """
    rows: list[tuple[str, int, list[DiagramNode]]] = []

    for track_id, track_nodes in grouped.items():
        components = _split_track_into_components(
            track_nodes=track_nodes,
            edges=edges,
        )

        for component_index, component_nodes in enumerate(components, start=1):
            rows.append((track_id, component_index, component_nodes))

    return rows


def _svg_text(
    *,
    x: int,
    y: int,
    text: str,
    size: int = 12,
    weight: str = "normal",
    anchor: str = "middle",
    fill: str = "#222",
) -> str:
    return (
        f'<text x="{x}" y="{y}" font-family="Arial, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" '
        f'fill="{fill}">{html.escape(text)}</text>'
    )


def _svg_multiline_text(
    *,
    x: int,
    y_center: int,
    lines: list[str],
    size: int = 10,
    weight: str = "normal",
    anchor: str = "middle",
    fill: str = "#222",
    line_height: int = 12,
) -> str:
    if not lines:
        return ""

    start_y = y_center - ((len(lines) - 1) * line_height) // 2 + 4

    return "\n".join(
        _svg_text(
            x=x,
            y=start_y + index * line_height,
            text=line,
            size=size,
            weight=weight,
            anchor=anchor,
            fill=fill,
        )
        for index, line in enumerate(lines)
    )


def _svg_box(
    *,
    x: int,
    y: int,
    width: int,
    height: int,
    label: str,
    subtitle: str,
    is_initial: bool = False,
) -> str:
    line1, line2 = _two_line_label(label, line_chars=26)
    subtitle = _shorten(subtitle, 28)
    stroke_width = 1.1

    text_lines = [
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="6" ry="6" '
        f'fill="#ffffff" stroke="#e85d24" stroke-width="{stroke_width}"/>',
    ]

    if line2:
        text_lines.extend(
            [
                _svg_text(
                    x=x + width // 2,
                    y=y + 16,
                    text=line1,
                    size=10,
                    weight="bold",
                ),
                _svg_text(
                    x=x + width // 2,
                    y=y + 29,
                    text=line2,
                    size=10,
                    weight="bold",
                ),
                _svg_text(
                    x=x + width // 2,
                    y=y + 42,
                    text=subtitle,
                    size=8,
                    fill="#555",
                ),
            ]
        )
    else:
        text_lines.extend(
            [
                _svg_text(
                    x=x + width // 2,
                    y=y + 20,
                    text=line1,
                    size=10,
                    weight="bold",
                ),
                _svg_text(
                    x=x + width // 2,
                    y=y + 37,
                    text=subtitle,
                    size=8,
                    fill="#555",
                ),
            ]
        )

    return "\n".join(text_lines)


def _svg_main_edge(
    *,
    source_center: tuple[int, int],
    target_center: tuple[int, int],
    node_half_width: int,
) -> str:
    x1, y1 = source_center
    x2, y2 = target_center

    start_x = x1 + node_half_width + 3
    end_x = x2 - node_half_width - 3

    if end_x <= start_x:
        return ""

    return (
        f'<path d="M {start_x} {y1} L {end_x} {y2}" '
        f'fill="none" stroke="{_BOX_COLOR}" stroke-width="1.5" '
        f'marker-end="url(#arrow)"/>'
    )


def _svg_secondary_edge(
    *,
    edge: DiagramEdge,
    source_center: tuple[int, int],
    target_center: tuple[int, int],
    show_labels: bool,
    node_half_width: int,
    edge_index: int = 0,
) -> str:
    x1, y1 = source_center
    x2, y2 = target_center

    is_failure = _is_failure_transition(edge.transition_type)
    is_loop = x1 == x2 and y1 == y2

    stroke_dash = 'stroke-dasharray="5,4"' if is_failure else ""
    color = _BOX_COLOR if is_loop else _stable_edge_color(edge)

    # Success/standard above, failure below.
    direction = 1 if is_failure else -1
    lane_offset = 24 + (edge_index % 3) * 10

    start_x = x1 + node_half_width + 3
    end_x = x2 - node_half_width - 3

    if is_loop:
        loop_y = y1 + direction * lane_offset
        path = (
            f"M {x1 + node_half_width - 8} {y1} "
            f"C {x1 + node_half_width + 54} {loop_y - 34 * direction}, "
            f"{x1 + node_half_width + 54} {loop_y + 34 * direction}, "
            f"{x1 + node_half_width - 8} {y1 + direction * 14}"
        )

        label = ""
        if show_labels:
            label = _svg_text(
                x=x1 + node_half_width + 56,
                y=loop_y,
                text=edge.transition_type,
                size=9,
                fill="#444",
            )

        return "\n".join(
            [
                f'<path d="{path}" fill="none" stroke="{color}" stroke-width="1.2" '
                f'marker-end="url(#arrow)" {stroke_dash}/>',
                label,
            ]
        )

    # Same row.
    if abs(y1 - y2) < 8:
        curve_y = y1 + direction * lane_offset
        mid_x = (start_x + end_x) // 2

        if end_x >= start_x:
            path = (
                f"M {start_x} {y1} "
                f"C {mid_x} {curve_y}, {mid_x} {curve_y}, {end_x} {y2}"
            )
        else:
            higher_curve_y = y1 + direction * (lane_offset + 34)
            path = (
                f"M {start_x} {y1} "
                f"C {start_x + 38} {higher_curve_y}, "
                f"{end_x - 38} {higher_curve_y}, {end_x} {y2}"
            )
            curve_y = higher_curve_y

        label = ""
        if show_labels:
            label = _svg_text(
                x=mid_x,
                y=curve_y - 4 if direction < 0 else curve_y + 12,
                text=edge.transition_type,
                size=9,
                fill="#444",
            )

        return "\n".join(
            [
                f'<path d="{path}" fill="none" stroke="{color}" stroke-width="1.2" '
                f'marker-end="url(#arrow)" {stroke_dash}/>',
                label,
            ]
        )

    # Cross-row edge.
    mid_x = (start_x + end_x) // 2
    path = f"M {start_x} {y1} C {mid_x} {y1}, {mid_x} {y2}, {end_x} {y2}"

    label = ""
    if show_labels:
        label = _svg_text(
            x=mid_x,
            y=(y1 + y2) // 2 - 6,
            text=edge.transition_type,
            size=9,
            fill="#444",
        )

    return "\n".join(
        [
            f'<path d="{path}" fill="none" stroke="{color}" stroke-width="1.2" '
            f'marker-end="url(#arrow)" {stroke_dash}/>',
            label,
        ]
    )


def _empty_svg(message: str) -> str:
    width = 900
    height = 180

    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}">',
            f'<rect x="0" y="0" width="{width}" height="{height}" fill="#fafafa"/>',
            _svg_text(x=width // 2, y=90, text=message, size=16, weight="bold"),
            "</svg>",
        ]
    )


def build_campaign_flow_svg(
    snapshot: dict[str, Any],
    *,
    max_nodes: int = 120,
    show_edge_labels: bool = False,
) -> str:
    """
    Build a simple dependency-free SVG campaign-flow diagram.

    Layout:
    - each track is a horizontal row;
    - each track usually corresponds to one visualization;
    - challenge/level nodes progress left to right;
    - success/failure transitions are drawn as arrows;
    - edge labels are optional because dense campaigns become unreadable quickly.
    """
    snapshot = _as_dict(snapshot)
    nodes = _extract_nodes(snapshot)

    if not nodes:
        return _empty_svg("No challenge/level data available for a flow diagram.")

    truncated = False
    if len(nodes) > max_nodes:
        nodes = nodes[:max_nodes]
        truncated = True

    visible_node_ids = {node.id for node in nodes}
    edges = _extract_edges(snapshot, visible_node_ids)
    grouped = _group_nodes_by_track(nodes)
    track_labels = _visualization_labels(snapshot)
    track_rows = _build_track_rows(grouped=grouped, edges=edges)

    box_width = 126
    box_height = 50
    node_gap_x = 30
    track_gap_y = 42
    margin_x = 165
    margin_y = 74
    right_margin = 60
    bottom_margin = 52

    max_track_nodes = max(len(row_nodes) for _, _, row_nodes in track_rows)

    width = (
            margin_x
            + max_track_nodes * box_width
            + max(0, max_track_nodes - 1) * node_gap_x
            + right_margin
    )
    height = margin_y + len(track_rows) * (box_height + track_gap_y) + bottom_margin

    node_centers: dict[str, tuple[int, int]] = {}
    node_boxes: list[str] = []
    edge_parts: list[str] = []

    title = _text(snapshot.get("campaign_name"), default="Campaign flow diagram")
    file_name = _text(snapshot.get("file_name"))

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        """
<defs>
  <marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3"
          orient="auto" markerUnits="strokeWidth">
    <path d="M0,0 L0,6 L9,3 z" fill="context-stroke" />
  </marker>
</defs>
""",
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#fafafa"/>',
        _svg_text(x=width // 2, y=30, text=title, size=18, weight="bold"),
    ]

    if file_name:
        parts.append(_svg_text(x=width // 2, y=52, text=file_name, size=11, fill="#555"))

    if truncated:
        parts.append(
            _svg_text(
                x=width // 2,
                y=72,
                text=f"Diagram truncated to first {max_nodes} challenge/level nodes.",
                size=10,
                fill="#555",
            )
        )

    previous_track_id: str | None = None

    for row_idx, (track_id, subtrack_index, row_nodes) in enumerate(track_rows):
        y = margin_y + row_idx * (box_height + track_gap_y)

        track_label = track_labels.get(track_id, f"Visualization {track_id}")

        if track_id != previous_track_id:
            label_lines = _wrap_text_lines(
                track_label,
                line_chars=24,
                max_lines=3,
            )

            label_svg = _svg_multiline_text(
                x=margin_x - 22,
                y_center=y + box_height // 2,
                lines=label_lines,
                size=10,
                weight="bold",
                anchor="end",
            )
        else:
            label_svg = _svg_text(
                x=margin_x - 22,
                y=y + box_height // 2 + 4,
                text=f"↳ track {subtrack_index}",
                size=10,
                weight="normal",
                anchor="end",
            )

        previous_track_id = track_id

        parts.append(label_svg)

        # Track guide line.
        parts.append(
            f'<line x1="{margin_x - 8}" y1="{y + box_height // 2}" '
            f'x2="{width - right_margin}" y2="{y + box_height // 2}" '
            f'stroke="#e6e6e6" stroke-width="1"/>'
        )

        for node_idx, node in enumerate(row_nodes):
            x = margin_x + node_idx * (box_width + node_gap_x)

            subtitle_parts = []
            if node.task_count is not None:
                subtitle_parts.append(f"{node.task_count} task(s)")
            if node.target_points not in (None, ""):
                subtitle_parts.append(f"target: {node.target_points}")

            subtitle = " · ".join(subtitle_parts) or f"ID: {node.id}"

            node_boxes.append(
                _svg_box(
                    x=x,
                    y=y,
                    width=box_width,
                    height=box_height,
                    label=node.label,
                    subtitle=subtitle,
                    is_initial=node.is_initial,
                )
            )

            node_centers[node.id] = (
                x + box_width // 2,
                y + box_height // 2,
            )

    node_half_width = box_width // 2
    main_edge_keys: set[tuple[str, str]] = set()

    # Adjacent displayed pairs after success-chain ordering.
    adjacent_row_pairs: set[tuple[str, str]] = set()
    for _, _, row_nodes in track_rows:
        for source_node, target_node in zip(row_nodes, row_nodes[1:]):
            adjacent_row_pairs.add((source_node.id, target_node.id))

    # Main progression arrows are formal workbook transitions only:
    # success/standard transition to the nearest displayed level on the right.
    for edge in edges:
        if (
                (edge.source, edge.target) in adjacent_row_pairs
                and _is_success_like_transition(edge.transition_type)
                and not _is_failure_transition(edge.transition_type)
        ):
            source_center = node_centers.get(edge.source)
            target_center = node_centers.get(edge.target)

            if source_center is None or target_center is None:
                continue

            main_edge_keys.add((edge.source, edge.target))

            edge_parts.append(
                _svg_main_edge(
                    source_center=source_center,
                    target_center=target_center,
                    node_half_width=node_half_width,
                )
            )

    # Secondary workbook transitions.
    for edge_index, edge in enumerate(edges):
        source_center = node_centers.get(edge.source)
        target_center = node_centers.get(edge.target)

        if source_center is None or target_center is None:
            continue

        # If the workbook success/standard transition is exactly the next box to
        # the right, the main progression arrow already communicates it.
        if (
                (edge.source, edge.target) in main_edge_keys
                and _is_success_like_transition(edge.transition_type)
                and not _is_failure_transition(edge.transition_type)
        ):
            continue

        edge_parts.append(
            _svg_secondary_edge(
                edge=edge,
                source_center=source_center,
                target_center=target_center,
                show_labels=show_edge_labels,
                node_half_width=node_half_width,
                edge_index=edge_index,
            )
        )

    parts.extend(edge_parts)
    parts.extend(node_boxes)

    # Legend.
    legend_y = height - 24
    parts.append(
        _svg_text(
            x=margin_x,
            y=legend_y,
            text="Orange arrows = direct success/standard transition to next level",
            size=10,
            anchor="start",
            fill="#555",
        )
    )
    parts.append(
        _svg_text(
            x=margin_x + 430,
            y=legend_y,
            text="Colored curves = other transitions",
            size=10,
            anchor="start",
            fill="#555",
        )
    )
    parts.append(
        _svg_text(
            x=margin_x + 660,
            y=legend_y,
            text="Dashed = failure transition",
            size=10,
            anchor="start",
            fill="#555",
        )
    )

    parts.append("</svg>")
    return "\n".join(parts)