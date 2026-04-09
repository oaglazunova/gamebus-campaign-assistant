from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

APP_NAME = "GameBus Campaign Assistant"
APP_ID = "gamebus_campaign_assistant"
APP_VERSION = "0.1.0"

# Paths
PACKAGE_DIR = Path(__file__).resolve().parent
SRC_DIR = PACKAGE_DIR.parent
REPO_ROOT = SRC_DIR.parent
CONFIG_DIR = REPO_ROOT / "config"
DOCS_DIR = REPO_ROOT / "docs"
SAMPLES_DIR = REPO_ROOT / "samples"

APP_CONFIG_FILE = CONFIG_DIR / "app_config.json"

DEFAULT_APP_CONFIG: Dict[str, Any] = {
	"campaigns_base_url": "https://campaigns.healthyw8.gamebus.eu",
	"default_language": "en",
	"default_generate_excel_report": False,
}


def load_app_config() -> Dict[str, Any]:
	"""
	Load global app configuration from config/app_config.json.
	If the file does not exist, create it with defaults.
	If it is invalid, fall back to defaults.
	"""
	CONFIG_DIR.mkdir(parents=True, exist_ok=True)

	if not APP_CONFIG_FILE.exists():
		APP_CONFIG_FILE.write_text(
			json.dumps(DEFAULT_APP_CONFIG, indent=2, ensure_ascii=False),
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