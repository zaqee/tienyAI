"""Tiny standard-library HTTP client used by CLI commands that need server state."""

from __future__ import annotations

import json
import logging
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from tieny.core.config import ConfigStore
from tieny.core.errors import TienyError

logger = logging.getLogger(__name__)


class ServerUnavailable(TienyError):
    pass


def base_url() -> str:
    config = ConfigStore().load()
    return f"http://{config.host}:{config.port}"


def request(
    method: str,
    path: str,
    *,
    payload: dict | None = None,
    query: dict[str, object] | None = None,
    timeout: float = 2.0,
) -> object:
    url = f"{base_url()}{path}"
    if query:
        url += "?" + urlencode(query)
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = Request(url, data=body, method=method)
    if body is not None:
        req.add_header("Content-Type", "application/json")
    logger.debug("CLI -> server %s %s", method, url)
    try:
        with urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(detail).get("detail", detail)
        except json.JSONDecodeError:
            pass
        raise TienyError(str(detail)) from exc
    except URLError as exc:
        raise ServerUnavailable(
            "Tieny server is not running. Start it with 'tieny start'."
        ) from exc


def target_path(target: str) -> str:
    return quote(target, safe="")


def is_running() -> bool:
    try:
        request("GET", "/api/health", timeout=0.35)
        return True
    except TienyError:
        return False
