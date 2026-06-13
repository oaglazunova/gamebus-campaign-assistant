from __future__ import annotations

from collections.abc import Mapping
from enum import Enum
from pathlib import Path
from typing import Any

import pandas as pd


WorkbookTables = Mapping[str, pd.DataFrame]


class VisualizationFlowKind(str, Enum):
    """Structural flow kind inferred for a visualization."""

    PROGRESSION = "progression"
    CYCLIC_SUPPORT = "cyclic_support"
    NON_PROGRESSION = "non_progression"


def _get_now_timestamp() -> pd.Timestamp:
    """Return a timezone-naive timestamp for comparing with Excel dates."""
    return pd.Timestamp.now().tz_localize(None)


def _normalise_table_name(name: Any) -> str:
    return str(name).strip().lower().replace(" ", "_")


def load_workbook_tables(file_path: str | Path) -> dict[str, pd.DataFrame]:
    """
    Load all sheets from a GameBus campaign export once.

    The native checkers expect lowercase sheet keys such as ``tasks`` and
    ``challenges``. Normalising names here keeps the wrapper independent from
    exact Excel sheet capitalisation while avoiding the old legacy checker
    dependency.
    """
    raw_tables = pd.read_excel(file_path, sheet_name=None)
    return {_normalise_table_name(name): df for name, df in raw_tables.items()}


def _get_table(tables: WorkbookTables, name: str) -> pd.DataFrame:
    key = _normalise_table_name(name)
    if key in tables:
        return tables[key]

    for table_name, df in tables.items():
        if _normalise_table_name(table_name) == key:
            return df

    raise KeyError(f"Required sheet '{name}' is missing from the campaign export.")


def _coerce_timestamp(value: Any) -> pd.Timestamp | None:
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass

    try:
        return pd.Timestamp(value).tz_localize(None)
    except Exception:
        return None


def _clean_scalar(value: Any) -> Any:
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass

    if isinstance(value, pd.Timestamp):
        return value.isoformat()

    return value


def _normalise_id(value: Any) -> str | None:
    value = _clean_scalar(value)
    if value is None:
        return None

    if isinstance(value, float) and value.is_integer():
        value = int(value)

    text = str(value).strip()
    if not text:
        return None

    try:
        number = float(text)
    except Exception:
        return text

    if number.is_integer():
        return str(int(number))

    return text


def _same_id(left: Any, right: Any) -> bool:
    left_id = _normalise_id(left)
    right_id = _normalise_id(right)
    return left_id is not None and left_id == right_id


def _reference_ids(value: Any) -> list[str]:
    value = _clean_scalar(value)
    if value is None:
        return []

    ids: list[str] = []
    for part in str(value).split(","):
        normalized = _normalise_id(part)
        if normalized is not None:
            ids.append(normalized)
    return ids


def _field_contains_id(value: Any, target_id: Any) -> bool:
    target = _normalise_id(target_id)
    return target is not None and target in set(_reference_ids(value))


def _first_reference_id(value: Any) -> str | None:
    ids = _reference_ids(value)
    return ids[0] if ids else None


def _challenge_belongs_to_visualization(challenge: Mapping[str, Any], visualization_id: Any) -> bool:
    return _field_contains_id(challenge.get("visualizations"), visualization_id)


def _challenge_visualizations(challenge: Mapping[str, Any]) -> list[str]:
    return _reference_ids(challenge.get("visualizations"))


def _challenges_for_visualization(
    challenges: Mapping[str, dict[str, Any]],
    visualization_id: Any,
) -> list[dict[str, Any]]:
    return [
        challenge
        for challenge in challenges.values()
        if _challenge_belongs_to_visualization(challenge, visualization_id)
    ]


def _coverage_note(
    *,
    check_name: str,
    memberships: int,
    challenge_count: int,
    visualization_count: int,
) -> str | None:
    if memberships > 0 or challenge_count == 0 or visualization_count == 0:
        return None

    return (
        f"{check_name} evaluated 0 challenge-visualization memberships, but the export contains "
        f"{challenge_count} challenge(s) and {visualization_count} visualization(s). "
        "This usually means reference ids were not parsed correctly, so the check result is not reliable."
    )


def _active_wave_ids(waves_df: pd.DataFrame | None, now: pd.Timestamp | None = None) -> set[str]:
    if waves_df is None or waves_df.empty:
        return set()

    now = now if now is not None else _get_now_timestamp()
    now = pd.Timestamp(now)
    if now.tzinfo is not None:
        now = now.tz_convert(None)

    active: set[str] = set()

    for _, row in waves_df.iterrows():
        start = _coerce_timestamp(row.get("start"))
        end = _coerce_timestamp(row.get("end"))
        wave_id = _normalise_id(row.get("id"))

        if wave_id is not None and start is not None and end is not None and start <= now <= end:
            active.add(wave_id)

    return active


def _challenge_index(challenges_df: pd.DataFrame) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}

    for _, row in challenges_df.iterrows():
        record = row.to_dict()
        challenge_id = _normalise_id(record.get("id"))

        if challenge_id is not None:
            index[challenge_id] = record

    return index


def _visualization_index(visualizations_df: pd.DataFrame) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}

    for _, row in visualizations_df.iterrows():
        record = row.to_dict()
        visualization_id = _normalise_id(record.get("id"))

        if visualization_id is not None:
            index[visualization_id] = record

    return index


def _challenge_url(visualization: Mapping[str, Any], challenge: Mapping[str, Any]) -> str:
    visualization_id = (
        _normalise_id(visualization.get("id"))
        or _first_reference_id(challenge.get("visualizations"))
        or ""
    )

    return (
        "https://campaigns.healthyw8.gamebus.eu/editor/for/"
        f"{visualization.get('campaign')}/{visualization_id}/challenges/{challenge.get('id')}"
    )


def _is_initial(challenge: Mapping[str, Any]) -> bool:
    return _clean_scalar(challenge.get("is_initial_level")) in {1, "1", True}


def _is_terminal(
    challenge: Mapping[str, Any],
    challenges: Mapping[str, dict[str, Any]] | None = None,
) -> bool:
    """
    Return whether a challenge is terminal.

    A terminal challenge is represented by ``success_next`` pointing to itself.
    ``challenges`` is optional for compatibility with callers that already have
    the current challenge row and do not need to resolve the successor record.
    """
    challenge_id = challenge.get("id")
    success_next = challenge.get("success_next")

    if _same_id(success_next, challenge_id):
        return True

    if challenges is None:
        return False

    next_challenge = challenges.get(_normalise_id(success_next) or "")
    return next_challenge is not None and _same_id(next_challenge.get("id"), challenge_id)


_SUPPORT_HINTS = {
    # English
    "tip",
    "tips",
    "support",
    "info",
    "information",
    "help",
    "advice",
    "recommendation",
    "recommendations",
    "faq",
    # Dutch
    "informatie",
    "ondersteuning",
    "hulp",
    "advies",
    "adviezen",
    "uitleg",
    # German
    "tipp",
    "tipps",
    "hilfe",
    "hinweis",
    "hinweise",
    "unterstützung",
    "unterstuetzung",
    "informationen",
    "ratgeber",
    # Portuguese
    "dica",
    "dicas",
    "informação",
    "informações",
    "informacao",
    "informacoes",
    "apoio",
    "suporte",
    "ajuda",
    "conselho",
    "conselhos",
}

_PROGRESS_HINTS = {
    # English
    "level",
    "levels",
    "challenge",
    "challenges",
    "progression",
    "progress",
    # Dutch
    "niveau",
    "niveaus",
    "uitdaging",
    "uitdagingen",
    "voortgang",
    "progressie",
    # German
    "stufe",
    "stufen",
    "herausforderung",
    "herausforderungen",
    "fortschritt",
    # Portuguese
    "nível",
    "níveis",
    "nivel",
    "niveis",
    "desafio",
    "desafios",
    "progressão",
    "progressao",
    "progresso",
}


def _visualization_text(visualization: Mapping[str, Any]) -> str:
    values = [
        visualization.get("description"),
        visualization.get("label"),
        visualization.get("visualization"),
        visualization.get("settings"),
    ]
    return " ".join(str(_clean_scalar(value) or "") for value in values).lower()


def _contains_any_word(text: str, words: set[str]) -> bool:
    normalized = text.replace("_", " ").replace("-", " ")
    tokens = set(normalized.split())
    return any(word in tokens or word in normalized for word in words)


def _success_next(
    challenge: Mapping[str, Any] | None,
    challenges: Mapping[str, dict[str, Any]],
) -> dict[str, Any] | None:
    if challenge is None:
        return None

    return challenges.get(_normalise_id(challenge.get("success_next")) or "")


def _has_success_cycle(
    challenges_for_vis: list[dict[str, Any]],
    challenges: Mapping[str, dict[str, Any]],
) -> bool:
    local_ids = {_normalise_id(challenge.get("id")) for challenge in challenges_for_vis}
    local_ids.discard(None)

    for challenge in challenges_for_vis:
        seen: set[str] = set()
        current: dict[str, Any] | None = challenge

        while current is not None:
            current_id = _normalise_id(current.get("id"))

            if current_id is None or current_id not in local_ids:
                break

            if current_id in seen:
                return True

            seen.add(current_id)
            current = _success_next(current, challenges)

    return False


def _classify_visualization_flow(
    visualization: Mapping[str, Any],
    challenges_for_vis: list[dict[str, Any]],
    challenges: Mapping[str, dict[str, Any]],
) -> VisualizationFlowKind:
    """
    Infer whether a visualization should be treated as a progression.

    Progression-like visualizations are expected to have initial and terminal
    levels. Support/cyclic visualizations, such as tips/info/support views in
    English, Dutch, German, or Portuguese, may intentionally loop and should not
    fail reachability only because they lack a terminal level.
    """
    if not challenges_for_vis:
        return VisualizationFlowKind.NON_PROGRESSION

    initials = [challenge for challenge in challenges_for_vis if _is_initial(challenge)]
    terminals = [challenge for challenge in challenges_for_vis if _is_terminal(challenge, challenges)]

    text = _visualization_text(visualization)
    has_support_hint = _contains_any_word(text, _SUPPORT_HINTS)
    has_progression_hint = _contains_any_word(text, _PROGRESS_HINTS)

    if initials and terminals:
        return VisualizationFlowKind.PROGRESSION

    if has_support_hint and not terminals and _has_success_cycle(challenges_for_vis, challenges):
        return VisualizationFlowKind.CYCLIC_SUPPORT

    if not initials and not terminals and not has_progression_hint:
        return VisualizationFlowKind.NON_PROGRESSION

    return VisualizationFlowKind.PROGRESSION
