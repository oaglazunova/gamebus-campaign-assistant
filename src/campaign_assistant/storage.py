from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

import keyring

from campaign_assistant.config import APP_NAME, APP_ID

SERVICE_NAME = APP_NAME

LOCAL_APPDATA = Path(os.environ.get("LOCALAPPDATA", Path.home()))
APP_DIR = LOCAL_APPDATA / APP_ID
SETTINGS_FILE = APP_DIR / "settings.json"
COOKIE_FILE = APP_DIR / "session_cookies.json"

DEFAULT_SETTINGS: Dict[str, Any] = {
    "email": "",
    "remember_credentials": True,
    "last_campaign_abbreviation": "",
    "last_source_mode": "Download from GameBus",
    "saved_campaign_abbreviations": [],
}


def ensure_app_dirs() -> None:
    """Ensure that the local app data directory exists."""
    APP_DIR.mkdir(parents=True, exist_ok=True)


def _normalize_abbreviation(value: str) -> str:
    """Normalize campaign abbreviations before storing them."""
    return value.strip()


def _merge_defaults(data: Dict[str, Any]) -> Dict[str, Any]:
    """Merge persisted settings with defaults and sanitize basic fields."""
    merged = DEFAULT_SETTINGS.copy()
    merged.update(data or {})

    if not isinstance(merged.get("saved_campaign_abbreviations"), list):
        merged["saved_campaign_abbreviations"] = []

    merged["saved_campaign_abbreviations"] = sorted(
        {
            _normalize_abbreviation(v)
            for v in merged["saved_campaign_abbreviations"]
            if isinstance(v, str) and _normalize_abbreviation(v)
        }
    )

    if not isinstance(merged.get("email"), str):
        merged["email"] = ""

    if not isinstance(merged.get("last_campaign_abbreviation"), str):
        merged["last_campaign_abbreviation"] = ""

    if not isinstance(merged.get("last_source_mode"), str):
        merged["last_source_mode"] = DEFAULT_SETTINGS["last_source_mode"]

    if not isinstance(merged.get("remember_credentials"), bool):
        merged["remember_credentials"] = DEFAULT_SETTINGS["remember_credentials"]

    return merged


def load_settings() -> Dict[str, Any]:
    """
    Load user-local settings from disk.
    If the settings file does not exist or is invalid, recreate it from defaults.
    """
    ensure_app_dirs()

    if not SETTINGS_FILE.exists():
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()

    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        return _merge_defaults(data)
    except Exception:
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()


def save_settings(settings: Dict[str, Any]) -> None:
    """Persist user-local settings to disk."""
    ensure_app_dirs()
    merged = _merge_defaults(settings)
    SETTINGS_FILE.write_text(
        json.dumps(merged, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def add_saved_campaign_abbreviation(abbreviation: str) -> None:
    """Add a campaign abbreviation to the saved list if it is not already present."""
    abbreviation = _normalize_abbreviation(abbreviation)
    if not abbreviation:
        return

    settings = load_settings()
    abbreviations = settings.get("saved_campaign_abbreviations", [])

    if abbreviation not in abbreviations:
        abbreviations.append(abbreviation)
        settings["saved_campaign_abbreviations"] = sorted(set(abbreviations))
        save_settings(settings)


def save_password(email: str, password: str) -> None:
    """Save the user's password securely in the OS keyring."""
    email = email.strip()
    if email and password:
        keyring.set_password(SERVICE_NAME, email, password)


def load_password(email: str) -> Optional[str]:
    """Load a saved password from the OS keyring."""
    email = email.strip()
    if not email:
        return None
    return keyring.get_password(SERVICE_NAME, email)


def delete_password(email: str) -> None:
    """Delete a saved password from the OS keyring if it exists."""
    email = email.strip()
    if not email:
        return
    try:
        keyring.delete_password(SERVICE_NAME, email)
    except Exception:
        pass


def get_cookie_file() -> Path:
    """Return the path of the local cookie/session file."""
    ensure_app_dirs()
    return COOKIE_FILE


def delete_cookie_file() -> None:
    """Delete the local cookie/session file if it exists."""
    try:
        get_cookie_file().unlink(missing_ok=True)
    except Exception:
        pass