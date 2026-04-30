from __future__ import annotations

from typing import Any


def get_capability_summary(context) -> dict[str, Any]:
    return context.shared.get("capability_summary", {}) or {}


def get_capabilities(context) -> dict[str, Any]:
    summary = get_capability_summary(context)
    return summary.get("capabilities", {}) or {}


def get_active_modules(context) -> dict[str, Any]:
    summary = get_capability_summary(context)
    return summary.get("active_modules", {}) or {}


def capability_is_true(context, name: str) -> bool:
    return get_capabilities(context).get(name) is True


def capability_is_false(context, name: str) -> bool:
    return get_capabilities(context).get(name) is False


def module_is_enabled(context, name: str, default: bool = True) -> bool:
    modules = get_active_modules(context)
    value = modules.get(name)
    if value is None:
        return default
    return bool(value)