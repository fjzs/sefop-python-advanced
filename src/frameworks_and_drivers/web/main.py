"""FastAPI application instance for the web delivery mechanism.

WHY THIS EXISTS:
    This is the module Uvicorn points at (see the Dockerfile's CMD and the
    README's "run the web app" instructions): `uvicorn
    frameworks_and_drivers.web.main:app`. Its only job is to build the
    FastAPI app, register the API routes, and serve the static frontend —
    it holds no business logic of its own.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from frameworks_and_drivers.web.routes import router

app = FastAPI(title="SEFOP Knapsack Solver")
app.include_router(router)

# Registered after the API routes: Starlette matches routes in registration
# order, so POST /solve and GET /health are matched first, and only requests
# for anything else (e.g. "/", "/app.js") fall through to the static files
# below. html=True makes "/" serve static/index.html automatically.
_STATIC_DIR = Path(__file__).parent / "static"
app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="static")
