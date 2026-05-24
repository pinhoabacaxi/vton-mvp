# -*- coding: utf-8 -*-
"""Ephemeral user person-photo handling for neural VTON.

User photos are stored only as short-lived temp files and are referenced through
opaque ephemeral:// URLs. They are never mounted under /uploads and are never
intended for public access.
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import UploadFile
from PIL import Image, ImageEnhance, ImageOps, UnidentifiedImageError


LOGGER = logging.getLogger(__name__)
EPHEMERAL_PERSON_DIR = Path(tempfile.gettempdir()) / "vton_ephemeral_person"
EPHEMERAL_PERSON_DIR.mkdir(parents=True, exist_ok=True)
EPHEMERAL_PREFIX = "ephemeral://person/"
MAX_PERSON_UPLOAD_BYTES = 8 * 1024 * 1024
DEFAULT_PERSON_TTL_SECONDS = int(os.getenv("PERSON_EPHEMERAL_TTL_SECONDS", str(20 * 60)))


class EphemeralPersonImageError(Exception):
    pass


async def save_ephemeral_person_upload(file: UploadFile, enhance: bool = True) -> tuple[str, int, bool]:
    """Save a privacy-sensitive person photo as a short-lived JPEG temp file."""

    content_type = (file.content_type or "").lower()
    if content_type and not content_type.startswith("image/"):
        raise EphemeralPersonImageError("Envie uma imagem em formato JPG, PNG ou WEBP.")

    payload = await file.read(MAX_PERSON_UPLOAD_BYTES + 1)
    if len(payload) > MAX_PERSON_UPLOAD_BYTES:
        raise EphemeralPersonImageError("A foto é muito grande. Tente uma imagem menor.")

    try:
        with Image.open(BytesIO(payload)) as source:
            image = ImageOps.exif_transpose(source)
            image = _prepare_person_jpeg(image, enhance=enhance)
    except (OSError, UnidentifiedImageError) as error:
        raise EphemeralPersonImageError("Não conseguimos abrir essa foto. Tente outra imagem.") from error

    filename = f"{uuid4().hex}.jpg"
    output_path = EPHEMERAL_PERSON_DIR / filename
    image.save(output_path, "JPEG", quality=86, optimize=True, progressive=False)

    reference = f"{EPHEMERAL_PREFIX}{filename}"
    schedule_ephemeral_person_delete(reference, delay_seconds=DEFAULT_PERSON_TTL_SECONDS)
    return reference, DEFAULT_PERSON_TTL_SECONDS, enhance


def is_ephemeral_person_reference(reference: Optional[str]) -> bool:
    return bool(reference and reference.startswith(EPHEMERAL_PREFIX))


def resolve_ephemeral_person_path(reference: str) -> Path:
    if not is_ephemeral_person_reference(reference):
        raise EphemeralPersonImageError("Referência efêmera de foto inválida.")

    filename = reference.removeprefix(EPHEMERAL_PREFIX)
    if not filename or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789-_."
                          for ch in filename.lower()):
        raise EphemeralPersonImageError("Referência efêmera de foto inválida.")

    path = (EPHEMERAL_PERSON_DIR / filename).resolve()
    if not _is_safe_ephemeral_path(path):
        raise EphemeralPersonImageError("Referência efêmera fora do diretório permitido.")
    if not path.exists():
        raise EphemeralPersonImageError("A foto efêmera expirou. Envie a foto novamente.")
    return path


def delete_ephemeral_person_reference(reference: Optional[str]) -> None:
    if not is_ephemeral_person_reference(reference):
        return

    try:
        path = resolve_ephemeral_person_path(reference)
    except EphemeralPersonImageError:
        return

    try:
        path.unlink(missing_ok=True)
        LOGGER.info("Deleted ephemeral person photo.")
    except OSError as error:
        LOGGER.warning("Failed to delete ephemeral person photo: %s", error)


def schedule_ephemeral_person_delete(reference: str, delay_seconds: int) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return

    loop.create_task(_delete_ephemeral_later(reference, delay_seconds))


async def _delete_ephemeral_later(reference: str, delay_seconds: int) -> None:
    await asyncio.sleep(max(0, delay_seconds))
    delete_ephemeral_person_reference(reference)


def _prepare_person_jpeg(image: Image.Image, enhance: bool = True) -> Image.Image:
    if image.width < 320 or image.height < 480:
        raise EphemeralPersonImageError(
            "A foto está pequena demais. Use uma foto de corpo inteiro com boa luz."
        )

    rgba = image.convert("RGBA")
    background = Image.new("RGB", rgba.size, (248, 248, 246))
    background.paste(rgba.convert("RGB"), mask=rgba.getchannel("A"))

    if enhance:
        background = ImageOps.autocontrast(background, cutoff=1)
        background = ImageEnhance.Brightness(background).enhance(1.08)
        background = ImageEnhance.Contrast(background).enhance(1.08)

    background.thumbnail((768, 1152), Image.Resampling.LANCZOS)
    return background


def _is_safe_ephemeral_path(path: Path) -> bool:
    try:
        path.relative_to(EPHEMERAL_PERSON_DIR.resolve())
        return True
    except ValueError:
        return False
