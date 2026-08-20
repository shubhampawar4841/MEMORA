"""Side-effect safety for consequential browser actions."""

from __future__ import annotations

import re
from typing import Any

CONSEQUENTIAL_PATTERNS = [
    r"\bsubmit\b",
    r"\bpurchase\b",
    r"\bbuy\b",
    r"\bcheckout\b",
    r"\bpay\b",
    r"\bapply\b",
    r"\bsend\s+(the\s+)?(message|email|form)\b",
    r"\bdelete\b",
    r"\bremove\s+account\b",
    r"\bchange\s+(password|email|account)\b",
    r"\bconfirm\s+order\b",
    r"\bplace\s+order\b",
    r"\bpost\b",
]

_CONFIRMATION_RE = re.compile(
    r"^\s*(yes|y|confirm|confirmed|go ahead|do it|proceed|ok|okay)\b",
    re.IGNORECASE,
)


def looks_consequential(text: str | None) -> bool:
    if not text:
        return False
    lower = text.lower()
    return any(re.search(pat, lower) for pat in CONSEQUENTIAL_PATTERNS)


def user_confirmed(history: list[dict[str, Any]] | None) -> bool:
    """True if the latest user message is an explicit confirmation."""
    if not history:
        return False
    for message in reversed(history):
        if message.get("role") != "user":
            continue
        content = message.get("content") or ""
        return bool(_CONFIRMATION_RE.match(content.strip()))
    return False


def gate_tool_call(
    tool_name: str,
    arguments: dict[str, Any],
    history: list[dict[str, Any]] | None,
) -> dict[str, Any] | None:
    """
    Return a clarification payload if the tool call must not proceed yet.
    Return None if execution is allowed.
    """
    if tool_name != "interact_with_page":
        return None

    if arguments.get("stop"):
        return None

    prompt = arguments.get("prompt") or ""
    code = arguments.get("code") or ""
    combined = f"{prompt}\n{code}"
    if not looks_consequential(combined):
        return None

    confirmed_flag = bool(arguments.get("confirmed_side_effect"))
    if confirmed_flag and user_confirmed(history):
        return None

    return {
        "requires_confirmation": True,
        "message": (
            "I've prepared the next step, but it looks like a consequential "
            "action (submit / purchase / apply / send / delete / account change). "
            "Do you want me to proceed? Reply Yes to confirm."
        ),
        "pending_tool": tool_name,
        "pending_arguments": {
            k: v
            for k, v in arguments.items()
            if k != "confirmed_side_effect"
        },
    }
