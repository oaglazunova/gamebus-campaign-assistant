from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

DEFAULT_APP_CONFIG: Dict[str, Any] = {
    "campaigns_base_url": "https://campaigns.healthyw8.gamebus.eu"
}

PROJECT_ROOT = Path(__file__).resolve().parent
APP_CONFIG_FILE = PROJECT_ROOT / "app_config.json"


def load_app_config() -> Dict[str, Any]:
    if not APP_CONFIG_FILE.exists():
        APP_CONFIG_FILE.write_text(
            json.dumps(DEFAULT_APP_CONFIG, indent=2),
            encoding="utf-8",
        )
        return DEFAULT_APP_CONFIG.copy()

    try:
        data = json.loads(APP_CONFIG_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return DEFAULT_APP_CONFIG.copy()

        merged = DEFAULT_APP_CONFIG.copy()
        merged.update(data)
        return merged
    except Exception:
        return DEFAULT_APP_CONFIG.copy()