"""Tests for Google OAuth helpers."""

from app.auth.google_access import google_mcp_auth_headers
from app.auth.google_oauth import (
    GOOGLE_CALENDAR_MCP_SCOPES,
    GOOGLE_GMAIL_MCP_SCOPES,
    create_authorization_url,
    has_workspace_mcp_scopes,
    validate_state,
)
from app.auth.token_store import get_google_connection_status, save_google_tokens

_FULL_MCP_SCOPES = list(GOOGLE_GMAIL_MCP_SCOPES) + list(GOOGLE_CALENDAR_MCP_SCOPES)


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

    reload(token_store)
    monkeypatch.setattr(token_store, "_STORE_DIR", store_dir)
    monkeypatch.setattr(token_store, "_STORE_PATH", store_file)

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


def test_get_valid_google_access_token_refreshes_when_expired(
    tmp_path, monkeypatch,
):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv(
        "GOOGLE_REDIRECT_URI",
        "http://localhost:8000/auth/google/callback",
    )

    store_dir = tmp_path / "google_oauth"
    store_dir.mkdir()
    store_file = store_dir / "tokens.json"
    store_file.write_text('{"users": {}}', encoding="utf-8")

    from importlib import reload

    import app.auth.google_access as google_access
    import app.auth.token_store as token_store

    reload(token_store)
    monkeypatch.setattr(token_store, "_STORE_DIR", store_dir)
    monkeypatch.setattr(token_store, "_STORE_PATH", store_file)
    reload(google_access)

    token_store.save_google_tokens(
        user_id="test-user",
        google_sub="sub-123",
        email="shubham@example.com",
        name="Shubham",
        access_token="expired-access",
        refresh_token="refresh-token",
        token_type="Bearer",
        expires_in=-10,
        scopes=_FULL_MCP_SCOPES,
    )

    def fake_refresh(refresh_token: str):
        assert refresh_token == "refresh-token"
        return {
            "access_token": "fresh-access",
            "expires_in": 3600,
            "token_type": "Bearer",
            "scope": " ".join(_FULL_MCP_SCOPES),
        }

    monkeypatch.setattr(
        google_access,
        "refresh_access_token",
        fake_refresh,
    )

    token = google_access.get_valid_google_access_token("test-user")
    assert token == "fresh-access"

    stored = token_store.get_google_tokens("test-user")
    assert stored is not None
    assert stored.access_token == "fresh-access"
    assert stored.refresh_token == "refresh-token"


def test_google_mcp_auth_headers_exact_format(tmp_path, monkeypatch):
    monkeypatch.setenv("NERVA_USER_ID", "test-user")
    store_dir = tmp_path / "google_oauth"
    store_dir.mkdir()
    store_file = store_dir / "tokens.json"
    store_file.write_text('{"users": {}}', encoding="utf-8")

    from importlib import reload

    import app.auth.google_access as google_access
    import app.auth.token_store as token_store

    reload(token_store)
    monkeypatch.setattr(token_store, "_STORE_DIR", store_dir)
    monkeypatch.setattr(token_store, "_STORE_PATH", store_file)
    reload(google_access)

    token_store.save_google_tokens(
        user_id="test-user",
        google_sub="sub-123",
        email="shubham@example.com",
        name="Shubham",
        access_token="valid-access-token",
        refresh_token="refresh-token",
        token_type="Bearer",
        expires_in=3600,
        scopes=_FULL_MCP_SCOPES,
    )

    headers = google_access.google_mcp_auth_headers("test-user")
    assert headers == {"Authorization": "Bearer valid-access-token"}


def test_google_mcp_auth_headers_rejects_missing_scopes(tmp_path, monkeypatch):
    monkeypatch.setenv("NERVA_USER_ID", "test-user")
    store_dir = tmp_path / "google_oauth"
    store_dir.mkdir()
    store_file = store_dir / "tokens.json"
    store_file.write_text('{"users": {}}', encoding="utf-8")

    from importlib import reload

    import app.auth.google_access as google_access
    import app.auth.token_store as token_store

    reload(token_store)
    monkeypatch.setattr(token_store, "_STORE_DIR", store_dir)
    monkeypatch.setattr(token_store, "_STORE_PATH", store_file)
    reload(google_access)

    token_store.save_google_tokens(
        user_id="test-user",
        google_sub="sub-123",
        email="shubham@example.com",
        name="Shubham",
        access_token="valid-access-token",
        refresh_token="refresh-token",
        token_type="Bearer",
        expires_in=3600,
        scopes=["https://www.googleapis.com/auth/gmail.readonly"],
    )

    assert google_access.google_mcp_auth_headers("test-user") is None


def test_has_workspace_mcp_scopes():
    assert has_workspace_mcp_scopes(
        list(GOOGLE_GMAIL_MCP_SCOPES) + list(GOOGLE_CALENDAR_MCP_SCOPES)
    )
    assert has_workspace_mcp_scopes(
        [
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/calendar.readonly",
        ]
    )
    assert not has_workspace_mcp_scopes(
        ["https://www.googleapis.com/auth/gmail.readonly"]
    )


def test_google_mcp_bridge_headers_endpoint(tmp_path, monkeypatch):
    monkeypatch.setenv("NERVA_USER_ID", "test-user")
    store_dir = tmp_path / "google_oauth"
    store_dir.mkdir()
    store_file = store_dir / "tokens.json"
    store_file.write_text('{"users": {}}', encoding="utf-8")

    from importlib import reload

    import app.auth.token_store as token_store
    import app.main as main

    reload(token_store)
    monkeypatch.setattr(token_store, "_STORE_DIR", store_dir)
    monkeypatch.setattr(token_store, "_STORE_PATH", store_file)

    token_store.save_google_tokens(
        user_id="test-user",
        google_sub="sub-123",
        email="shubham@example.com",
        name="Shubham",
        access_token="bridge-access-token",
        refresh_token="refresh-token",
        token_type="Bearer",
        expires_in=3600,
        scopes=_FULL_MCP_SCOPES,
    )

    from fastapi.testclient import TestClient

    import app.routers.auth as auth_router

    monkeypatch.setattr(auth_router, "GOOGLE_MCP_BRIDGE_SECRET", "test-bridge-secret")

    client = TestClient(main.app)
    response = client.get(
        "/auth/google/mcp/headers?user_id=test-user",
        headers={"X-Nerva-MCP-Bridge-Key": "test-bridge-secret"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["headers"] == {
        "Authorization": "Bearer bridge-access-token",
    }
    assert payload["token_refresh_performed"] is False
    assert "refresh_token" not in payload
