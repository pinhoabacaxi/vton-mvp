import asyncio
import os
import shutil
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen
from uuid import uuid4

from PIL import Image, ImageChops, ImageFilter, ImageOps

from app.models.vton import VtonPayload
from app.services.url_utils import absolute_url


class HuggingFaceNotConfigured(Exception):
    pass


class HuggingFaceProviderError(Exception):
    pass


HF_OUTPUT_DIR = Path("uploads") / "vton"
HF_INPUT_DIR = Path("uploads") / "hf_inputs"
HF_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
HF_INPUT_DIR.mkdir(parents=True, exist_ok=True)


def is_huggingface_configured() -> bool:
    space_id = os.getenv("HF_SPACE_ID", "yisol/IDM-VTON").strip()
    return bool(space_id)


async def run_huggingface_vton(payload: VtonPayload) -> Dict[str, Any]:
    if not is_huggingface_configured():
        raise HuggingFaceNotConfigured("HF_SPACE_ID nao configurado.")

    if _env_bool("HF_SKIP_FOR_MOCK_PERSON", False) and _is_mock_person_url(payload.person_image_url):
        raise HuggingFaceProviderError(
            "Hugging Face ignorado para manequim sintetico por HF_SKIP_FOR_MOCK_PERSON=true."
        )

    person_source = _absolute_public_url(payload.person_image_url, "person_image_url")
    garment_source = _absolute_public_url(
        payload.garment_processed_url or payload.garment_original_url,
        "garment_processed_url",
    )

    if _env_bool("HF_NORMALIZE_INPUTS", True):
        person_url = normalize_image_for_hf(person_source, "person")
        garment_url = normalize_image_for_hf(garment_source, "garment")
    else:
        person_url = person_source
        garment_url = garment_source

    try:
        raw_result = await asyncio.to_thread(
            _call_space,
            person_url=person_url,
            garment_url=garment_url,
        )
    except HuggingFaceProviderError:
        raise
    except Exception as error:
        raise _controlled_space_error(error) from error

    serialized_output = _serialize_gradio_value(raw_result)
    output_items = _as_sequence(serialized_output)
    result_url = _normalize_result_reference(output_items[0] if output_items else None)
    masked_url = _normalize_result_reference(output_items[1] if len(output_items) > 1 else None)

    return {
        "provider": "huggingface",
        "space_id": _space_id(),
        "status": "succeeded",
        "output": serialized_output,
        "result_url": result_url,
        "masked_url": masked_url,
    }


def extract_huggingface_result_url(raw_response: Dict[str, Any]) -> Optional[str]:
    for key in ("result_url", "image_url", "output_url", "url"):
        value = raw_response.get(key)
        if isinstance(value, str) and value:
            return value

    output = raw_response.get("output")
    output_items = _as_sequence(output)
    if output_items:
        return _normalize_result_reference(output_items[0])

    return None


def download_or_open_image(path_or_url: str) -> Image.Image:
    local_path = _resolve_local_path(path_or_url)
    if local_path and local_path.exists():
        return Image.open(local_path)

    if path_or_url.startswith(("http://", "https://")):
        request = Request(
            path_or_url,
            headers={"User-Agent": "VTON-MVP/1.0 hf-input-normalizer"},
        )
        with urlopen(request, timeout=20) as response:
            payload = response.read(10 * 1024 * 1024)
        return Image.open(BytesIO(payload))

    raise HuggingFaceProviderError("Imagem nao encontrada ou URL invalida para Hugging Face.")


def normalize_image_for_hf(input_path_or_url: str, kind: str) -> str:
    target_size = _target_size_for_hf(kind)
    filename = f"hf_{kind}_{uuid4().hex}.jpg"
    output_path = HF_INPUT_DIR / filename

    try:
        with download_or_open_image(input_path_or_url) as image:
            image = ImageOps.exif_transpose(image)
            _validate_hf_source_image(image, kind)
            normalized = _fit_on_light_canvas(image, target_size, kind)
            normalized.save(
                output_path,
                "JPEG",
                quality=_env_int("HF_JPEG_QUALITY", 90),
                optimize=True,
                progressive=True,
            )
    except HuggingFaceProviderError:
        raise
    except Exception as error:
        raise HuggingFaceProviderError(
            f"Nao foi possivel normalizar imagem {kind} para Hugging Face: {type(error).__name__}: {error}"
        ) from error

    return _public_upload_url(output_path)


def _call_space(person_url: str, garment_url: str) -> Any:
    try:
        from gradio_client import Client

        try:
            from gradio_client import handle_file as gradio_file
        except ImportError:
            from gradio_client import file as gradio_file
    except ImportError as error:
        raise HuggingFaceProviderError(
            "gradio_client nao instalado. Execute pip install -r requirements.txt."
        ) from error

    token = os.getenv("HF_API_TOKEN", "").strip() or None
    try:
        client = Client(_space_id(), hf_token=token)
    except TypeError:
        client = Client(_space_id(), token=token)

    return client.predict(
        dict={
            "background": gradio_file(person_url),
            "layers": [],
            "composite": None,
        },
        garm_img=gradio_file(garment_url),
        garment_des=_env_str(
            "HF_GARMENT_DESCRIPTION",
            "clothing item for virtual try-on",
        ),
        is_checked=True,
        is_checked_crop=_env_bool("HF_IS_CHECKED_CROP", False),
        denoise_steps=_env_int("HF_DENOISE_STEPS", 30),
        seed=_env_int("HF_SEED", 42),
        api_name=_env_str("HF_SPACE_API_NAME", "/tryon"),
    )


def _absolute_public_url(path_or_url: Optional[str], field_name: str) -> str:
    if not path_or_url:
        raise HuggingFaceProviderError(f"{field_name} ausente para Hugging Face VTON.")

    url = absolute_url(path_or_url)
    if url.startswith(("http://", "https://")):
        return url

    if url.startswith("/uploads"):
        public_backend_url = os.getenv("PUBLIC_BACKEND_URL", "").strip().rstrip("/")
        if public_backend_url:
            return f"{public_backend_url}{url}"

    raise HuggingFaceProviderError(
        f"{field_name} precisa ser URL publica. Configure PUBLIC_BACKEND_URL para arquivos /uploads."
    )


def _public_upload_url(path: Path) -> str:
    normalized = path.as_posix()
    if "uploads/" not in normalized:
        raise HuggingFaceProviderError("Arquivo normalizado fora de /uploads.")

    public_backend_url = os.getenv("PUBLIC_BACKEND_URL", "").strip().rstrip("/")
    if not public_backend_url:
        raise HuggingFaceProviderError(
            "PUBLIC_BACKEND_URL ausente. Hugging Face precisa de URLs publicas para /uploads."
        )

    relative = normalized.split("uploads/", 1)[1].lstrip("/")
    return f"{public_backend_url}/uploads/{relative}"


def _resolve_local_path(path_or_url: str) -> Optional[Path]:
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


def _target_size_for_hf(kind: str) -> tuple[int, int]:
    if kind == "person":
        return (
            _env_int("HF_PERSON_WIDTH", 768),
            _env_int("HF_PERSON_HEIGHT", 1024),
        )

    return (
        _env_int("HF_GARMENT_WIDTH", 768),
        _env_int("HF_GARMENT_HEIGHT", 1024),
    )


def _validate_hf_source_image(image: Image.Image, kind: str) -> None:
    if image.width < 128 or image.height < 128:
        raise HuggingFaceProviderError(f"Imagem {kind} pequena demais para Hugging Face.")

    if kind == "person" and (image.width < 320 or image.height < 480):
        raise HuggingFaceProviderError("Imagem da pessoa/manequim pequena demais para Hugging Face.")

    if "A" in image.getbands():
        alpha = image.convert("RGBA").getchannel("A")
        visible_bbox = alpha.point(lambda value: 255 if value > 12 else 0).getbbox()
        if not visible_bbox:
            raise HuggingFaceProviderError(f"Imagem {kind} sem pixels visiveis.")

        visible_area = (visible_bbox[2] - visible_bbox[0]) * (visible_bbox[3] - visible_bbox[1])
        total_area = image.width * image.height
        if kind == "person" and visible_area / max(1, total_area) < 0.08:
            raise HuggingFaceProviderError("Imagem da pessoa/manequim transparente demais para Hugging Face.")


def _fit_on_light_canvas(
    image: Image.Image,
    target_size: tuple[int, int],
    kind: str,
) -> Image.Image:
    rgba = image.convert("RGBA")
    rgb = Image.new("RGB", rgba.size, (246, 242, 236))
    rgb.paste(rgba.convert("RGB"), mask=rgba.getchannel("A"))

    if kind == "garment":
        rgb = _crop_garment_content(rgb)

    canvas = Image.new("RGB", target_size, (246, 242, 236))
    max_width = int(target_size[0] * (0.82 if kind == "person" else 0.76))
    max_height = int(target_size[1] * (0.94 if kind == "person" else 0.86))
    rgb.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

    x = (target_size[0] - rgb.width) // 2
    y = int((target_size[1] - rgb.height) * (0.48 if kind == "person" else 0.50))
    canvas.paste(rgb, (x, max(0, y)))
    return canvas


def _crop_garment_content(image: Image.Image) -> Image.Image:
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


def _is_mock_person_url(path_or_url: Optional[str]) -> bool:
    if not path_or_url:
        return False
    normalized = path_or_url.replace("\\", "/")
    return "/uploads/mannequin/" in normalized or normalized.startswith("uploads/mannequin/")


def _controlled_space_error(error: Exception) -> HuggingFaceProviderError:
    raw_message = str(error)
    lowered = raw_message.lower()
    error_name = type(error).__name__

    if (
        "indexerror" in error_name.lower()
        or "indexerror" in lowered
        or "list index out of range" in lowered
        or "empty mask" in lowered
        or "mask" in lowered and "empty" in lowered
        or "crop" in lowered
        or "detect" in lowered
    ):
        return HuggingFaceProviderError(
            "O Space Hugging Face falhou ao processar a imagem. "
            "Isso costuma acontecer quando a imagem da pessoa/manequim não é compatível com o modelo."
        )

    return HuggingFaceProviderError(
        f"Hugging Face Space falhou: {error_name}: {raw_message}"
    )


def _normalize_result_reference(value: Any) -> Optional[str]:
    reference = _extract_file_reference(value)
    if not reference:
        return None

    if reference.startswith(("http://", "https://")):
        return reference

    if reference.startswith("/uploads"):
        return absolute_url(reference)

    path = Path(reference)
    if path.exists() and path.is_file():
        extension = path.suffix if path.suffix else ".png"
        filename = f"hf_vton_{uuid4().hex}{extension}"
        destination = HF_OUTPUT_DIR / filename
        shutil.copyfile(path, destination)
        return absolute_url(f"/uploads/vton/{filename}")

    return None


def _extract_file_reference(value: Any) -> Optional[str]:
    if isinstance(value, str):
        return value

    if isinstance(value, dict):
        for key in ("url", "path", "name", "file", "filepath"):
            nested = value.get(key)
            if isinstance(nested, str) and nested:
                return nested

        data = value.get("data")
        if isinstance(data, dict):
            return _extract_file_reference(data)

    return None


def _serialize_gradio_value(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_serialize_gradio_value(item) for item in value]

    if isinstance(value, list):
        return [_serialize_gradio_value(item) for item in value]

    if isinstance(value, dict):
        return {key: _serialize_gradio_value(item) for key, item in value.items()}

    if isinstance(value, (str, int, float, bool)) or value is None:
        return value

    if hasattr(value, "model_dump"):
        return _serialize_gradio_value(value.model_dump())

    if hasattr(value, "dict"):
        return _serialize_gradio_value(value.dict())

    path = getattr(value, "path", None)
    if isinstance(path, str):
        return {"path": path}

    url = getattr(value, "url", None)
    if isinstance(url, str):
        return {"url": url}

    return str(value)


def _as_sequence(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if value is None:
        return []
    return [value]


def _space_id() -> str:
    return _env_str("HF_SPACE_ID", "yisol/IDM-VTON")


def _env_str(name: str, default: str) -> str:
    return os.getenv(name, default).strip() or default


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "sim"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name, "").strip()
    if not value:
        return default

    try:
        return int(value)
    except ValueError:
        return default
