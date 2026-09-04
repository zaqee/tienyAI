"""Typer command-line interface for Tieny v0.2.0."""

from __future__ import annotations

import logging
import threading
import time
import webbrowser
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from tieny.cli import client
from tieny.core.config import ConfigStore
from tieny.core.errors import TienyError
from tieny.core.logging import setup_logging
from tieny.core.version import __version__
from tieny.install import Installer
from tieny.models.entity import ModelRecord
from tieny.models.service import ModelService

app = typer.Typer(
    name="tieny",
    help="Local AI hosting with one model registry, Python API, CLI, and Web UI.",
    no_args_is_help=True,
    add_completion=True,
)
console = Console()
logger = logging.getLogger(__name__)
models = ModelService()


def _boot_logging() -> None:
    setup_logging(ConfigStore().load().log_level)


def _human_size(size: int | None) -> str:
    if size is None:
        return "missing"
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return str(size)


def _direct_row(model: ModelRecord, loaded_id: str | None) -> dict:
    try:
        size = Path(model.path).stat().st_size
    except OSError:
        size = None
    return {
        **model.to_dict(),
        "loaded": model.id == loaded_id,
        "size_bytes": size,
    }


def _loaded_id_from_server() -> str | None:
    try:
        health = client.request("GET", "/api/health", timeout=0.4)
        loaded = health.get("loaded_model") if isinstance(health, dict) else None
        return loaded.get("id") if loaded else None
    except TienyError:
        return None


@app.callback(invoke_without_command=True)
def main(
    version: bool = typer.Option(
        False,
        "--version",
        help="Show the installed Tieny version and exit.",
        is_eager=True,
    ),
) -> None:
    """Tieny's generic model commands work across modalities as support is added."""
    _boot_logging()

    if version:
        console.print(f"Tieny {__version__}")
        raise typer.Exit()


@app.command()
def install() -> None:
    """Install the dependencies required by the current basic Tieny runtime."""
    logger.info("CLI command: install")
    try:
        Installer().install()
        console.print("[bold green]Tieny dependencies are ready.[/bold green]")
    except TienyError as exc:
        console.print(f"[bold red]Install failed:[/bold red] {exc}")
        raise typer.Exit(1)


@app.command()
def start(
    no_browser: bool = typer.Option(
        False, "--no-browser", help="Start the local server without opening the Web UI."
    ),
) -> None:
    """Start the persistent local API/runtime process and Web UI."""
    logger.info("CLI command: start no_browser=%s", no_browser)
    config = ConfigStore().load()
    url = f"http://{config.host}:{config.port}"

    if not no_browser:
        def open_later() -> None:
            time.sleep(0.8)
            logger.info("Opening Web UI at %s", url)
            webbrowser.open(url)

        threading.Thread(target=open_later, daemon=True).start()

    console.print(f"[bold]Tieny[/bold] starting at [cyan]{url}[/cyan]")
    import uvicorn

    uvicorn.run("tieny.server.app:app", host=config.host, port=config.port, log_level="info")


@app.command("add")
def add_model(path: str = typer.Argument(..., help="Path to an existing model file.")) -> None:
    """Register a model by path. The model file is never copied."""
    logger.info("CLI command: add path=%s", path)
    try:
        if client.is_running():
            result = client.request("POST", "/api/models/add", payload={"path": path})
            model_name, model_id, model_path = result["name"], result["id"], result["path"]
        else:
            model = models.add(path)
            model_name, model_id, model_path = model.name, model.id, model.path
        console.print(
            f"[green]Added[/green] {model_name}  [dim]id={model_id} path={model_path}[/dim]"
        )
    except TienyError as exc:
        console.print(f"[bold red]Add failed:[/bold red] {exc}")
        raise typer.Exit(1)


@app.command("list")
def list_models() -> None:
    """List registered models and useful registry/runtime information."""
    logger.info("CLI command: list")
    loaded_id = _loaded_id_from_server()
    records = models.list()
    table = Table(title="Tieny models", show_lines=False)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="bold")
    table.add_column("Type")
    table.add_column("Format")
    table.add_column("Runtime")
    table.add_column("Size", justify="right")
    table.add_column("Loaded")
    table.add_column("Path", overflow="fold")

    for model in records:
        row = _direct_row(model, loaded_id)
        table.add_row(
            model.id,
            model.name,
            model.type.upper(),
            model.format,
            model.runtime,
            _human_size(row["size_bytes"]),
            "yes" if row["loaded"] else "",
            model.path,
        )
    console.print(table)


@app.command("load")
def load_model(target: str = typer.Argument(..., help="Model ID or name.")) -> None:
    """Load a model into the running Tieny server process."""
    logger.info("CLI command: load target=%s", target)
    try:
        result = client.request("POST", f"/api/models/load/{client.target_path(target)}")
        console.print(f"[green]Loaded[/green] {result['name']} [dim]({result['id']})[/dim]")
    except TienyError as exc:
        console.print(f"[bold red]Load failed:[/bold red] {exc}")
        raise typer.Exit(1)


@app.command("unload")
def unload_model(
    target: Optional[str] = typer.Argument(None, help="Optional loaded model ID or name."),
) -> None:
    """Unload the current model, optionally verifying it by ID or name."""
    logger.info("CLI command: unload target=%s", target)
    try:
        result = client.request("POST", "/api/models/unload", query={"target": target} if target else None)
        item = result.get("unloaded") if isinstance(result, dict) else None
        if item:
            console.print(f"[green]Unloaded[/green] {item['name']} [dim]({item['id']})[/dim]")
        else:
            console.print("No model was loaded.")
    except TienyError as exc:
        console.print(f"[bold red]Unload failed:[/bold red] {exc}")
        raise typer.Exit(1)


@app.command("remove")
def remove_model(
    target: str = typer.Argument(..., help="Model ID or name."),
    delete_file: bool = typer.Option(
        False,
        "--del",
        help="Also permanently delete the original model file from disk.",
    ),
) -> None:
    """Remove a registry entry; --del also deletes the original model file."""
    logger.warning("CLI command: remove target=%s delete_file=%s", target, delete_file)
    try:
        model = models.resolve(target)
        if delete_file:
            confirmed = typer.confirm(
                f"Delete the ORIGINAL model file too?\n{model.path}\nThis cannot be undone",
                default=False,
            )
            if not confirmed:
                console.print("Cancelled.")
                raise typer.Exit()

        if client.is_running():
            result = client.request(
                "DELETE",
                f"/api/models/{client.target_path(model.id)}",
                query={"delete_file": str(delete_file).lower()},
            )
            removed = result["removed"]
        else:
            removed = models.remove(model.id, delete_file=delete_file).to_dict()

        verb = "Deleted file and removed" if delete_file else "Removed"
        console.print(f"[green]{verb}[/green] {removed['name']} [dim]({removed['id']})[/dim]")
    except TienyError as exc:
        console.print(f"[bold red]Remove failed:[/bold red] {exc}")
        raise typer.Exit(1)


@app.command("name")
def name_model(
    target: str = typer.Argument(..., help="Model ID or current name."),
    new_name: Optional[str] = typer.Argument(None, help="New unique model name."),
    remove_name: bool = typer.Option(
        False,
        "--remove",
        help="Reset the name to the filename-derived default.",
    ),
) -> None:
    """Change a model's name, or reset it with --remove."""
    logger.info(
        "CLI command: name target=%s new_name=%s remove=%s",
        target,
        new_name,
        remove_name,
    )
    if remove_name and new_name is not None:
        console.print("[red]Use either a new name or --remove, not both.[/red]")
        raise typer.Exit(2)
    if not remove_name and new_name is None:
        console.print("[red]Provide a new name or use --remove.[/red]")
        raise typer.Exit(2)

    try:
        if client.is_running():
            result = client.request(
                "POST",
                f"/api/models/{client.target_path(target)}/name",
                payload={"name": new_name, "remove": remove_name},
            )
            model_name = result["name"]
            model_id = result["id"]
        else:
            model = models.reset_name(target) if remove_name else models.rename(target, new_name or "")
            model_name, model_id = model.name, model.id
        console.print(f"[green]Name set[/green] {model_name} [dim]({model_id})[/dim]")
    except TienyError as exc:
        console.print(f"[bold red]Name failed:[/bold red] {exc}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
