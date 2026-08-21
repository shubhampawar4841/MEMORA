"""LiveKit CLI entrypoint.

`lk agent dev` looks for ./agent.py or ./src/agent.py under backend/.
The real agent implementation lives in app/voice/agent.py.
"""

from app.voice.agent import server

if __name__ == "__main__":
    from livekit.agents import cli

    cli.run_app(server)
