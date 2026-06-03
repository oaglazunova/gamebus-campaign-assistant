from __future__ import annotations

from pathlib import Path


_THEORY_FILES = [
    "bct_summary.md",
    "com_b_summary.md",
    "ttm_summary.md",
]


def load_theory_knowledge_pack() -> str:
    base_dir = Path(__file__).parent
    sections: list[str] = []

    for file_name in _THEORY_FILES:
        path = base_dir / file_name
        if not path.exists():
            continue

        text = path.read_text(encoding="utf-8").strip()
        if text:
            sections.append(text)

    return "\n\n---\n\n".join(sections)
