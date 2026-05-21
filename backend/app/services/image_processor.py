import os
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from PIL import Image, ImageOps

from app.services.url_utils import absolute_url


UPLOAD_DIR = Path("uploads")
ORIGINAL_DIR = UPLOAD_DIR / "originals"
PROCESSED_DIR = UPLOAD_DIR / "processed"
MAX_IMAGE_EDGE = int(os.getenv("IMAGE_PROCESSOR_MAX_EDGE", "1600"))

ORIGINAL_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
}


def _extension_from_content_type(content_type: str | None) -> str:
    if content_type == "image/png":
        return ".png"
    if content_type == "image/webp":
        return ".webp"
    return ".jpg"


async def save_garment_upload(file: UploadFile) -> tuple[str, str]:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError("Formato inválido. Envie JPG, PNG ou WEBP.")

    extension = _extension_from_content_type(file.content_type)
    filename = f"garment_{uuid4().hex}{extension}"
    destination = ORIGINAL_DIR / filename

    content = await file.read()

    if not content:
        raise ValueError("Arquivo vazio.")

    destination.write_bytes(content)

    return filename, str(destination)


def remove_background(original_path: str) -> tuple[str, str]:
    original = Path(original_path)

    if not original.exists():
        raise FileNotFoundError("Imagem original não encontrada.")

    output_filename = f"{original.stem}_nobg.png"
    output_path = PROCESSED_DIR / output_filename

    with Image.open(original) as image:
        image = ImageOps.exif_transpose(image)
        image.thumbnail((MAX_IMAGE_EDGE, MAX_IMAGE_EDGE), Image.Resampling.LANCZOS)
        image = image.convert("RGBA")

        if os.getenv("DISABLE_REMBG", "").strip().lower() == "true":
            fallback_filename = f"{original.stem}_optimized.png"
            fallback_path = PROCESSED_DIR / fallback_filename
            image.save(fallback_path, "PNG", optimize=True)
            return fallback_filename, str(fallback_path)

        from rembg import remove

        processed = remove(image)
        processed.save(output_path, "PNG", optimize=True)

    return output_filename, str(output_path)


def public_file_url(path: str) -> str:
    normalized = Path(path).as_posix()

    if "uploads/" in normalized:
        relative = normalized.split("uploads/", 1)[1]
    else:
        relative = Path(path).name

    return absolute_url(f"/uploads/{relative}")
