# -*- coding: utf-8 -*-
import os
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen
from uuid import uuid4

from PIL import Image, ImageChops, ImageFilter, ImageOps, ImageStat, UnidentifiedImageError


class ImageNormalizationError(Exception):
    pass


@dataclass(frozen=True)
class NormalizedImage:
    url: str
    path: Path
    width: int
    height: int
    file_size_bytes: int
    simplicity_score: float
    too_simple: bool


HF_INPUT_DIR = Path("uploads") / "hf_inputs"
HF_INPUT_DIR.mkdir(parents=True, exist_ok=True)


def download_or_open_image(path_or_url: str, max_bytes: int = 10 * 1024 * 1024) -> Image.Image:
    """Open a local upload path or download a public image into a PIL image."""

    if not path_or_url:
        raise ImageNormalizationError("Caminho/URL de imagem ausente.")

    local_path = resolve_local_path(path_or_url)
    if local_path and local_path.exists():
        try:
            return Image.open(local_path)
        except (OSError, UnidentifiedImageError) as error:
            raise ImageNormalizationError(
                f"Imagem local invalida ou corrompida: {type(error).__name__}: {error}"
            ) from error

    if path_or_url.startswith(("http://", "https://")):
        request = Request(
            path_or_url,
            headers={"User-Agent": "VTON-MVP/1.0 image-normalizer"},
        )
        try:
            with urlopen(request, timeout=20) as response:
                payload = response.read(max_bytes + 1)
        except OSError as error:
            raise ImageNormalizationError(
                f"Nao foi possivel baixar imagem publica: {type(error).__name__}: {error}"
            ) from error

        if len(payload) > max_bytes:
            raise ImageNormalizationError("Imagem maior que o limite de download permitido.")

        try:
            return Image.open(BytesIO(payload))
        except (OSError, UnidentifiedImageError) as error:
            raise ImageNormalizationError(
                f"Imagem remota invalida ou corrompida: {type(error).__name__}: {error}"
            ) from error

    raise ImageNormalizationError("Imagem nao encontrada ou URL invalida.")


def normalize_image_for_vton(
    input_path_or_url: str,
    *,
    kind: str,
    output_dir: Path = HF_INPUT_DIR,
    target_size: tuple[int, int] = (768, 1024),
    background_rgb: tuple[int, int, int] = (248, 248, 246),
    max_file_size_bytes: int = 2 * 1024 * 1024,
    require_public_url: bool = True,
) -> NormalizedImage:
    """Normalize person/garment images for strict VTON provider expectations."""

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{kind}_{uuid4().hex}.jpg"

    try:
        with download_or_open_image(input_path_or_url) as image:
            image = ImageOps.exif_transpose(image)
            validate_source_image(image, kind)
            normalized = fit_on_studio_canvas(
                image,
                target_size=target_size,
                kind=kind,
                background_rgb=background_rgb,
            )
            simplicity_score = image_simplicity_score(normalized)
            too_simple = is_too_simple_for_vton(normalized, kind, simplicity_score)
            file_size = save_optimized_jpeg(
                normalized,
                output_path,
                max_file_size_bytes=max_file_size_bytes,
            )
    except ImageNormalizationError:
        raise
    except Exception as error:
        raise ImageNormalizationError(
            f"Nao foi possivel normalizar imagem {kind}: {type(error).__name__}: {error}"
        ) from error

    return NormalizedImage(
        url=public_upload_url(output_path, require_public_url=require_public_url),
        path=output_path,
        width=target_size[0],
        height=target_size[1],
        file_size_bytes=file_size,
        simplicity_score=simplicity_score,
        too_simple=too_simple,
    )


def fit_on_studio_canvas(
    image: Image.Image,
    *,
    target_size: tuple[int, int],
    kind: str,
    background_rgb: tuple[int, int, int],
) -> Image.Image:
    rgba = image.convert("RGBA")
    rgb = Image.new("RGB", rgba.size, background_rgb)
    rgb.paste(rgba.convert("RGB"), mask=rgba.getchannel("A"))

    if kind == "garment":
        rgb = crop_garment_content(rgb)

    canvas = Image.new("RGB", target_size, background_rgb)
    max_width = int(target_size[0] * (0.88 if kind == "person" else 0.78))
    max_height = int(target_size[1] * (0.96 if kind == "person" else 0.86))
    rgb.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

    x = (target_size[0] - rgb.width) // 2
    y_bias = 0.46 if kind == "person" else 0.50
    y = int((target_size[1] - rgb.height) * y_bias)
    canvas.paste(rgb, (x, max(0, y)))
    return canvas


def validate_source_image(image: Image.Image, kind: str) -> None:
    if image.width < 128 or image.height < 128:
        raise ImageNormalizationError(f"Imagem {kind} pequena demais para VTON.")

    if kind == "person" and (image.width < 320 or image.height < 480):
        raise ImageNormalizationError("Imagem da pessoa/manequim pequena demais para VTON.")

    if "A" in image.getbands():
        alpha = image.convert("RGBA").getchannel("A")
        visible_bbox = alpha.point(lambda value: 255 if value > 12 else 0).getbbox()
        if not visible_bbox:
            raise ImageNormalizationError(f"Imagem {kind} sem pixels visiveis.")

        visible_area = (visible_bbox[2] - visible_bbox[0]) * (visible_bbox[3] - visible_bbox[1])
        total_area = image.width * image.height
        if kind == "person" and visible_area / max(1, total_area) < 0.08:
            raise ImageNormalizationError("Imagem da pessoa/manequim transparente demais para VTON.")


def crop_garment_content(image: Image.Image) -> Image.Image:
    sample_points = [
        (0, 0),
        (image.width - 1, 0),
        (0, image.height - 1),
        (image.width - 1, image.height - 1),
    ]
    colors = [image.getpixel(point) for point in sample_points]
    background = tuple(int(sum(channel) / len(colors)) for channel in zip(*colors))
    diff = ImageChops.difference(image, Image.new("RGB", image.size, background)).convert("L")
    mask = diff.point(lambda value: 255 if value > 22 else 0)
    mask = mask.filter(ImageFilter.MaxFilter(9))
    bbox = mask.getbbox()
    if not bbox:
        return image

    margin_x = int(image.width * 0.04)
    margin_y = int(image.height * 0.04)
    return image.crop(
        (
            max(0, bbox[0] - margin_x),
            max(0, bbox[1] - margin_y),
            min(image.width, bbox[2] + margin_x),
            min(image.height, bbox[3] + margin_y),
        )
    )


def image_simplicity_score(image: Image.Image) -> float:
    """Return 0.0 for visually simple images and closer to 1.0 for photo-like images."""

    rgb = image.convert("RGB").resize((192, 256), Image.Resampling.BILINEAR)
    stat = ImageStat.Stat(rgb)
    channel_stddev = sum(stat.stddev) / 3.0

    gray = rgb.convert("L")
    edge = gray.filter(ImageFilter.FIND_EDGES)
    edge_stat = ImageStat.Stat(edge)
    edge_strength = edge_stat.mean[0]

    histogram = gray.histogram()
    non_empty_bins = sum(1 for value in histogram if value)

    score = (channel_stddev / 80.0) * 0.45
    score += (edge_strength / 40.0) * 0.35
    score += (non_empty_bins / 256.0) * 0.20
    return max(0.0, min(1.0, score))


def is_too_simple_for_vton(
    image: Image.Image,
    kind: str,
    simplicity_score: Optional[float] = None,
) -> bool:
    if kind != "person":
        return False

    score = simplicity_score if simplicity_score is not None else image_simplicity_score(image)
    if score >= float(os.getenv("VTON_PERSON_SIMPLICITY_MIN_SCORE", "0.18")):
        return False

    return os.getenv("HF_REJECT_SIMPLE_PERSON", "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "sim",
    }


def save_optimized_jpeg(
    image: Image.Image,
    output_path: Path,
    *,
    max_file_size_bytes: int,
) -> int:
    quality_values = (90, 84, 78, 72, 66)
    for quality in quality_values:
        image.save(output_path, "JPEG", quality=quality, optimize=True, progressive=False)
        file_size = output_path.stat().st_size
        if file_size <= max_file_size_bytes:
            return file_size

    return output_path.stat().st_size


def public_upload_url(path: Path, *, require_public_url: bool = True) -> str:
    normalized = path.as_posix()
    if "uploads/" not in normalized:
        raise ImageNormalizationError("Arquivo normalizado fora de /uploads.")

    public_backend_url = os.getenv("PUBLIC_BACKEND_URL", "").strip().rstrip("/")
    relative = normalized.split("uploads/", 1)[1].lstrip("/")
    if public_backend_url:
        return f"{public_backend_url}/uploads/{relative}"

    if require_public_url:
        raise ImageNormalizationError(
            "PUBLIC_BACKEND_URL ausente. Providers externos precisam de URLs publicas para /uploads."
        )

    return f"/uploads/{relative}"


def resolve_local_path(path_or_url: str) -> Optional[Path]:
    parsed = urlparse(path_or_url)
    normalized = parsed.path if parsed.scheme else path_or_url
    normalized = unquote(normalized.replace("\\", "/"))

    direct = Path(normalized)
    if direct.exists():
        return direct

    if "uploads/" in normalized:
        relative = normalized.split("uploads/", 1)[1].lstrip("/")
        return Path("uploads") / relative

    return None
