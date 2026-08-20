"""Shared Groq client for RAG generation and the Firecrawl agent."""

from groq import Groq

from app.config import GROQ_API_KEY

if not GROQ_API_KEY:
    raise RuntimeError(
        "GROQ_API_KEY is missing. "
        "Create a .env file in the backend directory."
    )

client = Groq(api_key=GROQ_API_KEY)
