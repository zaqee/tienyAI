"""FastAPI application factory for the local Tieny server and Web UI."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
import os

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from tieny.core.config import ConfigStore
from tieny.core.errors import TienyError
from tieny.core.logging import setup_logging
from tieny.core.version import __version__
from tieny.server import state
from tieny.server.routes import chat, compat, models, system
from tieny.core.state import StateStore

config = ConfigStore().load()
setup_logging(config.log_level)
logger = logging.getLogger(__name__)

WEB_ROOT = Path(__file__).resolve().parent.parent / "webui" / "static"


def _resolve_startup_preload() -> str | None:
    """Resolve which model, if any, should be loaded during server startup."""
    startup_request = os.getenv("TIENY_START_PRELOAD")

    logger.debug(
        "Resolving startup preload request=%s auto=%s configured_model=%s",
        startup_request,
        config.preload.auto,
        config.preload.model,
    )

    # No explicit --preload and automatic preload is disabled.
    if startup_request is None and not config.preload.auto:
        logger.debug("Startup preload is disabled")
        return None

    # An explicit model passed through `tieny start --preload MODEL`
    # always wins over persistent configuration.
    if startup_request not in {None, "__default__"}:
        logger.debug(
            "Using explicit startup preload model id=%s",
            startup_request,
        )
        return startup_request

    # Next priority is the configured preload model.
    if config.preload.model is not None:
        logger.debug(
            "Using configured preload model id=%s",
            config.preload.model,
        )
        return config.preload.model

    # No configured model means "last successfully loaded model".
    last_used = StateStore().load().last_used_model

    if last_used is not None:
        logger.debug(
            "Using last successfully loaded model id=%s",
            last_used,
        )
        return last_used

    logger.warning(
        "Preload was requested but no configured or last-used model exists"
    )
    return None


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Tieny server startup")

    preload_target = _resolve_startup_preload()

    if preload_target is not None:
        try:
            logger.info(
                "Preloading model during server startup: %s",
                preload_target,
            )

            loaded = state.runtime.load(preload_target)

            logger.info(
                "Startup preload complete id=%s name=%s",
                loaded.id,
                loaded.name,
            )

        except TienyError as exc:
            # A failed preload should not prevent the server/Web UI from
            # starting. The user can still load another model normally.
            logger.error(
                "Startup preload failed for '%s': %s",
                preload_target,
                exc,
            )

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
