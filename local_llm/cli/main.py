"""CLI entrypoint for local-llm."""
from __future__ import annotations

import time
import webbrowser
from pathlib import Path
from threading import Thread
from urllib.request import urlopen

import typer
import uvicorn
from rich.console import Console
from rich.table import Table
from local_llm.core.registry import repair_registry
from ..core.inference import RuntimeState
from ..core.paths import ensure_app_dirs
from ..core.registry import (
    ModelEntry,
    get_active_model,
    load_config,
    load_registry,
    register_model,
    save_registry,
    set_active_model,
)
from ..core.storage import download_model, is_url, prepare_local_model
from ..server.app import build_app

app = typer.Typer(add_completion=False, help="Local-first LLM server.")
console = Console()


def _wait_for_server(host: str, port: int, timeout: float = 30.0) -> None:
    url = f"http://{host}:{port}/health"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(0.25)
    raise RuntimeError("Server did not become ready in time.")


def _show_models_table(registry: dict) -> None:
    table = Table(title="Registered models")
    table.add_column("ID", style="cyan")
    table.add_column("Alias", style="green")
    table.add_column("Name", style="white")
    table.add_column("Source", style="magenta")
    table.add_column("Path", style="green")
    table.add_column("Active", style="yellow")

    active_id = registry.get("app", {}).get("active_model_id", "")

    for model in registry.get("models", []):
        alias = model.get("alias")
        display_alias = alias if alias not in (None, "") else model["name"]

        table.add_row(
            model["id"],
            display_alias,
            model["name"],
            f'{model["source_type"]}: {model["source"]}',
            model["local_path"],
            "yes" if model["id"] == active_id else "",
        )

    console.print(table)


def _choose_existing_model(registry: dict) -> str | None:
    models = registry.get("models", [])
    if not models:
        console.print("[yellow]No models are registered yet.[/yellow]")
        return None

    _show_models_table(registry)
    choice = typer.prompt("Enter a model ID to use").strip()
    for model in models:
        if model["id"] == choice:
            return choice

    console.print("[red]That model ID was not found.[/red]")
    return None


def _add_source_to_registry(source_text: str) -> ModelEntry:
    """Add a path or URL to the registry and return the new entry."""
    registry = load_registry()
    alias = typer.prompt("Give this model a name (or leave empty)", default="").strip()
    alias = alias or None
    if is_url(source_text):
        temp_id = f"download_{len(registry.get('models', [])) + 1:04d}"
        downloaded = download_model(source_text, temp_id)
        entry = register_model(
            data=registry,
            name=downloaded.stem,
            source_type="url",
            source=source_text,
            local_path=downloaded,
            alias=alias,
        )
    else:
        local_source = Path(source_text).expanduser()
        if not local_source.exists():
            raise FileNotFoundError(f"Model path does not exist: {local_source}")
        temp_id = f"local_{len(registry.get('models', [])) + 1:04d}"
        copied = prepare_local_model(str(local_source), temp_id)
        entry = register_model(
            data=registry,
            name=copied.stem,
            source_type="path",
            source=str(local_source),
            local_path=copied,
            alias=alias,
        )

    # Move the copied/downloaded model into a stable folder named by the final ID.
    current = Path(entry.local_path)
    final_dir = current.parent.parent / entry.id
    final_dir.mkdir(parents=True, exist_ok=True)
    final_path = final_dir / current.name
    if final_path != current:
        current.rename(final_path)
    registry["models"][-1]["local_path"] = str(final_path)
    save_registry(registry)
    return entry


@app.command()
def start(
    host: str = typer.Option("127.0.0.1", help="Server host."),
    port: int = typer.Option(8000, help="Server port."),
    open_browser: bool = typer.Option(True, help="Open the settings page automatically."),
) -> None:
    """Start the local server."""
    ensure_app_dirs()
    config = load_config()
    if config.get("server"):
        host = config["server"].get("host", host)
        port = int(config["server"].get("port", port))
    open_browser = bool(config.get("ui", {}).get("open_browser", open_browser))

    registry = load_registry()
    active = get_active_model(registry)

    if active is None or not Path(active.local_path).exists():
        console.print("[bold]No active model found.[/bold]")
        console.print("Enter a model path, a download URL, or type [bold]list[/bold].")

        source_text = ""
        while True:
            raw = typer.prompt("Model path / URL / list").strip()
            if not raw:
                continue
            if raw.lower() == "list":
                choice = _choose_existing_model(registry)
                if choice:
                    set_active_model(registry, choice)
                    save_registry(registry)
                    break
                continue
            source_text = raw
            break

        if source_text:
            entry = _add_source_to_registry(source_text)
            set_active_model(registry, entry.id)
            save_registry(registry)

    registry = load_registry()
    registry = repair_registry(registry)
    active = get_active_model(registry)

    runtime = RuntimeState()
    runtime.settings.update(registry.get("settings", {}))
    if active and Path(active.local_path).exists():
        console.print(f"[green]Loading model:[/green] {active.name}")
        runtime.load_model(active)
    else:
        console.print("[yellow]The server will start, but no valid model is loaded.[/yellow]")

    app_obj = build_app(runtime)
    config = uvicorn.Config(app_obj, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)

    thread = Thread(target=server.run, daemon=True)
    thread.start()

    _wait_for_server(host, port)

    if open_browser:
        webbrowser.open(f"http://{host}:{port}/")

    console.print(f"[green]local-llm is running on http://{host}:{port}[/green]")
    console.print("Press Ctrl+C to stop.")

    try:
        while thread.is_alive():
            time.sleep(0.5)
    except KeyboardInterrupt:
        console.print("\n[bold]Shutting down...[/bold]")
        server.should_exit = True
        thread.join(timeout=5)


@app.command()
def models() -> None:
    """Print the registry of installed models."""
    registry = load_registry()
    _show_models_table(registry)


@app.command()
def add(source: str) -> None:
    """Add a model from a local path or direct URL to the registry."""
    entry = _add_source_to_registry(source)
    console.print(f"[green]Added model[/green] {entry.id}")
    
@app.command()

@app.command()
def use(model_id: str):
    """Set active model by ID or alias."""
    registry = load_registry()

    model = next(
        (m for m in registry.get("models", [])
         if m["id"] == model_id or m.get("alias") == model_id),
        None
    )

    if not model:
        console.print("[red]Model not found[/red]")
        raise typer.Exit(1)

    set_active_model(registry, model["id"])

    save_registry(registry)

    console.print(f"[green]Active model → {model.get('alias') or model['id']}[/green]")

@app.command()
def alias(model_id: str, name: str):
    """Set or update a model alias."""
    registry = load_registry()

    updated = False

    for i, m in enumerate(registry.get("models", [])):
        if m["id"] == model_id or m.get("alias") == model_id:
            registry["models"][i]["alias"] = name 
            updated = True
            break

    if not updated:
        console.print("[red]Model not found[/red]")
        raise typer.Exit(1)

    save_registry(registry)

    console.print(f"[green]Alias set → {name}[/green]")
if __name__ == "__main__":
    app()
@app.command()
def unalias(model_id: str):
    """Remove a model alias."""
    registry = load_registry()

    model = next(
        (m for m in registry.get("models", [])
         if m["id"] == model_id or m.get("alias") == model_id),
        None
    )

    if not model:
        console.print("[red]Model not found[/red]")
        raise typer.Exit(1)

    model["alias"] = None
    save_registry(registry)

    console.print("[yellow]Alias removed[/yellow]")