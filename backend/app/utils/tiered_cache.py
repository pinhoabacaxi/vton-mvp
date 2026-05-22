from __future__ import annotations

import hashlib
import json
import time
from copy import deepcopy
from threading import Lock
from typing import Any, Optional


_CACHE: dict[str, tuple[float, Any]] = {}
_LOCK = Lock()
DEFAULT_TTL_SECONDS = 900


def stable_hash(payload: Any) -> str:
    """Create a deterministic hash for fit/render cache keys."""

    encoded = json.dumps(_jsonable(payload), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:24]


def get_cache(key: str) -> Optional[Any]:
    now = time.time()
    with _LOCK:
        entry = _CACHE.get(key)
        if not entry:
            return None

        expires_at, value = entry
        if expires_at < now:
            _CACHE.pop(key, None)
            return None

        return deepcopy(value)


def set_cache(key: str, value: Any, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
    with _LOCK:
        _CACHE[key] = (time.time() + ttl_seconds, deepcopy(value))


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value
