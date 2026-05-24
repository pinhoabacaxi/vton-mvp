# -*- coding: utf-8 -*-
"""Production health check for the VTON MVP backend."""

from __future__ import annotations

import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_HEALTH_URL = "https://vton-mvp-api.onrender.com/health"


def main() -> int:
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_HEALTH_URL
    request = Request(url, headers={"Accept": "application/json"})

    try:
        with urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        print(f"HEALTH_CHECK_FAILED: {error}", file=sys.stderr)
        return 1

    if payload.get("ok") is True or payload.get("status") == "ok":
        print(json.dumps({"ok": True, "url": url}, ensure_ascii=False))
        return 0

    print(f"HEALTH_CHECK_UNEXPECTED_PAYLOAD: {payload}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
