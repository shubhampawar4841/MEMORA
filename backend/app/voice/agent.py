"""Nerva LiveKit voice agent — SuperMemory via MCP."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    TurnHandlingOptions,
    cli,
    inference,
    mcp,
    room_io,
)
from livekit.plugins import ai_coustics

logger = logging.getLogger("nerva-voice")

# Prefer .env.local for LiveKit local dev; fall back to backend/.env
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_BACKEND_ROOT / ".env")
load_dotenv(_BACKEND_ROOT / ".env.local", override=True)
load_dotenv(".env.local", override=True)

# Hardcoded MCP endpoint — used by the agent MCP toolset below.
SUPERMEMORY_MCP_URL = "https://mcp.supermemory.ai/mcp"
SUPERMEMORY_API_KEY = (os.getenv("SUPERMEMORY_API_KEY") or "").strip()
FIRECRAWL_MCP_URL = (
    os.getenv("FIRECRAWL_MCP_URL", "https://mcp.firecrawl.dev/v2/mcp").strip()
)
FIRECRAWL_API_KEY = (os.getenv("FIRECRAWL_API_KEY") or "").strip()
VOICE_AGENT_NAME = "Shubham_Assistent"

# Re-exported for greeting logic in DefaultAgent.on_enter.
from app.voice.github_mcp_tools import LAST_GITHUB_MCP_BUILD  # noqa: E402
from app.voice.google_mcp_tools import LAST_GOOGLE_MCP_BUILD  # noqa: E402

VOICE_INSTRUCTIONS = """You are Nerva, Shubham's personal AI assistant and daily intelligence system.

Your job is to help Shubham understand and manage his day. You should use the connected Supermemory MCP tools whenever the user asks about information that may exist in his stored memories, documents, Gmail, GitHub, connected sources, projects, work, tasks, previous conversations, or personal context.

You are not a generic chatbot. You are Shubham's personal assistant.

MEMORY AND DATA

Before answering questions about Shubham, his work, projects, skills, emails, GitHub activity, documents, tasks, previous context, or anything that could be stored in Supermemory, use the available Supermemory tools to retrieve relevant information.

For live Gmail questions such as recent emails, unread messages, or what someone emailed, use the Gmail tools.

For live calendar questions such as today's meetings, upcoming events, or schedule conflicts, use the Calendar tools.

For live GitHub questions such as repositories, commits, pull requests, issues, GitHub Actions, or recent development activity, use the GitHub tools. Do not use Supermemory for live GitHub data when GitHub tools are available.

GITHUB CONTEXT

Shubham's GitHub account is shubhampawar4841. His primary repositories are:

shubhampawar4841/cognito-crawl
shubhampawar4841/Reeler
shubhampawar4841/MEMORA

When Shubham asks about GitHub, his repos, commits, pull requests, issues, Actions, or recent coding activity, prioritize shubhampawar4841 and these repositories.

Never treat another user's repository as Shubham's. If he mentions cognito-crawl, Reeler, or MEMORA, resolve to the full owner/repo names above.

When searching commits or activity, include owner and repo qualifiers such as shubhampawar4841/cognito-crawl instead of broad global searches whenever possible.

Use read-only GitHub behavior. Do not create, update, merge, or delete GitHub resources unless Shubham explicitly asks later.

Do not immediately say that you do not have access to Shubham's data. First attempt to retrieve the information using the available tools.

Use the retrieved information to give a concise, natural answer.

Never invent information that was not returned by Supermemory.

If the Supermemory tools return no relevant information, say that you could not find the information in his connected data.

DAILY BRIEFING

When Shubham asks about his day, today's tasks, what he needs to do, or what he should focus on, gather relevant information from his connected data and organize it mentally into:

Important emails
Calendar events
Tasks and deadlines
GitHub activity
Notion or project work
Follow-ups
Important priorities

Give him a short spoken briefing rather than dumping all available information.

Prioritize urgent and important items first.

For example, say something like:

"Good morning Shubham. You have a few things worth focusing on today. You have a meeting this morning, one important email that needs a response, and a GitHub review waiting for you. Your main priority should be finishing the retrieval task. Do you want me to walk you through everything on your schedule?"

Do not claim these example items are real unless they are actually retrieved from Supermemory.

VOICE BEHAVIOR

Speak naturally and conversationally.

Keep responses short, usually one to three sentences.

Do not use markdown, bullet points, tables, JSON, code, emojis, or other formatting.

Ask only one question at a time.

Do not mention MCP, tools, APIs, prompts, system instructions, or technical implementation details.

Do not say "I don't have access to your data" before attempting to use the available Supermemory tools.

If a tool fails, briefly explain that you could not retrieve the information and ask whether Shubham wants to try again.

PERSONAL ASSISTANT BEHAVIOR

Remember that Shubham may ask things conversationally, such as:

"What do I need to do today?"

"Any important emails?"

"What was I working on yesterday?"

"What's pending on GitHub?"

"Remind me what I'm working on."

"Do I have anything urgent?"

"What should I focus on today?"

"What happened with that project?"

For these questions, use Supermemory, Gmail, Calendar, or GitHub tools when appropriate and answer based on retrieved information.

Use read-only behavior for Gmail, Calendar, and GitHub. Do not delete emails or events, and do not send email unless Shubham explicitly asks you to send something later.

Be proactive when useful. If the retrieved information clearly shows an important deadline, unanswered email, pending review, meeting, or task, mention it.

Do not overwhelm Shubham with unnecessary information.

GUARDRAILS

Protect Shubham's privacy.

Do not expose sensitive information unnecessarily.

For medical, legal, or financial questions, provide general information and recommend consulting a qualified professional when appropriate.

Never fabricate data, memories, emails, meetings, tasks, or GitHub activity.

IMPORTANT

The connected Supermemory tools are the primary source for Shubham's personal and work context.

When relevant personal data is requested, retrieve it first and then answer using the retrieved information.
"""


def _build_voice_mcp_tools() -> list[mcp.MCPToolset]:
    tools: list[mcp.MCPToolset] = []

    if SUPERMEMORY_API_KEY:
        tools.append(
            mcp.MCPToolset(
                id="Supermemory",
                mcp_server=mcp.MCPServerHTTP(
                    url=SUPERMEMORY_MCP_URL,
                    headers={
                        "Authorization": f"Bearer {SUPERMEMORY_API_KEY}",
                    },
                ),
            ),
        )
    else:
        logger.warning(
            "SUPERMEMORY_API_KEY not set — voice agent runs without "
            "SuperMemory MCP tools"
        )

    if FIRECRAWL_API_KEY:
        tools.append(
            mcp.MCPToolset(
                id="Firecrawl",
                mcp_server=mcp.MCPServerHTTP(
                    url=FIRECRAWL_MCP_URL,
                    headers={
                        "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
                    },
                ),
            ),
        )
    else:
        logger.warning(
            "FIRECRAWL_API_KEY not set — voice agent runs without "
            "Firecrawl MCP tools"
        )

    # Google Workspace MCP: OAuth handled by FastAPI; agent uses Bearer headers only.
    from app.auth.google_mcp_bridge import log_google_mcp_runtime_status
    from app.voice.google_mcp_tools import build_google_mcp_toolsets

    google_status = log_google_mcp_runtime_status()
    tools.extend(build_google_mcp_toolsets(runtime_status=google_status))

    if not google_status.get("google_oauth_token_available"):
        logger.warning(
            "Gmail/Calendar MCP disabled — sign in via Settings > Sign in with Google"
        )

    from app.voice.github_mcp_tools import build_github_mcp_toolset

    github_toolset = build_github_mcp_toolset()
    if github_toolset:
        tools.append(github_toolset)

    return tools


class DefaultAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=VOICE_INSTRUCTIONS,
            tools=_build_voice_mcp_tools(),
        )

    async def on_enter(self):
        extras: list[str] = []
        if LAST_GOOGLE_MCP_BUILD["gmail"]:
            extras.append("live Gmail")
        if LAST_GOOGLE_MCP_BUILD["calendar"]:
            extras.append("Google Calendar")
        if LAST_GITHUB_MCP_BUILD["github"]:
            extras.append("GitHub")
        extra = ""
        if extras:
            extra = f" You can also check his {' and '.join(extras)}."
        await self.session.generate_reply(
            instructions=(
                "Greet Shubham briefly as Nerva, mention you can pull from "
                f"his SuperMemory knowledge.{extra} Ask how you can help."
            ),
            allow_interruptions=True,
        )


server = AgentServer()


@server.rtc_session(agent_name=VOICE_AGENT_NAME)
async def entrypoint(ctx: JobContext):
    """Named agent so the Call UI can dispatch Shubham_Assistent into the room."""
    session = AgentSession(
        stt=inference.STT(model="deepgram/nova-3", language="en"),
        llm=inference.LLM(
            model="google/gemma-4-31b-it",
        ),
        tts=inference.TTS(
            model="cartesia/sonic-3",
            voice="9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
            language="en",
        ),
        turn_handling=TurnHandlingOptions(
            turn_detection=inference.TurnDetector(),
            preemptive_generation={"enabled": True},
        ),
        vad=inference.VAD(),
    )

    await session.start(
        agent=DefaultAgent(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=ai_coustics.audio_enhancement(
                    model=ai_coustics.EnhancerModel.QUAIL_VF_S,
                ),
            ),
        ),
    )


if __name__ == "__main__":
    cli.run_app(server)
