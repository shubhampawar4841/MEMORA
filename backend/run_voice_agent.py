"""Run the Nerva LiveKit voice agent worker.

Usage (from backend/):
  python run_voice_agent.py dev
  python run_voice_agent.py start
"""

from app.voice.agent import server
from livekit.agents import cli

if __name__ == "__main__":
    cli.run_app(server)
