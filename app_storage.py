from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, List

import keyring

APP_ID = "GameBusCampaignAssistant"
SERVICE_NAME = "GameBus Campaign Assistant"

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
    APP_DIR.mkdir(parents=True, exist_ok=True)


def _merge_defaults(data: Dict[str, Any]) -> Dict[str, Any]:
    merged = DEFAULT_SETTINGS.copy()
    merged.update(data or {})

    if not isinstance(merged.get("saved_campaign_abbreviations"), list):
        merged["saved_campaign_abbreviations"] = []

    return merged


def load_settings() -> Dict[str, Any]:
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
    ensure_app_dirs()
    merged = _merge_defaults(settings)
    SETTINGS_FILE.write_text(
        json.dumps(merged, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def add_saved_campaign_abbreviation(abbreviation: str) -> None:
    abbreviation = abbreviation.strip()
    if not abbreviation:
        return

    settings = load_settings()
    abbreviations = settings.get("saved_campaign_abbreviations", [])

    if abbreviation not in abbreviations:
        abbreviations.append(abbreviation)
        abbreviations.sort()
        settings["saved_campaign_abbreviations"] = abbreviations
        save_settings(settings)


def save_password(email: str, password: str) -> None:
    if email.strip() and password:
        keyring.set_password(SERVICE_NAME, email.strip(), password)


def load_password(email: str) -> Optional[str]:
    if not email.strip():
        return None
    return keyring.get_password(SERVICE_NAME, email.strip())


def delete_password(email: str) -> None:
    if not email.strip():
        return
    try:
        keyring.delete_password(SERVICE_NAME, email.strip())
    except Exception:
        pass


def get_cookie_file() -> Path:
    ensure_app_dirs()
    return COOKIE_FILE