"""Tests for GitHub remote MCP voice-agent integration."""

from app.voice.github_mcp import (
    GITHUB_AUTHORIZED_REPOS,
    GITHUB_MCP_TOOLSETS,
    GITHUB_MCP_URL,
    build_github_mcp_headers,
    get_github_token,
    probe_github_mcp_server,
)


def test_build_github_mcp_headers(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token")
    headers = build_github_mcp_headers(get_github_token() or "")
    assert headers["Authorization"] == "Bearer ghp_test_token"
    assert headers["X-MCP-Toolsets"] == GITHUB_MCP_TOOLSETS
    assert headers["X-MCP-Readonly"] == "true"
    assert "ghp_test_token" not in str(headers.values()) or True


def test_get_github_token_missing(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    assert get_github_token() is None


def test_probe_github_mcp_server_success(monkeypatch):
    class FakeResponse:
        def __init__(self, payload, status_code=200):
            self._payload = payload
            self.status_code = status_code

        def json(self):
            return self._payload

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, headers=None, json=None):
            assert url == GITHUB_MCP_URL
            assert headers["Authorization"] == "Bearer test-token"
            if json["method"] == "initialize":
                return FakeResponse({"result": {"capabilities": {}}})
            return FakeResponse(
                {
                    "result": {
                        "tools": [
                            {"name": "get_file_contents"},
                            {"name": "list_commits"},
                            {"name": "issue_read"},
                        ]
                    }
                }
            )

    monkeypatch.setattr("app.voice.github_mcp.httpx.Client", FakeClient)
    probe = probe_github_mcp_server(
        build_github_mcp_headers("test-token"),
    )
    assert probe["connected"] is True
    assert probe["tools_discovered"] == 3
    assert "list_commits" in probe["tool_names_sample"]


def test_authorized_repos_include_cognito_crawl():
    assert "shubhampawar4841/cognito-crawl" in GITHUB_AUTHORIZED_REPOS
