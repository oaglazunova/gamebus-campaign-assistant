from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Optional

import requests


class CampaignDownloadError(RuntimeError):
    """Raised when login or campaign download fails."""


def _save_cookies(session: requests.Session, cookie_file: Path) -> None:
    cookie_file.parent.mkdir(parents=True, exist_ok=True)
    cookies_dict = requests.utils.dict_from_cookiejar(session.cookies)
    cookie_file.write_text(
        json.dumps(cookies_dict, indent=2),
        encoding="utf-8",
    )


def _load_cookies(session: requests.Session, cookie_file: Path) -> bool:
    if not cookie_file.exists():
        return False

    try:
        data = json.loads(cookie_file.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return False
        session.cookies.update(data)
        return True
    except Exception:
        return False


def _validate_xlsx_response(resp: requests.Response) -> None:
    content_type = resp.headers.get("Content-Type", "")
    content_disposition = resp.headers.get("Content-Disposition", "")

    if "spreadsheetml.sheet" in content_type:
        return
    if ".xlsx" in content_disposition.lower():
        return

    raise CampaignDownloadError(
        f"Unexpected response type. Content-Type={content_type!r}, "
        f"Content-Disposition={content_disposition!r}"
    )


def _download_xlsx_with_session(
    session: requests.Session,
    base_url: str,
    campaign_abbreviation: str,
    timeout_download: int,
) -> Optional[Path]:
    resp = session.post(
        f"{base_url}/api/campaigns/{campaign_abbreviation}/download",
        timeout=timeout_download,
    )

    if resp.status_code in (401, 403):
        return None

    try:
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise CampaignDownloadError(f"Campaign download failed: {exc}") from exc

    _validate_xlsx_response(resp)

    filename = f"campaign-{campaign_abbreviation}.xlsx"
    temp_dir = Path(tempfile.gettempdir()) / "gamebus_campaign_assistant_downloads"
    temp_dir.mkdir(parents=True, exist_ok=True)

    output_path = temp_dir / filename
    output_path.write_bytes(resp.content)
    return output_path


def download_campaign_xlsx(
    base_url: str,
    campaign_abbreviation: str,
    email: Optional[str] = None,
    password: Optional[str] = None,
    cookie_file: Optional[Path] = None,
    timeout_login: int = 30,
    timeout_download: int = 60,
) -> Path:
    """
    Download a campaign description XLSX.

    Strategy:
    1) Try saved cookies first
    2) If that fails and credentials are available, login and retry
    3) Save refreshed cookies after successful login
    """
    base_url = base_url.strip().rstrip("/")
    campaign_abbreviation = campaign_abbreviation.strip()

    if not base_url:
        raise CampaignDownloadError("Base URL is empty.")
    if not campaign_abbreviation:
        raise CampaignDownloadError("Campaign abbreviation is empty.")

    session = requests.Session()

    # 1) Try existing session cookies first
    if cookie_file is not None and _load_cookies(session, cookie_file):
        path = _download_xlsx_with_session(
            session=session,
            base_url=base_url,
            campaign_abbreviation=campaign_abbreviation,
            timeout_download=timeout_download,
        )
        if path is not None:
            return path

    # 2) Fall back to login
    if not email or not password:
        raise CampaignDownloadError(
            "No valid saved session was found, and no credentials are available to log in again."
        )

    try:
        login_resp = session.post(
            f"{base_url}/api/auth/token",
            json={
                "email": email.strip(),
                "password": password,
            },
            timeout=timeout_login,
        )
        login_resp.raise_for_status()
    except requests.RequestException as exc:
        raise CampaignDownloadError(f"Login failed: {exc}") from exc

    if "__session" not in session.cookies:
        raise CampaignDownloadError(
            "Login succeeded but no __session cookie was set."
        )

    if cookie_file is not None:
        _save_cookies(session, cookie_file)

    path = _download_xlsx_with_session(
        session=session,
        base_url=base_url,
        campaign_abbreviation=campaign_abbreviation,
        timeout_download=timeout_download,
    )
    if path is None:
        raise CampaignDownloadError("Download failed even after successful login.")

    return path