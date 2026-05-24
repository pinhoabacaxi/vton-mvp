# -*- coding: utf-8 -*-
"""Lightweight upload lifecycle management for Render Free.

Render's local filesystem is ephemeral and small. This module only removes files
inside the configured uploads directory, and it does so after a delay so mobile
clients have time to poll and render the generated result.
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Iterable
from urllib.parse import unquote, urlparse


LOGGER = logging.getLogger(__name__)
UPLOAD_ROOT = Path(os.getenv("UPLOAD_DIR", "uploads")).resolve()
DEFAULT_CLEANUP_DELAY_SECONDS = int(os.getenv("UPLOAD_GC_DELAY_SECONDS", "1800"))


def schedule_upload_cleanup(
    references: Iterable[str | Path | None],
    delay_seconds: int | None = None,
) -> None:
    """Schedule asynchronous deletion for safe upload references.

    The function is intentionally best-effort: cleanup failures should never
    break a completed VTON task.
    """

    paths = collect_upload_paths(references)
    if not paths:
        return

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        LOGGER.info("Skipping upload cleanup scheduling because no event loop is running.")
        return

    loop.create_task(cleanup_uploads_later(paths, delay_seconds=delay_seconds))


async def cleanup_uploads_later(
    paths: Iterable[Path],
    delay_seconds: int | None = None,
) -> None:
    """Delete files under uploads after a configurable delay."""

    delay = DEFAULT_CLEANUP_DELAY_SECONDS if delay_seconds is None else max(0, delay_seconds)
    if delay:
        await asyncio.sleep(delay)

    for path in paths:
        try:
            resolved = path.resolve()
            if not _is_safe_upload_path(resolved):
                LOGGER.warning("Refusing to cleanup path outside uploads: %s", resolved)
                continue

            if resolved.exists() and resolved.is_file():
                resolved.unlink()
                LOGGER.info("Cleaned temporary upload file: %s", resolved)
                _remove_empty_upload_parents(resolved.parent)
        except Exception as error:  # pragma: no cover - defensive cleanup path
            LOGGER.warning("Failed to cleanup upload file %s: %s", path, error)


def collect_upload_paths(references: Iterable[str | Path | None]) -> list[Path]:
    """Resolve unique upload-local paths from URLs, API paths, and file paths."""

    seen: set[Path] = set()
    paths: list[Path] = []

    for reference in references:
        path = resolve_upload_reference(reference)
        if path and path not in seen:
            seen.add(path)
            paths.append(path)

    return paths


def resolve_upload_reference(reference: str | Path | None) -> Path | None:
    """Map a reference to a local upload file path when it is safe to delete."""

    if not reference:
        return None

    raw = str(reference).strip()
    if not raw:
        return None

    parsed = urlparse(raw)
    if parsed.scheme in {"http", "https"}:
        raw = unquote(parsed.path)

    marker = "/uploads/"
    if raw.startswith(marker):
        candidate = UPLOAD_ROOT / raw[len(marker) :]
    elif raw.startswith("uploads/") or raw.startswith("uploads\\"):
        candidate = Path(raw)
    else:
        candidate = Path(raw)

    try:
        resolved = candidate.resolve()
    except OSError:
        return None

    return resolved if _is_safe_upload_path(resolved) else None


def _is_safe_upload_path(path: Path) -> bool:
    try:
        path.relative_to(UPLOAD_ROOT)
        return True
    except ValueError:
        return False


def _remove_empty_upload_parents(start: Path) -> None:
    """Prune empty child directories without removing the upload root itself."""

    current = start.resolve()
    while current != UPLOAD_ROOT and _is_safe_upload_path(current):
        try:
            current.rmdir()
        except OSError:
            return
        current = current.parent
