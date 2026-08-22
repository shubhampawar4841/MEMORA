"""Vercel serverless entry — Mangum wraps the slim Nerva app."""

from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from mangum import Mangum

from app.vercel_app import app

handler = Mangum(app, lifespan="off")
