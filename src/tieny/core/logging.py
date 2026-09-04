"""Central logging configuration and an in-memory feed for Developer Mode."""

from __future__ import annotations

import logging
from collections import deque
from logging.handlers import RotatingFileHandler
from threading import Lock

from tieny.core.paths import ensure_data_dirs, log_file_path

_LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class MemoryLogHandler(logging.Handler):
    """Keep recent formatted log lines for the Web UI developer console."""

    def __init__(self, capacity: int = 2000) -> None:
        super().__init__(level=logging.DEBUG)
        self.lines: deque[dict[str, str]] = deque(maxlen=capacity)
        self._lock = Lock()

    def emit(self, record: logging.LogRecord) -> None:
        item = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "formatted": self.format(record),
        }
        with self._lock:
            self.lines.append(item)

    def recent(self, limit: int = 500, level: str | None = None) -> list[dict[str, str]]:
        with self._lock:
            items = list(self.lines)
        if level and level.upper() != "ALL":
            items = [item for item in items if item["level"] == level.upper()]
        return items[-max(1, min(limit, 2000)) :]

    def clear(self) -> None:
        with self._lock:
            self.lines.clear()


_memory_handler = MemoryLogHandler()
_configured = False


def setup_logging(level: str = "DEBUG") -> None:
    """Configure console, rotating file, and in-memory logging once per process."""
    global _configured
    if _configured:
        logging.getLogger().setLevel(getattr(logging, level.upper(), logging.DEBUG))
        return

    ensure_data_dirs()
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.DEBUG))

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        log_file_path(), maxBytes=2_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    _memory_handler.setFormatter(formatter)

    root.addHandler(console)
    root.addHandler(file_handler)
    root.addHandler(_memory_handler)
    _configured = True
    logging.getLogger(__name__).debug("Central logging configured")


def recent_logs(limit: int = 500, level: str | None = None) -> list[dict[str, str]]:
    return _memory_handler.recent(limit=limit, level=level)


def clear_recent_logs() -> None:
    _memory_handler.clear()
