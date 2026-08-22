"""Tests for Google OAuth helpers."""

from app.auth.google_oauth import create_authorization_url, validate_state
from app.auth.token_store import get_google_connection_status, save_google_tokens


def test_oauth_state_is_single_use(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv(
        "GOOGLE_REDIRECT_URI",
        "http://localhost:8000/auth/google/callback",
    )

    from importlib import reload

    import app.auth.google_oauth as google_oauth
    import app.config as config

    reload(config)
    reload(google_oauth)

    _url, state = google_oauth.create_authorization_url()
    assert "accounts.google.com" in _url
    assert google_oauth.validate_state(state) is True
    assert google_oauth.validate_state(state) is False


def test_token_store_public_status(tmp_path, monkeypatch):
    monkeypatch.setenv("NERVA_USER_ID", "test-user")
    store_dir = tmp_path / "google_oauth"
    store_dir.mkdir()
    store_file = store_dir / "tokens.json"
    store_file.write_text('{"users": {}}', encoding="utf-8")

    from importlib import reload

    import app.auth.token_store as token_store

    monkeypatch.setattr(token_store, "_STORE_DIR", store_dir)
    monkeypatch.setattr(token_store, "_STORE_PATH", store_file)
    reload(token_store)

    status = token_store.get_google_connection_status("test-user")
    assert status["connected"] is False

    token_store.save_google_tokens(
        user_id="test-user",
        google_sub="sub-123",
        email="shubham@example.com",
        name="Shubham",
        access_token="access-token",
        refresh_token="refresh-token",
        token_type="Bearer",
        expires_in=3600,
        scopes=["openid", "email"],
    )

    status = get_google_connection_status("test-user")
    assert status["connected"] is True
    assert status["email"] == "shubham@example.com"
    assert status["has_refresh_token"] is True
    assert "access_token" not in status
    assert "refresh_token" not in status
