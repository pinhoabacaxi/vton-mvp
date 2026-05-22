import logging
import os
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from PIL import Image, ImageEnhance, ImageOps

from app.services.url_utils import absolute_url


LOGGER = logging.getLogger(__name__)

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


def _is_rembg_disabled() -> bool:
    return os.getenv("DISABLE_REMBG", "").strip().lower() == "true"


async def save_garment_upload(file: UploadFile) -> tuple[str, str]:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError("Formato invalido. Envie JPG, PNG ou WEBP.")

    extension = _extension_from_content_type(file.content_type)
    filename = f"garment_{uuid4().hex}{extension}"
    destination = ORIGINAL_DIR / filename

    content = await file.read()

    if not content:
        raise ValueError("Arquivo vazio.")

    destination.write_bytes(content)

    return filename, str(destination)


def _open_optimized_rgba(original: Path) -> Image.Image:
    image = Image.open(original)
    image = ImageOps.exif_transpose(image)
    image.thumbnail((MAX_IMAGE_EDGE, MAX_IMAGE_EDGE), Image.Resampling.LANCZOS)
    return image.convert("RGBA")


def _save_lightweight_fallback(image: Image.Image, original: Path, reason: str) -> tuple[str, str]:
    fallback_filename = f"{original.stem}_optimized.png"
    fallback_path = PROCESSED_DIR / fallback_filename
    normalized = normalize_garment_visual(image)
    normalized.save(fallback_path, "PNG", optimize=True)
    LOGGER.info("Using lightweight image fallback for %s: %s", original.name, reason)
    return fallback_filename, str(fallback_path)


def normalize_garment_visual(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")

    rgb = Image.new("RGB", rgba.size, (22, 18, 30))
    rgb.paste(rgba.convert("RGB"), mask=alpha)
    rgb = ImageEnhance.Contrast(rgb).enhance(1.08)
    rgb = ImageEnhance.Color(rgb).enhance(1.06)
    rgb = ImageEnhance.Sharpness(rgb).enhance(1.04)
    rgb = ImageEnhance.Brightness(rgb).enhance(1.01)

    return Image.merge("RGBA", (*rgb.split(), alpha))


def remove_background(original_path: str) -> tuple[str, str]:
    original = Path(original_path)

    if not original.exists():
        raise FileNotFoundError("Imagem original nao encontrada.")

    with _open_optimized_rgba(original) as image:
        if _is_rembg_disabled():
            return _save_lightweight_fallback(image, original, "DISABLE_REMBG=true")

        try:
            from rembg import remove
        except ImportError as error:
            return _save_lightweight_fallback(
                image,
                original,
                f"rembg is not installed ({error.__class__.__name__})",
            )

        output_filename = f"{original.stem}_nobg.png"
        output_path = PROCESSED_DIR / output_filename

        try:
            processed = remove(image)
            processed = normalize_garment_visual(processed)
            processed.save(output_path, "PNG", optimize=True)
        except Exception as error:
            LOGGER.exception(
                "rembg failed for %s; using lightweight fallback instead.",
                original.name,
            )
            return _save_lightweight_fallback(
                image,
                original,
                f"rembg failed ({error.__class__.__name__})",
            )

    return output_filename, str(output_path)


def public_file_url(path: str) -> str:
    normalized = Path(path).as_posix()

    if "uploads/" in normalized:
        relative = normalized.split("uploads/", 1)[1]
    else:
        relative = Path(path).name

    return absolute_url(f"/uploads/{relative}")
