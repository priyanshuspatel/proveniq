import json
import socket
from urllib import error, request

from app.config import Settings


class ResponseTooLarge(Exception):
    pass


def ollama_headers(settings: Settings) -> dict[str, str]:
    headers = {"Accept": "application/json"}
    key = (settings.ollama_api_key or "").strip()
    if key:
        headers["Authorization"] = f"Bearer {key}"
    return headers


def read_bounded_response(response, max_bytes: int) -> bytes:
    """Read at most one byte past the configured limit and reject oversized output."""
    try:
        raw = response.read(max_bytes + 1)
    except TypeError:
        # Small test doubles and older urllib-compatible adapters may not accept a size.
        raw = response.read()
    if len(raw) > max_bytes:
        raise ResponseTooLarge
    return raw


def inference_status(settings: Settings) -> dict:
    url = settings.ollama_host.rstrip("/") + "/api/tags"
    req = request.Request(url, headers=ollama_headers(settings))
    try:
        with request.urlopen(req, timeout=settings.ollama_health_timeout_seconds) as response:
            payload = json.loads(read_bounded_response(response, settings.ollama_max_response_bytes).decode())
    except error.URLError as exc:
        if isinstance(exc.reason, (TimeoutError, socket.timeout)):
            return {"status": "unavailable", "code": "extraction_timeout"}
        return {"status": "unavailable", "code": "extraction_unavailable"}
    except (TimeoutError, socket.timeout, json.JSONDecodeError, UnicodeError, ResponseTooLarge):
        return {"status": "unavailable", "code": "extraction_unavailable"}
    names = []
    if isinstance(payload, dict):
        for item in payload.get("models") or []:
            if isinstance(item, dict) and isinstance(item.get("name"), str):
                names.append(item["name"])
    wanted = settings.ollama_model
    if wanted not in names and not any(name.startswith(wanted + ":") for name in names):
        return {"status": "unavailable", "code": "model_unavailable", "model": wanted}
    return {"status": "ok", "model": wanted}
