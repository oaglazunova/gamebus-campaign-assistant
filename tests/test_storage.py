from __future__ import annotations

from pathlib import Path

from campaign_assistant import storage


def patch_storage_paths(monkeypatch, tmp_path: Path):
    app_dir = tmp_path / "appdata"
    settings_file = app_dir / "settings.json"
    cookie_file = app_dir / "session_cookies.json"

    monkeypatch.setattr(storage, "APP_DIR", app_dir)
    monkeypatch.setattr(storage, "SETTINGS_FILE", settings_file)
    monkeypatch.setattr(storage, "COOKIE_FILE", cookie_file)

    return app_dir, settings_file, cookie_file


def test_load_settings_creates_defaults_when_missing(monkeypatch, tmp_path):
    _, settings_file, _ = patch_storage_paths(monkeypatch, tmp_path)

    result = storage.load_settings()

    assert settings_file.exists()
    assert result["email"] == ""
    assert result["remember_credentials"] is True
    assert result["saved_campaign_abbreviations"] == []


def test_save_and_load_settings_roundtrip(monkeypatch, tmp_path):
    _, _, _ = patch_storage_paths(monkeypatch, tmp_path)

    settings = {
        "email": "user@example.com",
        "remember_credentials": False,
        "last_campaign_abbreviation": "ABC",
        "last_source_mode": "Upload Excel file",
        "saved_campaign_abbreviations": ["ABC", "XYZ"],
    }

    storage.save_settings(settings)
    loaded = storage.load_settings()

    assert loaded["email"] == "user@example.com"
    assert loaded["remember_credentials"] is False
    assert loaded["last_campaign_abbreviation"] == "ABC"
    assert loaded["last_source_mode"] == "Upload Excel file"
    assert loaded["saved_campaign_abbreviations"] == ["ABC", "XYZ"]


def test_add_saved_campaign_abbreviation_normalizes_and_deduplicates(monkeypatch, tmp_path):
    _, _, _ = patch_storage_paths(monkeypatch, tmp_path)

    storage.save_settings(storage.DEFAULT_SETTINGS.copy())

    storage.add_saved_campaign_abbreviation("  TEST  ")
    storage.add_saved_campaign_abbreviation("TEST")
    settings = storage.add_saved_campaign_abbreviation("ANOTHER")

    assert settings["saved_campaign_abbreviations"] == ["ANOTHER", "TEST"]

    loaded = storage.load_settings()
    assert loaded["saved_campaign_abbreviations"] == ["ANOTHER", "TEST"]


def test_add_saved_campaign_abbreviation_with_provided_settings(monkeypatch, tmp_path):
    _, _, _ = patch_storage_paths(monkeypatch, tmp_path)

    my_settings = storage.DEFAULT_SETTINGS.copy()
    my_settings["saved_campaign_abbreviations"] = ["EXISTING"]

    result = storage.add_saved_campaign_abbreviation("NEW", settings=my_settings)

    assert result["saved_campaign_abbreviations"] == ["EXISTING", "NEW"]
    assert my_settings["saved_campaign_abbreviations"] == ["EXISTING", "NEW"]

    loaded = storage.load_settings()
    assert loaded["saved_campaign_abbreviations"] == ["EXISTING", "NEW"]


def test_get_cookie_file_returns_expected_path(monkeypatch, tmp_path):
    _, _, cookie_file = patch_storage_paths(monkeypatch, tmp_path)

    result = storage.get_cookie_file()

    assert result == cookie_file
    assert cookie_file.parent.exists()


def test_delete_cookie_file_removes_existing_file(monkeypatch, tmp_path):
    _, _, cookie_file = patch_storage_paths(monkeypatch, tmp_path)

    cookie_file.parent.mkdir(parents=True, exist_ok=True)
    cookie_file.write_text("cookie-data", encoding="utf-8")
    assert cookie_file.exists()

    storage.delete_cookie_file()

    assert not cookie_file.exists()


def test_save_load_delete_password_uses_keyring(monkeypatch):
    saved = {}

    def fake_set_password(service_name, email, password):
        saved[(service_name, email)] = password

    def fake_get_password(service_name, email):
        return saved.get((service_name, email))

    def fake_delete_password(service_name, email):
        saved.pop((service_name, email), None)

    monkeypatch.setattr(storage.keyring, "set_password", fake_set_password)
    monkeypatch.setattr(storage.keyring, "get_password", fake_get_password)
    monkeypatch.setattr(storage.keyring, "delete_password", fake_delete_password)

    email = "user@example.com"

    storage.save_password(email, "secret123")
    assert storage.load_password(email) == "secret123"

    storage.delete_password(email)
    assert storage.load_password(email) is None