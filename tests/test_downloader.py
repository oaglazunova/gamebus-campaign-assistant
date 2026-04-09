from __future__ import annotations

import json
from pathlib import Path

import pytest
import requests

from campaign_assistant.downloader import CampaignDownloadError, download_campaign_xlsx


class FakeResponse:
    def __init__(
        self,
        status_code: int = 200,
        headers: dict | None = None,
        content: bytes = b"",
        raise_exc: Exception | None = None,
    ) -> None:
        self.status_code = status_code
        self.headers = headers or {}
        self.content = content
        self._raise_exc = raise_exc

    def raise_for_status(self) -> None:
        if self._raise_exc is not None:
            raise self._raise_exc

    def iter_content(self, chunk_size: int = 8192):
        if self.content:
            yield self.content


class FakeSession:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.cookies = requests.Session().cookies
        self.headers = {}
        self.calls: list[dict] = []

    def post(
        self,
        url: str,
        json: dict | None = None,
        timeout: int | None = None,
        stream: bool | None = None,
    ):
        self.calls.append(
            {
                "url": url,
                "json": json,
                "timeout": timeout,
                "stream": stream,
            }
        )
        if not self.responses:
            raise AssertionError("No more fake responses configured")
        return self.responses.pop(0)


def _xlsx_headers() -> dict:
    return {
        "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "Content-Disposition": 'attachment; filename="campaign.xlsx"',
    }


def test_download_success_after_login(monkeypatch, tmp_path):
    fake_session = FakeSession(
        responses=[
            FakeResponse(status_code=200),  # login
            FakeResponse(
                status_code=200,
                headers=_xlsx_headers(),
                content=b"excel-bytes",
            ),  # download
        ]
    )

    def fake_session_factory():
        return fake_session

    monkeypatch.setattr("campaign_assistant.downloader.requests.Session", fake_session_factory)
    monkeypatch.setattr("campaign_assistant.downloader.tempfile.gettempdir", lambda: str(tmp_path))

    # Simulate successful login by setting the session cookie during the login call.
    original_post = fake_session.post

    def post_with_cookie(url: str, json=None, timeout=None, stream=None):
        response = original_post(url, json=json, timeout=timeout, stream=stream)
        if url.endswith("/api/auth/token"):
            fake_session.cookies.set("__session", "abc123")
        return response

    fake_session.post = post_with_cookie  # type: ignore[method-assign]

    cookie_file = tmp_path / "cookies.json"
    result = download_campaign_xlsx(
        base_url="https://campaigns.example.com",
        campaign_abbreviation="MYCAMPAIGN",
        email="user@example.com",
        password="secret",
        cookie_file=cookie_file,
    )

    assert result.exists()
    assert result.read_bytes() == b"excel-bytes"
    assert result.name == "campaign-MYCAMPAIGN.xlsx"
    assert cookie_file.exists()

    # First call = login, second call = download
    assert len(fake_session.calls) == 2
    assert fake_session.calls[0]["url"].endswith("/api/auth/token")
    assert fake_session.calls[1]["url"].endswith("/api/campaigns/MYCAMPAIGN/download")


def test_download_uses_saved_cookies_without_login(monkeypatch, tmp_path):
    cookie_file = tmp_path / "cookies.json"
    cookie_file.write_text(json.dumps({"__session": "saved-cookie"}), encoding="utf-8")

    fake_session = FakeSession(
        responses=[
            FakeResponse(
                status_code=200,
                headers=_xlsx_headers(),
                content=b"from-cookie-session",
            )
        ]
    )

    monkeypatch.setattr("campaign_assistant.downloader.requests.Session", lambda: fake_session)
    monkeypatch.setattr("campaign_assistant.downloader.tempfile.gettempdir", lambda: str(tmp_path))

    result = download_campaign_xlsx(
        base_url="https://campaigns.example.com",
        campaign_abbreviation="COOKIECAMPAIGN",
        cookie_file=cookie_file,
    )

    assert result.exists()
    assert result.read_bytes() == b"from-cookie-session"
    assert len(fake_session.calls) == 1
    assert fake_session.calls[0]["url"].endswith("/api/campaigns/COOKIECAMPAIGN/download")


def test_download_cookie_fallback_to_login(monkeypatch, tmp_path):
    cookie_file = tmp_path / "cookies.json"
    cookie_file.write_text(json.dumps({"__session": "expired-cookie"}), encoding="utf-8")

    fake_session = FakeSession(
        responses=[
            FakeResponse(status_code=401),  # cookie-based download fails
            FakeResponse(status_code=200),  # login
            FakeResponse(
                status_code=200,
                headers=_xlsx_headers(),
                content=b"after-login-download",
            ),  # download after login
        ]
    )

    original_post = fake_session.post

    def post_with_cookie(url: str, json=None, timeout=None, stream=None):
        response = original_post(url, json=json, timeout=timeout, stream=stream)
        if url.endswith("/api/auth/token"):
            fake_session.cookies.set("__session", "new-cookie")
        return response

    fake_session.post = post_with_cookie  # type: ignore[method-assign]

    monkeypatch.setattr("campaign_assistant.downloader.requests.Session", lambda: fake_session)
    monkeypatch.setattr("campaign_assistant.downloader.tempfile.gettempdir", lambda: str(tmp_path))

    result = download_campaign_xlsx(
        base_url="https://campaigns.example.com",
        campaign_abbreviation="FALLBACK",
        email="user@example.com",
        password="secret",
        cookie_file=cookie_file,
    )

    assert result.exists()
    assert result.read_bytes() == b"after-login-download"
    assert len(fake_session.calls) == 3
    assert fake_session.calls[0]["url"].endswith("/api/campaigns/FALLBACK/download")
    assert fake_session.calls[1]["url"].endswith("/api/auth/token")
    assert fake_session.calls[2]["url"].endswith("/api/campaigns/FALLBACK/download")


def test_download_raises_on_invalid_response_type(monkeypatch, tmp_path):
    fake_session = FakeSession(
        responses=[
            FakeResponse(status_code=200),  # login
            FakeResponse(
                status_code=200,
                headers={"Content-Type": "text/html"},
                content=b"<html>not an xlsx</html>",
            ),
        ]
    )

    original_post = fake_session.post

    def post_with_cookie(url: str, json=None, timeout=None, stream=None):
        response = original_post(url, json=json, timeout=timeout, stream=stream)
        if url.endswith("/api/auth/token"):
            fake_session.cookies.set("__session", "abc123")
        return response

    fake_session.post = post_with_cookie  # type: ignore[method-assign]

    monkeypatch.setattr("campaign_assistant.downloader.requests.Session", lambda: fake_session)
    monkeypatch.setattr("campaign_assistant.downloader.tempfile.gettempdir", lambda: str(tmp_path))

    with pytest.raises(CampaignDownloadError, match="Unexpected response type"):
        download_campaign_xlsx(
            base_url="https://campaigns.example.com",
            campaign_abbreviation="BADTYPE",
            email="user@example.com",
            password="secret",
            cookie_file=tmp_path / "cookies.json",
        )


def test_download_raises_when_login_has_no_session_cookie(monkeypatch, tmp_path):
    fake_session = FakeSession(
        responses=[
            FakeResponse(status_code=200),  # login succeeds but sets no cookie
        ]
    )

    monkeypatch.setattr("campaign_assistant.downloader.requests.Session", lambda: fake_session)

    with pytest.raises(CampaignDownloadError, match="no __session cookie"):
        download_campaign_xlsx(
            base_url="https://campaigns.example.com",
            campaign_abbreviation="NOCOOKIE",
            email="user@example.com",
            password="secret",
            cookie_file=tmp_path / "cookies.json",
        )