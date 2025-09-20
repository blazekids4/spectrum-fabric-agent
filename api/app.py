"""Vercel adapter: exposes the FastAPI `app` from backend.app.

This file is intentionally minimal — Vercel will import this module and
use the `app` (or `handler`) callable as the server entrypoint.
"""
from backend.app import app

# Some Vercel runtimes expect `handler` or `app`. Expose both to be safe.
handler = app
