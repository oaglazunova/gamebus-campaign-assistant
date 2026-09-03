from __future__ import annotations

import html
from collections import defaultdict
from dataclasses import dataclass
from typing import Any


_BOX_COLOR = "#e85d24"
_SUCCESS_EDGE_COLOR = "#e85d24"
_FAILURE_EDGE_COLOR = "#2e6fbb"
_OTHER_EDGE_COLOR = "#6b7280"
_LOOP_EDGE_COLOR = "#7c3aed"

_INITIAL_BORDER_COLOR = "#15803d"
_INITIAL_FILL_COLOR = "#f0fdf4"


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
		or text in {"", "transition"}
	)


def _is_other_transition(edge: DiagramEdge) -> bool:
	return (
		not _is_failure_transition(edge.transition_type)
		and not _is_success_like_transition(edge.transition_type)
	)


def _edge_color(edge: DiagramEdge) -> str:
	if _is_failure_transition(edge.transition_type):
		return _FAILURE_EDGE_COLOR

	if _is_success_like_transition(edge.transition_type):
		return _SUCCESS_EDGE_COLOR

	return _OTHER_EDGE_COLOR


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


@dataclass
class DiagramComponentLayout:
	track_id: str
	subtrack_index: int
	placements: list[tuple[DiagramNode, int, int]]
	spine_ids: list[str]
	min_lane: int
	max_lane: int
	max_column: int


def _safe_node_id_sort_key(node_id: str) -> tuple[int, int | str]:
	try:
		return 0, int(float(node_id))
	except Exception:
		return 1, node_id


def _primary_spine_ids(
	*,
	component_nodes: list[DiagramNode],
	edges: list[DiagramEdge],
) -> list[str]:
	"""
	Return only the direct success progression.

	Branches reachable through failure or unusual transitions are deliberately
	excluded from the central line.
	"""
	node_ids = {node.id for node in component_nodes}

	success_map = _success_edges_for_nodes(
		node_ids=node_ids,
		edges=edges,
	)

	incoming_success = set(success_map.values())

	initial_starts = sorted(
		(
			node.id
			for node in component_nodes
			if node.is_initial
		),
		key=_safe_node_id_sort_key,
	)

	root_starts = sorted(
		(
			node.id
			for node in component_nodes
			if node.id not in incoming_success
		),
		key=_safe_node_id_sort_key,
	)

	if initial_starts:
		start_id = initial_starts[0]
	elif root_starts:
		start_id = root_starts[0]
	else:
		start_id = min(
			node_ids,
			key=_safe_node_id_sort_key,
		)

	spine_ids: list[str] = []
	seen: set[str] = set()
	current_id: str | None = start_id

	while (
		current_id is not None
		and current_id in node_ids
		and current_id not in seen
	):
		seen.add(current_id)
		spine_ids.append(current_id)

		next_id = success_map.get(current_id)

		if next_id == current_id:
			break

		current_id = next_id

	return spine_ids


def _candidate_branch_lanes(
	preferred_lane: int,
) -> list[int]:
	"""
	Failure branches prefer lanes below the spine.
	Other branches prefer lanes above it.
	"""
	if preferred_lane == 0:
		preferred_lane = 1

	direction = 1 if preferred_lane > 0 else -1
	starting_distance = abs(preferred_lane)

	return [
		direction * distance
		for distance in range(
			starting_distance,
			starting_distance + 30,
		)
	]


def _layout_component(
	*,
	track_id: str,
	subtrack_index: int,
	component_nodes: list[DiagramNode],
	edges: list[DiagramEdge],
) -> DiagramComponentLayout:
	node_by_id = {
		node.id: node
		for node in component_nodes
	}
	node_ids = set(node_by_id)

	component_edges = [
		edge
		for edge in edges
		if edge.source in node_ids
		and edge.target in node_ids
	]

	success_map = _success_edges_for_nodes(
		node_ids=node_ids,
		edges=component_edges,
	)

	spine_ids = _primary_spine_ids(
		component_nodes=component_nodes,
		edges=component_edges,
	)
	spine_set = set(spine_ids)

	# Horizontal positions use half-column slots:
	# 0, 2, 4... are main-progression positions;
	# 1, 3, 5... are gaps available for branch challenges.
	positions: dict[str, tuple[int, int]] = {
		node_id: (column * 2, 0)
		for column, node_id in enumerate(spine_ids)
	}

	occupied = set(positions.values())
	unplaced = node_ids - spine_set

	def place_branch_chain(
		*,
		start_id: str,
		start_column: int,
		preferred_lane: int,
	) -> None:
		chain: list[str] = []
		current_id = start_id
		local_seen: set[str] = set()

		while (
			current_id in unplaced
			and current_id not in local_seen
		):
			local_seen.add(current_id)
			chain.append(current_id)

			next_id = success_map.get(current_id)

			if (
				next_id is None
				or next_id in spine_set
				or next_id not in unplaced
			):
				break

			current_id = next_id

		selected_lane = preferred_lane

		for candidate_lane in _candidate_branch_lanes(
			preferred_lane
		):
			required_positions = {
				(
					start_column + offset * 2,
					candidate_lane,
				)
				for offset in range(len(chain))
			}

			if required_positions.isdisjoint(occupied):
				selected_lane = candidate_lane
				break

		for offset, node_id in enumerate(chain):
			position = (
				start_column + offset * 2,
				selected_lane,
			)
			positions[node_id] = position
			occupied.add(position)
			unplaced.discard(node_id)

	while unplaced:
		candidate_edges = [
			edge
			for edge in component_edges
			if edge.source in positions
			and edge.target in unplaced
			and edge.source != edge.target
		]

		candidate_edges.sort(
			key=lambda edge: (
				positions[edge.source][0],
				0
				if _is_failure_transition(
					edge.transition_type
				)
				else 1,
				_safe_node_id_sort_key(edge.target),
			)
		)

		if candidate_edges:
			incoming_edge = candidate_edges[0]
			source_column, source_lane = positions[
				incoming_edge.source
			]

			if source_lane != 0:
				preferred_lane = source_lane
			elif _is_failure_transition(
				incoming_edge.transition_type
			):
				preferred_lane = 1
			else:
				preferred_lane = -1

			if (
					source_lane == 0
					and _is_failure_transition(
				incoming_edge.transition_type
			)
			):
				# Main-progression failure targets are placed in the gap
				# immediately before their source challenge.
				branch_start_column = max(
					0,
					source_column - 1,
				)
			else:
				# Branches originating from another branch continue forward.
				branch_start_column = (
						source_column + 1
				)

			place_branch_chain(
				start_id=incoming_edge.target,
				start_column=branch_start_column,
				preferred_lane=preferred_lane,
			)

			continue

		# A malformed progression can contain a non-initial challenge that has
		# outgoing transitions back into the visible progression but no incoming
		# transition from it. Such a node is structurally unreachable, but placing
		# it at column 0 makes the diagram harder to read. Keep it near the levels
		# it points to; reachability checking is responsible for reporting that it
		# cannot actually be reached.
		reverse_candidate_edges = [
			edge
			for edge in component_edges
			if edge.source in unplaced
			   and edge.target in positions
			   and edge.source != edge.target
		]

		if reverse_candidate_edges:
			reverse_sources = sorted(
				{edge.source for edge in reverse_candidate_edges},
				key=_safe_node_id_sort_key,
			)
			reverse_source = reverse_sources[0]

			outgoing_to_positioned = [
				edge
				for edge in reverse_candidate_edges
				if edge.source == reverse_source
			]

			target_columns = [
				positions[edge.target][0]
				for edge in outgoing_to_positioned
			]

			min_target_column = min(target_columns)
			max_target_column = max(target_columns)

			if min_target_column == max_target_column:
				branch_start_column = max(
					0,
					min_target_column - 1,
				)
			else:
				branch_start_column = (
											  min_target_column + max_target_column
									  ) // 2

			preferred_lane = (
				1
				if any(
					_is_failure_transition(edge.transition_type)
					for edge in outgoing_to_positioned
				)
				else -1
			)

			place_branch_chain(
				start_id=reverse_source,
				start_column=branch_start_column,
				preferred_lane=preferred_lane,
			)

			continue

		# Defensive fallback for a malformed or incompletely connected export.
		remaining_id = min(
			unplaced,
			key=_safe_node_id_sort_key,
		)

		place_branch_chain(
			start_id=remaining_id,
			start_column=0,
			preferred_lane=1,
		)

	placements = [
		(
			node_by_id[node_id],
			column,
			lane,
		)
		for node_id, (column, lane) in positions.items()
	]

	placements.sort(
		key=lambda item: (
			item[2],
			item[1],
			_safe_node_id_sort_key(item[0].id),
		)
	)

	lanes = [lane for _, _, lane in placements]
	columns = [column for _, column, _ in placements]

	return DiagramComponentLayout(
		track_id=track_id,
		subtrack_index=subtrack_index,
		placements=placements,
		spine_ids=spine_ids,
		min_lane=min(lanes, default=0),
		max_lane=max(lanes, default=0),
		max_column=max(columns, default=0),
	)


def _build_component_layouts(
	*,
	grouped: dict[str, list[DiagramNode]],
	edges: list[DiagramEdge],
) -> list[DiagramComponentLayout]:
	layouts: list[DiagramComponentLayout] = []

	for track_id, track_nodes in grouped.items():
		components = _split_track_into_components(
			track_nodes=track_nodes,
			edges=edges,
		)

		for component_index, component_nodes in enumerate(
			components,
			start=1,
		):
			layouts.append(
				_layout_component(
					track_id=track_id,
					subtrack_index=component_index,
					component_nodes=component_nodes,
					edges=edges,
				)
			)

	return layouts


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



def _svg_top_legend(
	width: int,
	*,
	show_other_transitions: bool,
) -> list[str]:
	legend_width = (
		850
		if show_other_transitions
		else 700
	)

	start_x = max(
		25,
		(width - legend_width) // 2,
	)
	y = 82

	parts = [
		# Direct progression
		f'<line x1="{start_x}" y1="{y}" '
		f'x2="{start_x + 38}" y2="{y}" '
		f'stroke="{_SUCCESS_EDGE_COLOR}" '
		f'stroke-width="2" marker-end="url(#arrow)"/>',
		_svg_text(
			x=start_x + 48,
			y=y + 4,
			text="Direct progression",
			size=10,
			anchor="start",
			fill="#555",
		),

		# Failure branch
		f'<line x1="{start_x + 160}" y1="{y}" '
		f'x2="{start_x + 198}" y2="{y}" '
		f'stroke="{_FAILURE_EDGE_COLOR}" '
		f'stroke-width="2" stroke-dasharray="5,4" '
		f'marker-end="url(#arrow)"/>',
		_svg_text(
			x=start_x + 208,
			y=y + 4,
			text="Failure transition",
			size=10,
			anchor="start",
			fill="#555",
		),

		# Alternative route, loop, or return
		f'<line x1="{start_x + 315}" y1="{y}" '
		f'x2="{start_x + 355}" y2="{y}" '
		f'stroke="{_LOOP_EDGE_COLOR}" '
		f'stroke-width="2" '
		f'marker-end="url(#arrow)"/>',
		_svg_text(
			x=start_x + 367,
			y=y + 4,
			text="Alternative success / loop / return",
			size=10,
			anchor="start",
			fill="#555",
		),

		# Initial challenge
		f'<rect x="{start_x + 580}" y="{y - 13}" '
		f'width="24" height="16" rx="3" ry="3" '
		f'fill="{_INITIAL_FILL_COLOR}" '
		f'stroke="{_INITIAL_BORDER_COLOR}" '
		f'stroke-width="2.2"/>',
		_svg_text(
			x=start_x + 614,
			y=y + 3,
			text="Configured initial challenge",
			size=10,
			anchor="start",
			fill="#555",
		),
	]

	if show_other_transitions:
		parts.extend(
			[
				f'<line x1="{start_x + 725}" y1="{y}" '
				f'x2="{start_x + 763}" y2="{y}" '
				f'stroke="{_OTHER_EDGE_COLOR}" '
				f'stroke-width="2" '
				f'marker-end="url(#arrow)"/>',
				_svg_text(
					x=start_x + 773,
					y=y + 4,
					text="Other transition",
					size=10,
					anchor="start",
					fill="#555",
				),
			]
		)

	return parts


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

	stroke_width = 2.2 if is_initial else 1.1
	stroke = (
		_INITIAL_BORDER_COLOR
		if is_initial
		else _BOX_COLOR
	)
	fill = (
		_INITIAL_FILL_COLOR
		if is_initial
		else "#ffffff"
	)

	text_lines = [
		f'<rect x="{x}" y="{y}" width="{width}" height="{height}" '
		f'rx="6" ry="6" fill="{fill}" stroke="{stroke}" '
		f'stroke-width="{stroke_width}"/>',
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
		f'fill="none" stroke="{_SUCCESS_EDGE_COLOR}" stroke-width="1.5" '
		f'marker-end="url(#arrow)"/>'
	)


def _svg_secondary_edge(
	*,
	edge: DiagramEdge,
	source_center: tuple[int, int],
	target_center: tuple[int, int],
	show_labels: bool,
	node_half_width: int,
	node_half_height: int,
	source_lane: int,
	target_lane: int,
	is_return: bool = False,
	edge_index: int = 0,
) -> str:
	x1, y1 = source_center
	x2, y2 = target_center

	is_failure = _is_failure_transition(
		edge.transition_type
	)
	is_loop = x1 == x2 and y1 == y2

	source_is_secondary = source_lane != 0
	target_is_secondary = target_lane != 0

	if is_failure:
		color = _FAILURE_EDGE_COLOR
	elif is_loop or is_return:
		color = _LOOP_EDGE_COLOR
	elif _is_success_like_transition(
		edge.transition_type
	):
		color = _SUCCESS_EDGE_COLOR
	else:
		color = _OTHER_EDGE_COLOR

	stroke_dash = (
		'stroke-dasharray="5,4"'
		if is_failure
		else ""
	)

	# Self-loops remain curved because their geometry must return to
	# the same challenge.
	if is_loop:
		direction = 1 if is_failure else -1
		lane_offset = (
			24 + (edge_index % 3) * 10
		)

		box_edge_y = (
			y1
			+ direction * node_half_height
		)
		loop_y = (
			box_edge_y
			+ direction * lane_offset
		)
		loop_left_x = (
			x1 - node_half_width // 2
		)
		loop_right_x = (
			x1 + node_half_width // 2
		)

		path = (
			f"M {loop_left_x} {box_edge_y} "
			f"C {loop_left_x} {loop_y}, "
			f"{loop_right_x} {loop_y}, "
			f"{loop_right_x} {box_edge_y}"
		)

		return (
			f'<path d="{path}" fill="none" '
			f'stroke="{color}" stroke-width="1.4" '
			f'marker-end="url(#arrow)" '
			f'{stroke_dash}/>'
		)

	quarter_width = node_half_width // 2

	# Failure from the main progression into a secondary challenge:
	# main lower-left -> secondary upper-right.
	if (
		is_failure
		and not source_is_secondary
		and target_is_secondary
	):
		source_x = x1 - quarter_width
		source_y = y1 + node_half_height + 3

		target_x = x2 + quarter_width
		target_y = y2 - node_half_height - 3

		path = (
			f"M {source_x} {source_y} "
			f"L {target_x} {target_y}"
		)

	# Failure from a secondary challenge back to the main progression:
	# secondary upper-left -> main lower-right.
	elif (
		is_failure
		and source_is_secondary
		and not target_is_secondary
	):
		source_x = x1 - quarter_width
		source_y = y1 - node_half_height - 3

		target_x = x2 + quarter_width
		target_y = y2 + node_half_height + 3

		path = (
			f"M {source_x} {source_y} "
			f"L {target_x} {target_y}"
		)

	# Alternative success from a secondary challenge:
	# secondary right-centre -> main lower-centre.
	elif (
		not is_failure
		and source_is_secondary
		and not target_is_secondary
	):
		source_x = x1 + node_half_width + 3
		source_y = y1

		target_x = x2
		target_y = y2 + node_half_height + 3

		path = (
			f"M {source_x} {source_y} "
			f"L {target_x} {target_y}"
		)

	# Transition between two secondary challenges:
	# use their nearest horizontal sides.
	elif (
		source_is_secondary
		and target_is_secondary
	):
		if x2 >= x1:
			source_x = x1 + node_half_width + 3
			source_y = y1
			target_x = x2 - node_half_width - 3
			target_y = y2
		else:
			source_x = x1 - node_half_width - 3
			source_y = y1
			target_x = x2 + node_half_width + 3
			target_y = y2

		path = (
			f"M {source_x} {source_y} "
			f"L {target_x} {target_y}"
		)

	# Alternative transition from the main progression to a secondary
	# challenge. This is unusual, but keep it direct.
	elif (
			not source_is_secondary
			and target_is_secondary
	):
		source_x = x1
		source_y = y1 + node_half_height + 3

		target_x = x2
		target_y = y2 - node_half_height - 3

		path = (
			f"M {source_x} {source_y} "
			f"L {target_x} {target_y}"
		)

	# Rounded return between main-progression challenges.
	elif x2 < x1:
		source_x = x1 - quarter_width
		source_y = y1 + node_half_height + 3

		target_x = x2 + quarter_width
		target_y = y2 + node_half_height + 3

		curve_y = (
				max(source_y, target_y)
				+ 28
				+ (edge_index % 3) * 12
		)

		path = (
			f"M {source_x} {source_y} "
			f"C {source_x} {curve_y}, "
			f"{target_x} {curve_y}, "
			f"{target_x} {target_y}"
		)

	# Defensive fallback for forward main-to-main transitions.
	else:
		source_x = x1 + node_half_width + 3
		source_y = y1

		target_x = x2 - node_half_width - 3
		target_y = y2

		path = (
			f"M {source_x} {source_y} "
			f"L {target_x} {target_y}"
		)

	parts = [
		(
			f'<path d="{path}" fill="none" '
			f'stroke="{color}" stroke-width="1.4" '
			f'marker-end="url(#arrow)" '
			f'{stroke_dash}/>'
		)
	]

	if (
		show_labels
		and _is_other_transition(edge)
	):
		parts.append(
			_svg_text(
				x=(source_x + target_x) // 2,
				y=(source_y + target_y) // 2 - 6,
				text=edge.transition_type,
				size=9,
				fill=color,
			)
		)

	return "\n".join(parts)





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
	Build a dependency-free SVG campaign-flow diagram.

	Layout:
	- each visualization can contain one or more connected progressions;
	- the direct success progression forms a horizontal spine;
	- failure-only and alternative challenges are placed in branch lanes;
	- direct progression, failure branches, and non-linear routes use
	  distinct visual styles.
	"""
	snapshot = _as_dict(snapshot)
	nodes = _extract_nodes(snapshot)

	if not nodes:
		return _empty_svg(
			"No challenge data available for a flow diagram."
		)

	truncated = False

	if len(nodes) > max_nodes:
		nodes = nodes[:max_nodes]
		truncated = True

	visible_node_ids = {
		node.id
		for node in nodes
	}

	edges = _extract_edges(
		snapshot,
		visible_node_ids,
	)
	grouped = _group_nodes_by_track(nodes)
	track_labels = _visualization_labels(snapshot)

	component_layouts = _build_component_layouts(
		grouped=grouped,
		edges=edges,
	)

	if not component_layouts:
		return _empty_svg(
			"No challenge progression could be constructed."
		)

	box_width = 126
	box_height = 50
	node_gap_x = 30
	lane_gap_y = 34
	component_gap_y = 60

	margin_x = 165
	margin_y = 180
	right_margin = 60
	bottom_margin = 30

	# One slot represents half the distance between two main challenges.
	slot_pitch = (
						 box_width + node_gap_x
				 ) // 2

	lane_pitch = box_height + lane_gap_y

	max_slot = max(
		layout.max_column
		for layout in component_layouts
	)

	width = max(
		900,
		(
				margin_x
				+ max_slot * slot_pitch
				+ box_width
				+ right_margin
		),
	)

	layout_origins: list[
		tuple[DiagramComponentLayout, int]
	] = []

	cursor_y = margin_y

	for layout in component_layouts:
		spine_y = (
			cursor_y
			+ (-layout.min_lane) * lane_pitch
		)

		layout_origins.append(
			(layout, spine_y)
		)

		component_height = (
			(layout.max_lane - layout.min_lane)
			* lane_pitch
			+ box_height
		)

		cursor_y += (
			component_height
			+ component_gap_y
		)

	height = (
		cursor_y
		- component_gap_y
		+ bottom_margin
	)

	title = _text(
		snapshot.get("campaign_name"),
		default="Campaign flow diagram",
	)
	file_name = _text(
		snapshot.get("file_name")
	)

	has_other_transitions = any(
		_is_other_transition(edge)
		for edge in edges
	)

	parts: list[str] = [
		(
			f'<svg xmlns="http://www.w3.org/2000/svg" '
			f'width="{width}" height="{height}" '
			f'viewBox="0 0 {width} {height}">'
		),
		"""
<defs>
  <marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3"
		  orient="auto" markerUnits="strokeWidth">
	<path d="M0,0 L0,6 L9,3 z" fill="context-stroke" />
  </marker>
</defs>
""",
		(
			f'<rect x="0" y="0" '
			f'width="{width}" height="{height}" '
			f'fill="#fafafa"/>'
		),
		_svg_text(
			x=width // 2,
			y=30,
			text=title,
			size=18,
			weight="bold",
		),
	]

	if file_name:
		parts.append(
			_svg_text(
				x=width // 2,
				y=52,
				text=file_name,
				size=11,
				fill="#555",
			)
		)

	parts.extend(
		_svg_top_legend(
			width,
			show_other_transitions=(
				has_other_transitions
			),
		)
	)

	if truncated:
		parts.append(
			_svg_text(
				x=width // 2,
				y=142,
				text=(
					"Diagram truncated to the first "
					f"{max_nodes} challenges."
				),
				size=10,
				fill="#555",
			)
		)

	node_centers: dict[
		str,
		tuple[int, int],
	] = {}

	node_grid_positions: dict[
		str,
		tuple[int, int],
	] = {}

	node_boxes: list[str] = []
	edge_parts: list[str] = []

	previous_track_id: str | None = None

	for layout, spine_y in layout_origins:
		track_id = layout.track_id

		track_label = track_labels.get(
			track_id,
			f"Visualization {track_id}",
		)

		if track_id != previous_track_id:
			label_lines = _wrap_text_lines(
				track_label,
				line_chars=24,
				max_lines=3,
			)

			parts.append(
				_svg_multiline_text(
					x=margin_x - 22,
					y_center=(
						spine_y
						+ box_height // 2
					),
					lines=label_lines,
					size=10,
					weight="bold",
					anchor="end",
				)
			)
		else:
			parts.append(
				_svg_text(
					x=margin_x - 22,
					y=(
						spine_y
						+ box_height // 2
						+ 4
					),
					text=(
						"↳ track "
						f"{layout.subtrack_index}"
					),
					size=10,
					anchor="end",
				)
			)

		previous_track_id = track_id

		# The guide line represents only the direct progression.
		parts.append(
			f'<line x1="{margin_x - 8}" '
			f'y1="{spine_y + box_height // 2}" '
			f'x2="{width - right_margin}" '
			f'y2="{spine_y + box_height // 2}" '
			f'stroke="#e6e6e6" stroke-width="1"/>'
		)

		for node, column, lane in layout.placements:
			x = (
					margin_x
					+ column * slot_pitch
			)
			y = (
				spine_y
				+ lane * lane_pitch
			)

			subtitle_parts: list[str] = []

			if node.task_count is not None:
				subtitle_parts.append(
					f"{node.task_count} task(s)"
				)

			if node.target_points not in (
				None,
				"",
			):
				subtitle_parts.append(
					f"target: {node.target_points}"
				)

			subtitle = (
				" · ".join(subtitle_parts)
				or f"ID: {node.id}"
			)

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

			node_grid_positions[node.id] = (
				column,
				lane,
			)

	node_half_width = box_width // 2

	adjacent_spine_pairs: set[
		tuple[str, str]
	] = set()

	for layout in component_layouts:
		adjacent_spine_pairs.update(
			zip(
				layout.spine_ids,
				layout.spine_ids[1:],
			)
		)

	main_edge_keys: set[
		tuple[str, str]
	] = set()

	# Draw adjacent success transitions on the straight spine.
	for edge in edges:
		edge_key = (
			edge.source,
			edge.target,
		)

		if (
				edge_key not in adjacent_spine_pairs
				or not _is_success_like_transition(
			edge.transition_type
		)
				or _is_failure_transition(
			edge.transition_type
		)
		):
			continue

		source_center = node_centers.get(
			edge.source
		)
		target_center = node_centers.get(
			edge.target
		)

		if (
				source_center is None
				or target_center is None
		):
			continue

		main_edge_keys.add(edge_key)

		edge_parts.append(
			_svg_main_edge(
				source_center=source_center,
				target_center=target_center,
				node_half_width=node_half_width,
			)
		)

	# Draw branches, loops, returns, and unusual transitions.
	for edge_index, edge in enumerate(edges):
		edge_key = (
			edge.source,
			edge.target,
		)

		# Direct spine progressions were already rendered in orange.
		if (
				edge_key in main_edge_keys
				and _is_success_like_transition(
			edge.transition_type
		)
				and not _is_failure_transition(
			edge.transition_type
		)
		):
			continue

		source_center = node_centers.get(
			edge.source
		)
		target_center = node_centers.get(
			edge.target
		)
		source_grid = node_grid_positions.get(
			edge.source
		)
		target_grid = node_grid_positions.get(
			edge.target
		)

		if (
				source_center is None
				or target_center is None
				or source_grid is None
				or target_grid is None
		):
			continue

		source_column, source_lane = (
			source_grid
		)
		target_column, target_lane = (
			target_grid
		)

		is_failure = _is_failure_transition(
			edge.transition_type
		)
		is_success_like = (
			_is_success_like_transition(
				edge.transition_type
			)
		)

		is_return = (
				edge.source == edge.target
				or (
						source_lane != 0
						and target_lane == 0
				)
				or target_column <= source_column
				or (
						is_success_like
						and not is_failure
				)
		)

		edge_parts.append(
			_svg_secondary_edge(
				edge=edge,
				source_center=source_center,
				target_center=target_center,
				show_labels=show_edge_labels,
				node_half_width=node_half_width,
				node_half_height=(
						box_height // 2
				),
				source_lane=source_lane,
				target_lane=target_lane,
				is_return=is_return,
				edge_index=edge_index,
			)
		)



	# Edges are added before boxes so that lines do not cover node contents.
	parts.extend(edge_parts)
	parts.extend(node_boxes)

	parts.append("</svg>")
	return "\n".join(parts)