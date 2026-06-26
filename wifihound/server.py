"""FastAPI application factory and static-file serving."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from wifihound import __version__
from wifihound.api import router

WEB_DIR = Path(__file__).parent / "web"


def create_app() -> FastAPI:
    app = FastAPI(title="WiFi-Hound", version=__version__)
    app.include_router(router)

    app.mount(
        "/static",
        StaticFiles(directory=str(WEB_DIR / "static")),
        name="static",
    )

    @app.get("/")
    def index():
        return FileResponse(str(WEB_DIR / "index.html"))

    @app.get("/health")
    def health():
        return {"status": "ok", "version": __version__}

    return app


app = create_app()
