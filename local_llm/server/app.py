"""FastAPI application for the local-llm server."""
from __future__ import annotations

from pathlib import Path
from typing import Any
import shutil

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from ..core.inference import RuntimeState
from ..core.paths import ensure_app_dirs
from ..core.registry import (
    ModelEntry,
    get_active_model,
    load_registry,
    save_registry,
    set_active_model,
    register_model,
)
from ..core.storage import download_model, prepare_local_model
from .schemas import ChatRequest, LoadModelRequest, OpenAIChatRequest, UpdateSettingsRequest
from fastapi.staticfiles import StaticFiles


from fastapi.staticfiles import StaticFiles

def build_app(runtime: RuntimeState | None = None) -> FastAPI:
    ensure_app_dirs()
    runtime_state = runtime or RuntimeState()

    app = FastAPI(title="local-llm", version="0.1.0")
    app.mount("/web", StaticFiles(directory="web", html=True), name="web")
    @app.get("/")
    def root():
        return RedirectResponse(url="/web")

    app.state.runtime = runtime_state
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def _startup() -> None:
        registry = load_registry()
        active = get_active_model(registry)
        runtime_state.settings.update(registry.get("settings", {}))

        if runtime_state.llm is None and active and Path(active.local_path).exists():
            runtime_state.load_model(active)


    @app.get("/health")
    def health() -> dict[str, Any]:
        return {
            "ok": True,
            "ready": runtime_state.llm is not None,
            "active_model": runtime_state.active_model.name if runtime_state.active_model else None,
        }


    @app.get("/api/state")
    def state() -> dict[str, Any]:
        return {
            "ready": runtime_state.llm is not None,
            "active_model": runtime_state.active_model.__dict__ if runtime_state.active_model else None,
            "settings": runtime_state.settings,
        }

    @app.get("/models")
    def list_models() -> dict[str, Any]:
        registry = load_registry()
        active = get_active_model(registry)
        return {
            "active_model_id": registry.get("app", {}).get("active_model_id", ""),
            "models": registry.get("models", []),
            "active_model": active.__dict__ if active else None,
        }

    @app.post("/models/load")
    def load_model(payload: LoadModelRequest) -> dict[str, Any]:
        registry = load_registry()

        model = next((item for item in registry.get("models", []) if item["id"] == payload.model_id), None)
        if model is None:
            raise HTTPException(status_code=404, detail="Model not found")

        entry = ModelEntry(**model)

        if not Path(entry.local_path).exists():
            raise HTTPException(status_code=404, detail="Model file missing")

        set_active_model(registry, payload.model_id)
        save_registry(registry)

        runtime_state.load_model(entry)

        return {"ok": True, "active_model_id": payload.model_id}


    @app.post("/models/add")
    async def add_model(
        file: UploadFile = File(None),
        url: str = Form(None),
    ) -> dict[str, Any]:

        registry = load_registry()

        try:
            if file:
                temp_path = Path(f"temp_{file.filename}")

                with open(temp_path, "wb") as f:
                    shutil.copyfileobj(file.file, f)

                copied = prepare_local_model(str(temp_path), "upload_temp")

                entry = register_model(
                    data=registry,
                    name=copied.stem,
                    source_type="upload",
                    source=file.filename,
                    local_path=copied,
                )

                temp_path.unlink(missing_ok=True)

            elif url:
                downloaded = download_model(url, "download_temp")

                entry = register_model(
                    data=registry,
                    name=downloaded.stem,
                    source_type="url",
                    source=url,
                    local_path=downloaded,
                )

            else:
                raise HTTPException(status_code=400, detail="Provide file or URL")

            set_active_model(registry, entry.id)
            save_registry(registry)


            runtime_state.load_model(entry)

            return {
                "ok": True,
                "model": entry.name,
                "id": entry.id,
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


    @app.post("/settings")
    def update_settings(payload: UpdateSettingsRequest) -> dict[str, Any]:
        registry = load_registry()
        settings = registry.setdefault("settings", {})

        for key, value in payload.model_dump(exclude_none=True).items():
            settings[key] = value

        save_registry(registry)
        runtime_state.update_settings(**payload.model_dump(exclude_none=True))

        return {"ok": True, "settings": runtime_state.settings}

    @app.post("/chat")
    def chat(payload: ChatRequest) -> dict[str, Any]:
        if runtime_state.llm is None:
            raise HTTPException(status_code=400, detail="No model loaded")

        text = runtime_state.generate(
            payload.message,
            temperature=payload.temperature,
            max_tokens=payload.max_tokens,
        )

        return {"response": text}

    @app.post("/v1/chat/completions")
    def openai_chat(payload: OpenAIChatRequest) -> JSONResponse:
        if runtime_state.llm is None:
            raise HTTPException(status_code=400, detail="No model loaded")

        text = runtime_state.generate_chat(
            [msg.model_dump() for msg in payload.messages],
            temperature=payload.temperature,
            max_tokens=payload.max_tokens,
        )

        response = {
            "id": "chatcmpl-local-001",
            "object": "chat.completion",
            "created": 0,
            "model": payload.model or (
                runtime_state.active_model.name if runtime_state.active_model else "local-llm"
            ),
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": text},
                    "finish_reason": "stop",
                }
            ],
        }

        return JSONResponse(response)

    return app


app = build_app()