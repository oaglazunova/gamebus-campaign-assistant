from __future__ import annotations


def format_tristate(value) -> str:
    if value is True:
        return "Yes"
    if value is False:
        return "No"
    return "Unknown"