"""Slim FastAPI app for Vercel — Telegram + health only (no local RAG / Chroma)."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS
from app.routers.health import router as health_router
from app.routers.telegram import router as telegram_router

app = FastAPI(title="Nerva API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(telegram_router)
