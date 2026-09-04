"""FastAPI application factory for the local Tieny server and Web UI."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from tieny.core.config import ConfigStore
from tieny.core.errors import TienyError
from tieny.core.logging import setup_logging
from tieny.core.version import __version__
from tieny.server import state
from tieny.server.routes import chat, compat, models, system

config = ConfigStore().load()
setup_logging(config.log_level)
logger = logging.getLogger(__name__)

WEB_ROOT = Path(__file__).resolve().parent.parent / "webui" / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Tieny server startup")
    try:
        yield
    finally:
        if state.runtime.loaded_model is not None:
            logger.info("Server shutdown is unloading the active model")
            state.runtime.unload()
        logger.info("Tieny server shutdown complete")


def create_app() -> FastAPI:
    app = FastAPI(title="Tieny", version=__version__, lifespan=lifespan)

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        logger.debug("HTTP %s %s", request.method, request.url.path)
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("Unhandled request failure: %s %s", request.method, request.url.path)
            raise
        logger.debug("HTTP %s %s -> %s", request.method, request.url.path, response.status_code)
        return response

    @app.exception_handler(TienyError)
    async def tieny_error_handler(_: Request, exc: TienyError):
        logger.warning("Tieny request error: %s", exc)
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(ValueError)
    async def value_error_handler(_: Request, exc: ValueError):
        logger.warning("Request validation error: %s", exc)
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    app.include_router(models.router)
    app.include_router(chat.router)
    app.include_router(system.router)
    app.include_router(compat.router)

    app.mount("/static", StaticFiles(directory=WEB_ROOT), name="static")

    @app.get("/", include_in_schema=False)
    def webui() -> FileResponse:
        return FileResponse(WEB_ROOT / "index.html")

    logger.info("Tieny FastAPI application created")
    return app


app = create_app()
