"""Utilities for copying or downloading model files into managed storage."""
from __future__ import annotations

import mimetypes
import shutil
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .paths import MODELS_DIR, ensure_app_dirs
from rich.progress import Progress, BarColumn, DownloadColumn, TransferSpeedColumn, TimeRemainingColumn


def is_url(text: str) -> bool:
    return text.startswith("http://") or text.startswith("https://")


def normalize_name(text: str) -> str:
    # Keep the name readable for humans, but safe for file systems.
    cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in text.strip())
    return cleaned.strip("._") or "model"


def filename_from_url(url: str, fallback: str = "downloaded-model.gguf") -> str:
    parsed = urlparse(url)
    name = Path(parsed.path).name
    if name:
        return name
    return fallback


def prepare_local_model(source_path: str, model_id: str) -> Path:
    """Copy a local model into the managed models directory."""
    ensure_app_dirs()
    src = Path(source_path).expanduser().resolve()
    if not src.exists():
        raise FileNotFoundError(f"Model path does not exist: {src}")
    if not src.is_file():
        raise ValueError(f"Model path is not a file: {src}")

    target_dir = MODELS_DIR / model_id
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / src.name
    shutil.copy2(src, target)
    return target


def download_model(url: str, model_id: str):
    from pathlib import Path

    models_dir = Path.home() / ".local-llm" / "models"
    target_dir = models_dir / model_id
    target_dir.mkdir(parents=True, exist_ok=True)

    filename = url.split("/")[-1]
    file_path = target_dir / filename

    with urlopen(url) as response:
        total = int(response.getheader("Content-Length", 0))

        with open(file_path, "wb") as f, Progress(
            "[progress.description]{task.description}",
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
        ) as progress:

            task = progress.add_task(f"Downloading {filename}...", total=total)

            while True:
                chunk = response.read(1024 * 64)  # 64KB chunks
                if not chunk:
                    break
                f.write(chunk)
                progress.update(task, advance=len(chunk))

    return file_path