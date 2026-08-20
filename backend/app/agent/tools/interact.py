from __future__ import annotations

import logging
from typing import Any

from app.agent.tools.base import AgentTool, fail, ok
from app.config import AGENT_TOOL_CONTENT_LIMIT
from app.firecrawl.client import (
    document_to_dict,
    get_firecrawl_client,
    truncate_text,
)

logger = logging.getLogger("nerva.agent.tools")


def _interact(args: dict[str, Any]) -> dict[str, Any]:
    tool = "interact_with_page"
    scrape_id = (
        args.get("scrape_id")
        or args.get("scrapeId")
        or args.get("job_id")
        or ""
    ).strip()
    prompt = (args.get("prompt") or "").strip()
    code = (args.get("code") or "").strip() or None
    language = (args.get("language") or "node").strip()
    stop = bool(args.get("stop", False))
    timeout = args.get("timeout")

    if not scrape_id:
        return fail(tool, "scrape_id required from scrape_page")
    if not prompt and not code and not stop:
        return fail(tool, "Provide prompt, code, or stop=true")

    try:
        client = get_firecrawl_client()
        logger.info("Tool selected: interact_with_page")

        if stop:
            result = client.stop_interaction(scrape_id)
            logger.info("Tool completed: interact_with_page (stop)")
            return ok(
                tool,
                {"scrape_id": scrape_id, "stopped": True, "result": document_to_dict(result)},
            )

        kwargs: dict[str, Any] = {"language": language}
        if timeout is not None:
            kwargs["timeout"] = int(timeout)

        if prompt:
            result = client.interact(scrape_id, prompt=prompt, **kwargs)
        else:
            result = client.interact(scrape_id, code=code, **kwargs)

        logger.info("Tool completed: interact_with_page")
        data = document_to_dict(result)
        output = data.get("output") or data.get("result") or data.get("stdout")
        if isinstance(output, str):
            output = truncate_text(output, min(4000, AGENT_TOOL_CONTENT_LIMIT))

        return ok(
            tool,
            {
                "scrape_id": scrape_id,
                "success": data.get("success", True),
                "output": output,
                "error": data.get("error") or data.get("stderr"),
            },
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("interact_with_page failed")
        return fail(tool, f"Unable to interact with page: {exc}")


interact_with_page_tool = AgentTool(
    name="interact_with_page",
    description=(
        "Browser actions via scrape_id. Set stop=true when done. "
        "For submit/buy/apply use confirmed_side_effect after user Yes."
    ),
    parameters={
        "type": "object",
        "properties": {
            "scrape_id": {"type": "string"},
            "prompt": {"type": "string"},
            "code": {"type": "string"},
            "language": {"type": "string", "default": "node"},
            "timeout": {"type": "integer"},
            "stop": {"type": "boolean", "default": False},
            "confirmed_side_effect": {"type": "boolean", "default": False},
        },
        "required": ["scrape_id"],
    },
    execute=_interact,
    status_message="Interacting with page…",
    read_only=False,
)
