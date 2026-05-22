import asyncio
import os
import shutil
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

from app.models.vton import VtonPayload
from app.services.url_utils import absolute_url


class HuggingFaceNotConfigured(Exception):
    pass


class HuggingFaceProviderError(Exception):
    pass


HF_OUTPUT_DIR = Path("uploads") / "vton"
HF_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def is_huggingface_configured() -> bool:
    space_id = os.getenv("HF_SPACE_ID", "yisol/IDM-VTON").strip()
    return bool(space_id)


async def run_huggingface_vton(payload: VtonPayload) -> Dict[str, Any]:
    if not is_huggingface_configured():
        raise HuggingFaceNotConfigured("HF_SPACE_ID nao configurado.")

    person_url = _absolute_public_url(payload.person_image_url, "person_image_url")
    garment_url = _absolute_public_url(
        payload.garment_processed_url or payload.garment_original_url,
        "garment_processed_url",
    )

    raw_result = await asyncio.to_thread(
        _call_space,
        person_url=person_url,
        garment_url=garment_url,
    )

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


def _call_space(person_url: str, garment_url: str) -> Any:
    try:
        from gradio_client import Client, file
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
            "background": file(person_url),
            "layers": [],
            "composite": None,
        },
        garm_img=file(garment_url),
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
