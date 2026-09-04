"""Health, logs, and local-desktop helper routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter

from tieny.core.config import ConfigStore
from tieny.core.errors import TienyError
from tieny.core.logging import clear_recent_logs, recent_logs
from tieny.server import state

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health")
def health() -> dict:
    loaded = state.runtime.loaded_model
    return {
        "ok": True,
        "loaded_model": loaded.to_dict() if loaded else None,
    }


@router.get("/logs")
def logs(limit: int = 500, level: str = "ALL") -> dict:
    return {"logs": recent_logs(limit=limit, level=level)}


@router.post("/logs/clear")
def clear_logs() -> dict:
    logger.info("Developer console cleared in-memory logs")
    clear_recent_logs()
    return {"ok": True}


@router.get("/config")
def config() -> dict:
    cfg = ConfigStore().load()
    return {
        "host": cfg.host,
        "port": cfg.port,
        "log_level": cfg.log_level,
        "n_ctx": cfg.n_ctx,
        "n_gpu_layers": cfg.n_gpu_layers,
    }


@router.post("/system/select-model-file")
def select_model_file() -> dict:
    """Open the host OS file picker and return the real local path.

    A browser upload control cannot reveal a real absolute filesystem path by
    design. Tieny runs locally, so asking the Python host process to open the
    native picker preserves the user's file in place and avoids duplicate GGUFs.
    """
    logger.info("Opening native model file picker")
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        selected = filedialog.askopenfilename(
            title="Select a Tieny model",
            filetypes=[("GGUF models", "*.gguf"), ("All files", "*.*")],
        )
        root.destroy()
    except Exception as exc:
        logger.exception("Native file picker failed")
        raise TienyError(
            "Could not open the native file picker on this host. "
            "Use the CLI 'tieny add <path>' instead."
        ) from exc

    if not selected:
        logger.info("Native model file picker cancelled")
        return {"path": None}
    logger.info("Native model file picker selected %s", selected)
    return {"path": selected}
