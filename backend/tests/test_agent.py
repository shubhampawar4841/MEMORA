"""Unit tests for Firecrawl agent tools, safety, and orchestrator limits."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.agent.safety import gate_tool_call, looks_consequential, user_confirmed
from app.agent.tools.base import fail, ok
from app.agent.tools.registry import execute_tool, list_tools
from app.config import MAX_AGENT_STEPS


class FakeDoc:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def model_dump(self, exclude_none=True):
        data = dict(self.__dict__)
        if exclude_none:
            return {k: v for k, v in data.items() if v is not None}
        return data


@pytest.fixture
def fake_client():
    return MagicMock()


def test_tool_registry_contains_expected_tools():
    names = {t.name for t in list_tools()}
    assert {
        "web_search",
        "scrape_page",
        "map_website",
        "crawl_website",
        "extract_data",
        "interact_with_page",
        "screenshot",
    } <= names


def test_ok_fail_normalization():
    assert ok("scrape_page", {"a": 1}) == {
        "success": True,
        "tool": "scrape_page",
        "data": {"a": 1},
    }
    assert fail("scrape_page", "boom")["success"] is False


@patch("app.agent.tools.search.get_firecrawl_client")
def test_web_search_success(mock_get, fake_client):
    mock_get.return_value = fake_client
    fake_client.search.return_value = SimpleNamespace(
        web=[
            SimpleNamespace(
                model_dump=lambda exclude_none=True: {
                    "url": "https://example.com",
                    "title": "Example",
                    "description": "desc",
                }
            )
        ]
    )
    result = execute_tool("web_search", {"query": "test", "limit": 3})
    assert result["success"] is True
    assert result["data"]["count"] == 1
    fake_client.search.assert_called_once()


@patch("app.agent.tools.scrape.get_firecrawl_client")
def test_scrape_page_success(mock_get, fake_client):
    mock_get.return_value = fake_client
    fake_client.scrape.return_value = FakeDoc(
        markdown="# Hello",
        html=None,
        links=["https://example.com/a"],
        metadata={
            "title": "Example Domain",
            "scrape_id": "job-123",
            "status_code": 200,
        },
    )
    result = execute_tool(
        "scrape_page",
        {"url": "https://example.com", "formats": ["markdown", "links"]},
    )
    assert result["success"] is True
    assert result["data"]["metadata"]["scrape_id"] == "job-123"
    assert "Hello" in (result["data"]["markdown"] or "")


def test_scrape_page_invalid_url():
    result = execute_tool("scrape_page", {"url": "not-a-url"})
    assert result["success"] is False


@patch("app.agent.tools.map.get_firecrawl_client")
def test_map_website(mock_get, fake_client):
    mock_get.return_value = fake_client
    fake_client.map.return_value = FakeDoc(
        links=["https://example.com/a", "https://example.com/b"]
    )
    result = execute_tool("map_website", {"url": "https://example.com"})
    assert result["success"] is True
    assert result["data"]["count"] == 2


@patch("app.agent.tools.crawl.get_firecrawl_client")
def test_crawl_website_respects_limit(mock_get, fake_client):
    mock_get.return_value = fake_client
    fake_client.crawl.return_value = FakeDoc(
        status="completed",
        data=[
            FakeDoc(
                markdown="page",
                metadata={"source_url": "https://example.com/1", "title": "One"},
            )
        ],
    )
    result = execute_tool(
        "crawl_website",
        {"url": "https://example.com", "limit": 1000},
    )
    assert result["success"] is True
    kwargs = fake_client.crawl.call_args.kwargs
    assert kwargs["limit"] <= 25


@patch("app.agent.tools.extract.get_firecrawl_client")
def test_extract_data(mock_get, fake_client):
    mock_get.return_value = fake_client
    fake_client.scrape.return_value = FakeDoc(
        json={"company": "Acme", "role": "Engineer"},
        metadata={"title": "Job"},
    )
    result = execute_tool(
        "extract_data",
        {
            "url": "https://example.com/jobs",
            "schema": {"company": "string", "role": "string"},
            "prompt": "Extract jobs",
        },
    )
    assert result["success"] is True
    assert result["data"]["results"][0]["json"]["company"] == "Acme"


@patch("app.agent.tools.interact.get_firecrawl_client")
def test_interact_with_page(mock_get, fake_client):
    mock_get.return_value = fake_client
    fake_client.interact.return_value = FakeDoc(
        success=True,
        output="Clicked next",
    )
    result = execute_tool(
        "interact_with_page",
        {"scrape_id": "job-1", "prompt": "Click the next button"},
    )
    assert result["success"] is True
    fake_client.interact.assert_called_once()


@patch("app.agent.tools.screenshot.get_firecrawl_client")
def test_screenshot_omits_binary(mock_get, fake_client):
    mock_get.return_value = fake_client
    fake_client.scrape.return_value = FakeDoc(
        screenshot="data:image/png;base64,AAAA",
        metadata={"title": "Shot", "scrape_id": "s1"},
    )
    result = execute_tool("screenshot", {"url": "https://example.com"})
    assert result["success"] is True
    shot = result["data"]["screenshot"]
    assert "AAAA" not in json.dumps(shot)
    assert shot["type"] == "inline_data_uri"


def test_unknown_tool_failure():
    result = execute_tool("not_real", {})
    assert result["success"] is False


def test_consequential_detection_and_gate():
    assert looks_consequential("please submit the application")
    assert not looks_consequential("click the pricing tab")

    blocked = gate_tool_call(
        "interact_with_page",
        {"scrape_id": "x", "prompt": "Click Submit to apply for the job"},
        [{"role": "user", "content": "Apply for this job"}],
    )
    assert blocked is not None
    assert blocked["requires_confirmation"] is True

    allowed = gate_tool_call(
        "interact_with_page",
        {
            "scrape_id": "x",
            "prompt": "Click Submit to apply for the job",
            "confirmed_side_effect": True,
        },
        [
            {"role": "assistant", "content": "confirm?"},
            {"role": "user", "content": "Yes"},
        ],
    )
    assert allowed is None
    assert user_confirmed([{"role": "user", "content": "Yes, go ahead"}])


@patch("app.agent.orchestrator.groq_client")
def test_agent_max_steps(mock_groq):
    from app.agent.orchestrator import run_agent

    tool_call = SimpleNamespace(
        id="call-1",
        function=SimpleNamespace(
            name="web_search",
            arguments='{"query":"x","limit":1}',
        ),
    )
    assistant = SimpleNamespace(
        content="",
        tool_calls=[tool_call],
    )
    choice = SimpleNamespace(message=assistant, finish_reason="tool_calls")
    mock_groq.chat.completions.create.return_value = SimpleNamespace(
        choices=[choice]
    )

    with patch(
        "app.agent.orchestrator.execute_tool",
        return_value=ok("web_search", {"results": []}),
    ):
        result = run_agent("search forever")

    assert result["success"] is False
    assert "maximum" in result["message"].lower()
    assert mock_groq.chat.completions.create.call_count == MAX_AGENT_STEPS


@patch("app.agent.orchestrator.groq_client")
def test_agent_final_answer_without_tools(mock_groq):
    from app.agent.orchestrator import run_agent

    assistant = SimpleNamespace(content="All done.", tool_calls=None)
    choice = SimpleNamespace(message=assistant, finish_reason="stop")
    mock_groq.chat.completions.create.return_value = SimpleNamespace(
        choices=[choice]
    )

    result = run_agent("hello")
    assert result["success"] is True
    assert result["message"] == "All done."
    assert result["steps"] == []


def test_planner_web_heuristic():
    from app.agent.planner import plan_route

    plan = plan_route("Go to https://example.com and find the pricing")
    assert plan["route"] == "web"

    ingest = plan_route(
        "Add this website to my knowledge base: https://docs.example.com"
    )
    assert ingest["route"] == "ingest_web"


def test_firecrawl_client_requires_key(monkeypatch):
    from app.firecrawl import client as fc

    monkeypatch.setattr(fc, "FIRECRAWL_API_KEY", None)
    fc.get_firecrawl_client.cache_clear()
    with pytest.raises(fc.FirecrawlNotConfiguredError):
        fc.get_firecrawl_client()
    fc.get_firecrawl_client.cache_clear()
