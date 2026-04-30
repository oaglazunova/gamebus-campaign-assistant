from __future__ import annotations

import pandas as pd

from campaign_assistant.checker.native_spellchecker import run_native_spellchecker_tables


class FakeSpellTool:
    def __init__(self, behavior: dict[str, str]):
        self.behavior = behavior

    def check(self, text):
        return self.behavior.get(text, [])

    def correct(self, text):
        return f"CORRECTED:{text}"


def _tables_for_spellchecker(
    *,
    tasks: list[dict],
    challenges: list[dict],
    visualizations: list[dict] | None = None,
    waves: list[dict] | None = None,
):
    if visualizations is None:
        visualizations = [
            {"campaign": 1, "id": 100, "description": "V1", "wave": 10},
        ]

    if waves is None:
        waves = [
            {
                "id": 10,
                "name": "Wave 1",
                "start": pd.Timestamp("2025-01-01"),
                "end": pd.Timestamp("2027-01-01"),
            }
        ]

    return {
        "tasks": pd.DataFrame(tasks),
        "challenges": pd.DataFrame(challenges),
        "visualizations": pd.DataFrame(visualizations),
        "waves": pd.DataFrame(waves),
    }


def test_native_spellchecker_passes_when_names_are_ok(monkeypatch):
    tables = _tables_for_spellchecker(
        tasks=[
            {"name": "Drink Water", "challenge": 1},
        ],
        challenges=[
            {"id": 1, "name": "Challenge 1", "visualizations": 100},
        ],
    )

    monkeypatch.setattr(
        "campaign_assistant.checker.native_spellchecker.classify_matches",
        lambda matches: "OK",
    )
    monkeypatch.setattr(
        "campaign_assistant.checker.native_spellchecker.TextStatus",
        type("TextStatus", (), {"FAULTY": "FAULTY", "GARBAGE": "GARBAGE"}),
    )

    result = run_native_spellchecker_tables(tables, tool=FakeSpellTool({}))

    assert result["status"] == "Passed"
    assert result["issues"] == []


def test_native_spellchecker_reports_faulty_task_name(monkeypatch):
    tables = _tables_for_spellchecker(
        tasks=[
            {"name": "Wrng Wrd", "challenge": 1},
        ],
        challenges=[
            {"id": 1, "name": "Challenge 1", "visualizations": 100},
        ],
    )

    monkeypatch.setattr(
        "campaign_assistant.checker.native_spellchecker.classify_matches",
        lambda matches: "FAULTY",
    )
    monkeypatch.setattr(
        "campaign_assistant.checker.native_spellchecker.TextStatus",
        type("TextStatus", (), {"FAULTY": "FAULTY", "GARBAGE": "GARBAGE"}),
    )

    result = run_native_spellchecker_tables(
        tables,
        tool=FakeSpellTool({"Wrng Wrd": ["dummy-match"]}),
    )

    assert result["status"] == "Failed"
    assert len(result["issues"]) == 2
    assert "Name of task is faulty 'Wrng Wrd'" in result["issues"][1].message or "Name of task is faulty 'Wrng Wrd'" in result["issues"][0].message


def test_native_spellchecker_reports_garbage_challenge_name(monkeypatch):
    tables = _tables_for_spellchecker(
        tasks=[
            {"name": "Drink Water", "challenge": 1},
        ],
        challenges=[
            {"id": 1, "name": "xxyyzz", "visualizations": 100},
        ],
    )

    def fake_classify(matches):
        if matches == ["garbage"]:
            return "GARBAGE"
        return "OK"

    monkeypatch.setattr(
        "campaign_assistant.checker.native_spellchecker.classify_matches",
        fake_classify,
    )
    monkeypatch.setattr(
        "campaign_assistant.checker.native_spellchecker.TextStatus",
        type("TextStatus", (), {"FAULTY": "FAULTY", "GARBAGE": "GARBAGE"}),
    )

    result = run_native_spellchecker_tables(
        tables,
        tool=FakeSpellTool({"xxyyzz": ["garbage"]}),
    )

    assert result["status"] == "Failed"
    assert len(result["issues"]) == 1
    assert "Name of challenge is garbage 'xxyyzz'" in result["issues"][0].message


def test_native_spellchecker_reports_faulty_task_name(monkeypatch):
    tables = _tables_for_spellchecker(
        tasks=[
            {"name": "Wrng Wrd", "challenge": 1},
        ],
        challenges=[
            {"id": 1, "name": "Challenge 1", "visualizations": 100},
        ],
    )

    def fake_classify(matches):
        if matches == ["faulty"]:
            return "FAULTY"
        return "OK"

    monkeypatch.setattr(
        "campaign_assistant.checker.native_spellchecker.classify_matches",
        fake_classify,
    )
    monkeypatch.setattr(
        "campaign_assistant.checker.native_spellchecker.TextStatus",
        type("TextStatus", (), {"FAULTY": "FAULTY", "GARBAGE": "GARBAGE"}),
    )

    result = run_native_spellchecker_tables(
        tables,
        tool=FakeSpellTool({"Wrng Wrd": ["faulty"]}),
    )

    assert result["status"] == "Failed"
    assert len(result["issues"]) == 1
    assert "Name of task is faulty 'Wrng Wrd'" in result["issues"][0].message
    assert "CORRECTED:Wrng Wrd" in result["issues"][0].message