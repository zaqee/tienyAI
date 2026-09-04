"""Typer command-line interface for Tieny v0.3.0."""

from __future__ import annotations

import logging
import threading
import time
import webbrowser
from pathlib import Path
from typing import Optional
import os

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

# Sub-command group for persistent configuration.
# Future config areas like runtime, GPU, wheel, etc. can live under this.
config_app = typer.Typer(
    name="config",
    help="View and change persistent Tieny settings.",
    no_args_is_help=True,
)

app.add_typer(config_app, name="config")

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


def _parse_bool(value: str, *, option: str) -> bool:
    """Parse common CLI boolean values into a real bool."""
    normalized = value.strip().lower()

    if normalized in {"true", "1", "yes", "on"}:
        return True
    if normalized in {"false", "0", "no", "off"}:
        return False

    logger.warning("Invalid boolean value for %s: %s", option, value)
    raise TienyError(f"{option} must be true or false.")


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
        model: Optional[str] = typer.Argument(
            None,
            help="Optional model ID or name to preload. Requires --preload.",
        ),
        no_ui: bool = typer.Option(
            False,
            "--no-ui",
            help="Start the local server without opening the Web UI.",
        ),
        preload: bool = typer.Option(
            False,
            "--preload",
            help="Preload a model when Tieny starts.",
        ),
) -> None:
    """Start the persistent local API/runtime process and Web UI."""
    logger.info(
        "CLI command: start no_ui=%s preload=%s model=%s",
        no_ui,
        preload,
        model,
    )

    if model is not None and not preload:
        logger.warning(
            "Rejected startup model '%s' because --preload was not supplied",
            model,
        )
        console.print(
            "[red]A startup model can only be used with --preload.[/red]"
        )
        raise typer.Exit(2)

    config = ConfigStore().load()

    if preload:
        if model is not None:
            try:
                resolved = models.resolve(model)
            except TienyError as exc:
                logger.warning(
                    "Could not resolve explicit preload model '%s': %s",
                    model,
                    exc,
                )
                console.print(
                    f"[bold red]Preload failed:[/bold red] {exc}"
                )
                raise typer.Exit(1)

            os.environ["TIENY_START_PRELOAD"] = resolved.id

            logger.debug(
                "Explicit startup preload resolved '%s' -> id=%s name=%s",
                model,
                resolved.id,
                resolved.name,
            )

            console.print(
                f"[cyan]Preload:[/cyan] "
                f"{resolved.name} [dim]({resolved.id})[/dim]"
            )
        else:
            os.environ["TIENY_START_PRELOAD"] = "__default__"
            logger.debug(
                "Startup preload requested using configured/default model"
            )
    else:
        os.environ.pop("TIENY_START_PRELOAD", None)

    url = f"http://{config.host}:{config.port}"

    # CLI --no-ui always overrides config.
    # Otherwise, follow the persistent ui.auto_open setting.
    should_open_ui = config.ui.auto_open and not no_ui

    logger.debug(
        "UI startup decision: config_auto_open=%s cli_no_ui=%s should_open=%s",
        config.ui.auto_open,
        no_ui,
        should_open_ui,
    )

    if should_open_ui:
        def open_later() -> None:
            time.sleep(0.8)
            logger.info("Opening Web UI at %s", url)
            webbrowser.open(url)

        threading.Thread(target=open_later, daemon=True).start()
    else:
        logger.info("Web UI auto-open disabled for this startup")

    console.print(f"[bold]Tieny[/bold] starting at [cyan]{url}[/cyan]")

    import uvicorn

    uvicorn.run(
        "tieny.server.app:app",
        host=config.host,
        port=config.port,
        log_level="info",
    )


@config_app.command("preload")
def config_preload(
        set_model: Optional[str] = typer.Option(
            None,
            "--set",
            metavar="MODEL",
            help="Set the default preload model by ID or name.",
        ),
        reset: bool = typer.Option(
            False,
            "--reset",
            help="Reset the preload model to the last successfully loaded model.",
        ),
        auto: Optional[str] = typer.Option(
            None,
            "--auto",
            metavar="BOOL",
            help="Automatically preload on start: true or false.",
        ),
) -> None:
    """View or change model preload settings."""
    logger.info(
        "CLI command: config preload set=%s reset=%s auto=%s",
        set_model,
        reset,
        auto,
    )

    # --set and --reset describe two conflicting operations on the same
    # setting, so accepting both would make the result ambiguous.
    if set_model is not None and reset:
        logger.warning("Rejected config preload: --set and --reset used together")
        console.print("[red]Use either --set or --reset, not both.[/red]")
        raise typer.Exit(2)

    store = ConfigStore()
    config = store.load()
    changed = False

    try:
        if set_model is not None:
            # Resolve before saving so config can never point at a model that
            # does not exist. Store the stable ID so renaming remains safe.
            model = models.resolve(set_model)
            config.preload.model = model.id
            changed = True

            logger.debug(
                "Resolved preload target '%s' -> id=%s name=%s",
                set_model,
                model.id,
                model.name,
            )

            console.print(
                f"[green]Default preload model set[/green] "
                f"{model.name} [dim]({model.id})[/dim]"
            )

        if reset:
            # None deliberately means "follow the last successfully loaded
            # model" rather than disabling preload entirely.
            previous = config.preload.model
            config.preload.model = None
            changed = True

            logger.debug(
                "Reset preload model from %s to last-used behaviour",
                previous,
            )

            console.print(
                "[green]Default preload model reset.[/green] "
                "Tieny will use the last successfully loaded model."
            )
        auto_value: bool | None = None

        if auto is not None:
            normalized = auto.strip().lower()

            if normalized in {"true", "1", "yes", "on"}:
                auto_value = True
            elif normalized in {"false", "0", "no", "off"}:
                auto_value = False
            else:
                logger.warning("Invalid preload --auto value: %s", auto)
                console.print(
                    "[red]--auto must be true or false.[/red]"
                )
                raise typer.Exit(2)

        if auto_value is not None:
            previous = config.preload.auto
            config.preload.auto = auto_value
            changed = True

            logger.debug(
                "Changed automatic preload from %s to %s",
                previous,
                auto_value,
            )

            state = "enabled" if auto_value else "disabled"
            console.print(f"[green]Automatic preload {state}.[/green]")

        if changed:
            store.save(config)
            logger.info(
                "Saved preload config model=%s auto=%s",
                config.preload.model,
                config.preload.auto,
            )
            return

        # No options means this command acts as a status/read command.
        logger.debug(
            "Displaying preload config model=%s auto=%s",
            config.preload.model,
            config.preload.auto,
        )

        table = Table(title="Preload configuration", show_header=False)
        table.add_column("Setting", style="bold")
        table.add_column("Value")

        if config.preload.model is None:
            model_display = "last used"
        else:
            try:
                model = models.resolve(config.preload.model)
                model_display = f"{model.name} ({model.id})"
            except TienyError:
                # Config may reference a model that was removed after it was
                # selected. Don't make viewing config itself fail.
                logger.warning(
                    "Configured preload model '%s' no longer exists",
                    config.preload.model,
                )
                model_display = f"{config.preload.model} [missing]"

        table.add_row("Default model", model_display)
        table.add_row(
            "Auto preload",
            "enabled" if config.preload.auto else "disabled",
        )

        console.print(table)

    except TienyError as exc:
        logger.warning("Preload configuration failed: %s", exc)
        console.print(f"[bold red]Config failed:[/bold red] {exc}")
        raise typer.Exit(1)


@config_app.command("no-ui")
def config_no_ui(
        auto: Optional[str] = typer.Option(
            None,
            "--auto",
            metavar="BOOL",
            help="Automatically start Tieny without opening the Web UI.",
        ),
) -> None:
    """View or change automatic no-UI startup behaviour."""
    logger.info("CLI command: config no-ui auto=%s", auto)

    store = ConfigStore()
    config = store.load()

    try:
        if auto is not None:
            no_ui_enabled = _parse_bool(auto, option="--auto")

            previous = config.ui.auto_open
            config.ui.auto_open = not no_ui_enabled

            logger.debug(
                "Changed UI auto-open from %s to %s",
                previous,
                config.ui.auto_open,
            )

            store.save(config)

            state = "enabled" if no_ui_enabled else "disabled"
            console.print(
                f"[green]Automatic no-UI startup {state}.[/green]"
            )
            return

        # No options means: show current setting.
        no_ui_enabled = not config.ui.auto_open

        logger.debug(
            "Displaying no-ui config auto=%s",
            no_ui_enabled,
        )

        table = Table(title="No-UI configuration", show_header=False)
        table.add_column("Setting", style="bold")
        table.add_column("Value")

        table.add_row(
            "Automatic no-UI",
            "enabled" if no_ui_enabled else "disabled",
        )

        console.print(table)

    except TienyError as exc:
        logger.warning("No-UI configuration failed: %s", exc)
        console.print(f"[bold red]Config failed:[/bold red] {exc}")
        raise typer.Exit(1)


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
