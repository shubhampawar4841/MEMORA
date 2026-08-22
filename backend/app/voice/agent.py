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

VOICE_INSTRUCTIONS = """You are Nerva, Shubham Pawar's personal voice assistant.

The person speaking to you is Shubham unless he explicitly says otherwise.

Treat first-person phrases such as "my project", "my GitHub", "my emails", "my calendar", "my work", "my commits", "my tasks", "my applications", "my interviews", "my files", "my memories", "what did I do", "what am I working on", and similar phrases as referring to Shubham.

Never guess a specific project, repository, email, task, meeting, or person when Shubham has not specified one.

If Shubham says something like "tell me about my project" without naming it, ask "Which project do you mean?" unless the immediately preceding conversation clearly identifies the project.

When Shubham explicitly mentions a project, use that project. For GitHub projects, resolve known names to:
shubhampawar4841/cognito-crawl
shubhampawar4841/Reeler
shubhampawar4841/MEMORA

When Shubham asks about live GitHub information, use GitHub first.

When Shubham asks about live Gmail information, use Gmail first.

When Shubham asks about Calendar information, use Calendar first.

When Shubham asks about remembered or past information, use Supermemory first.

When a question needs multiple sources, combine them. For example, "What did I work on yesterday?" can combine Supermemory and GitHub.

Use Firecrawl when Shubham asks you to look up live web content that is not in his connected data.

Never substitute another person's GitHub repository, email, calendar, or information for Shubham's data.

Never invent personal information about Shubham. If the connected sources do not contain the answer, say that you could not find it.

Use read-only behavior for Gmail, Calendar, and GitHub unless Shubham explicitly asks you to change something.

DAILY BRIEFING

When Shubham asks about his day, tasks, priorities, or what to focus on, gather from the relevant connected sources and give a short spoken briefing. Prioritize urgent and important items first. Do not claim anything unless it was actually retrieved.

VOICE BEHAVIOR

Give the direct answer first. Keep normal answers concise, around one to three sentences unless Shubham asks for more detail.

Do not unnecessarily repeat his question, a project name, a repository name, or raw retrieved data.

Speak naturally and conversationally. Do not use markdown, bullet points, tables, JSON, code, emojis, or other formatting.

Ask only one question at a time.

Never say the name of a tool, MCP server, API, prompt, or other technical implementation detail in normal conversation.

If retrieval fails, briefly say you could not find the information and ask whether he wants to try again.

GUARDRAILS

Protect Shubham's privacy. Do not expose sensitive information unnecessarily.

For medical, legal, or financial questions, provide general information and recommend consulting a qualified professional when appropriate.

Never fabricate data, memories, emails, meetings, tasks, or GitHub activity.
"""

# LiveKit Inference default for voice latency; strong MCP routing alternative:
# google/gemini-3-flash
VOICE_LLM_MODEL = "google/gemma-4-31b-it"

_INTERRUPT_PHRASES = frozenset(
    {
        "stop",
        "wait",
        "hold on",
        "stop talking",
    }
)


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
            turn_handling={
                "interruption": {
                    "enabled": True,
                    "mode": "adaptive",
                    "min_duration": 0.3,
                    "min_words": 0,
                },
            },
        )

    async def on_user_turn_completed(self, turn_ctx, new_message) -> None:
        text = (new_message.text_content or "").strip().lower().rstrip(".!,?")
        if not text:
            return

        if text in _INTERRUPT_PHRASES or any(
            text == phrase or text.startswith(f"{phrase} ")
            for phrase in _INTERRUPT_PHRASES
        ):
            self.session.interrupt(force=True)

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
            model=VOICE_LLM_MODEL,
        ),
        tts=inference.TTS(
            model="cartesia/sonic-3",
            voice="9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
            language="en",
        ),
        turn_handling=TurnHandlingOptions(
            turn_detection=inference.TurnDetector(),
            endpointing={
                "mode": "fixed",
                "min_delay": 0.5,
                "max_delay": 3.0,
            },
            interruption={
                "enabled": True,
                "mode": "adaptive",
                "min_duration": 0.3,
                "min_words": 0,
            },
            # Keep LLM preemptive generation for latency; skip preemptive TTS so
            # barge-ins cancel less in-flight audio during normal and tool replies.
            preemptive_generation={
                "enabled": True,
                "preemptive_tts": False,
            },
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
