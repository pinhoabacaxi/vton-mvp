import asyncio
import os
import time
from typing import Any, Dict, Optional

import httpx

from app.models.vton import VtonPayload
from app.services.url_utils import absolute_url


class ReplicateNotConfigured(Exception):
    pass


class ReplicateProviderError(Exception):
    pass


REPLICATE_BASE_URL = "https://api.replicate.com/v1"


def is_replicate_configured() -> bool:
    token = os.getenv("REPLICATE_API_TOKEN", "").strip()
    model = os.getenv("REPLICATE_MODEL", "").strip()
    version = os.getenv("REPLICATE_VERSION", "").strip()

    return bool(token and (model or version))


def _get_headers() -> Dict[str, str]:
    token = os.getenv("REPLICATE_API_TOKEN", "").strip()

    if not token:
        raise ReplicateNotConfigured("REPLICATE_API_TOKEN nao configurado.")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    prefer_wait = os.getenv("REPLICATE_PREFER_WAIT", "false").strip().lower()
    if prefer_wait in {"1", "true", "yes", "sim"}:
        headers["Prefer"] = "wait"

    return headers


def _absolute_backend_url(path_or_url: Optional[str]) -> Optional[str]:
    if not path_or_url:
        return None

    url = absolute_url(path_or_url)
    if not url.startswith(("http://", "https://")):
        return None

    return url


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


def _is_idm_vton_model(model_name: str, schema: str) -> bool:
    return schema in {"idm_vton", "idm-vton"} or (
        not schema and "idm-vton" in model_name
    )


def _build_replicate_input(payload: VtonPayload) -> Dict[str, Any]:
    garment_url = _absolute_backend_url(payload.garment_processed_url)
    person_image_url = _absolute_backend_url(payload.person_image_url)

    if not garment_url:
        raise ReplicateProviderError(
            "garment_processed_url nao esta acessivel publicamente. "
            "Configure PUBLIC_BACKEND_URL ou envie uma URL absoluta."
        )

    if not person_image_url:
        raise ReplicateProviderError(
            "person_image_url nao esta acessivel publicamente. "
            "O backend precisa gerar ou receber uma imagem HTTPS do manequim/pessoa."
        )

    prompt = (
        os.getenv("REPLICATE_GARMENT_PROMPT", "").strip()
        or "Virtual try-on preview of the garment on a neutral front-facing mannequin. "
        "Preserve garment shape, fabric and color. Clean studio background."
    )
    category = os.getenv("REPLICATE_GARMENT_CATEGORY", "upper_body").strip()
    category = category or "upper_body"
    schema = os.getenv("REPLICATE_INPUT_SCHEMA", "").strip().lower()
    model_name = os.getenv("REPLICATE_MODEL", "").strip().lower()

    if _is_idm_vton_model(model_name, schema):
        return {
            "human_img": person_image_url,
            "garm_img": garment_url,
            "garment_des": prompt,
            "category": category,
            "crop": _env_bool("REPLICATE_AUTO_CROP", False),
            "force_dc": _env_bool("REPLICATE_FORCE_DC", False),
            "mask_only": _env_bool("REPLICATE_MASK_ONLY", False),
            "steps": _env_int(
                "REPLICATE_STEPS",
                _env_int("REPLICATE_DENOISE_STEPS", 30),
            ),
            "seed": _env_int("REPLICATE_SEED", 42),
        }

    return {
        "person_image": person_image_url,
        "garment_image": garment_url,
        "prompt": prompt,
        "category": category,
        "fit_notes": [zone.model_dump() for zone in payload.fit_zones],
        "measurements": {
            "height_cm": payload.mannequin.height_cm,
            "chest_cm": payload.mannequin.chest_cm,
            "waist_cm": payload.mannequin.waist_cm,
            "hip_cm": payload.mannequin.hip_cm,
            "shoulder_cm": payload.mannequin.shoulder_cm,
            "sleeve_cm": payload.mannequin.sleeve_cm,
            "biceps_cm": payload.mannequin.biceps_cm,
            "top_length_cm": payload.mannequin.top_length_cm,
            "inseam_cm": payload.mannequin.inseam_cm,
            "thigh_cm": payload.mannequin.thigh_cm,
            "rise_cm": payload.mannequin.rise_cm,
            "wrist_cm": payload.mannequin.wrist_cm,
        },
    }


async def run_replicate_vton(payload: VtonPayload) -> Dict[str, Any]:
    token = os.getenv("REPLICATE_API_TOKEN", "").strip()
    model = os.getenv("REPLICATE_MODEL", "").strip()
    version = os.getenv("REPLICATE_VERSION", "").strip()

    if not token:
        raise ReplicateNotConfigured("REPLICATE_API_TOKEN nao configurado.")

    if not model and not version:
        raise ReplicateNotConfigured("Configure REPLICATE_MODEL ou REPLICATE_VERSION.")

    prediction = await _create_prediction(
        model=model,
        version=version,
        input_data=_build_replicate_input(payload),
    )

    prediction_id = prediction.get("id")
    status = prediction.get("status")

    if status == "succeeded":
        return prediction

    if not prediction_id:
        raise ReplicateProviderError(
            f"Prediction criada sem id. Resposta: {prediction}"
        )

    return await _poll_prediction(prediction_id)


async def _create_prediction(
    model: str,
    version: str,
    input_data: Dict[str, Any],
) -> Dict[str, Any]:
    headers = _get_headers()

    async with httpx.AsyncClient(timeout=120) as client:
        if version:
            response = await _post_prediction_with_retry(
                client=client,
                url=f"{REPLICATE_BASE_URL}/predictions",
                body={
                    "version": version,
                    "input": input_data,
                },
                headers=headers,
            )
        elif model:
            url = f"{REPLICATE_BASE_URL}/models/{model}/predictions"
            body = {
                "input": input_data,
            }

            response = await _post_prediction_with_retry(
                client=client,
                url=url,
                body=body,
                headers=headers,
            )

            if response.status_code == 404:
                latest_version = await _resolve_latest_model_version(
                    client=client,
                    model=model,
                    headers=headers,
                )
                response = await _post_prediction_with_retry(
                    client=client,
                    url=f"{REPLICATE_BASE_URL}/predictions",
                    body={
                        "version": latest_version,
                        "input": input_data,
                    },
                    headers=headers,
                )
        else:
            url = f"{REPLICATE_BASE_URL}/predictions"
            body = {
                "version": version,
                "input": input_data,
            }
            response = await _post_prediction_with_retry(
                client=client,
                url=url,
                body=body,
                headers=headers,
            )

    if response.status_code >= 400:
        raise ReplicateProviderError(
            f"Erro ao criar prediction na Replicate: {response.status_code} {response.text}"
        )

    return response.json()


async def _post_prediction_with_retry(
    client: httpx.AsyncClient,
    url: str,
    body: Dict[str, Any],
    headers: Dict[str, str],
) -> httpx.Response:
    max_retries = _env_int("REPLICATE_CREATE_MAX_RETRIES", 2)

    for attempt in range(max_retries + 1):
        response = await client.post(url, json=body, headers=headers)

        if response.status_code != 429 or attempt >= max_retries:
            return response

        await asyncio.sleep(_replicate_retry_after_seconds(response))

    return response


def _replicate_retry_after_seconds(response: httpx.Response) -> float:
    header_value = response.headers.get("retry-after") or response.headers.get("Retry-After")
    if header_value:
        try:
            return max(1.0, min(30.0, float(header_value)))
        except ValueError:
            pass

    try:
        data = response.json()
    except Exception:
        data = {}

    retry_after = data.get("retry_after") if isinstance(data, dict) else None
    try:
        return max(1.0, min(30.0, float(retry_after)))
    except (TypeError, ValueError):
        return 10.0


async def _resolve_latest_model_version(
    client: httpx.AsyncClient,
    model: str,
    headers: Dict[str, str],
) -> str:
    parts = model.split("/", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ReplicateProviderError(
            "REPLICATE_MODEL deve estar no formato owner/model ou defina REPLICATE_VERSION."
        )

    response = await client.get(
        f"{REPLICATE_BASE_URL}/models/{parts[0]}/{parts[1]}",
        headers=headers,
    )

    if response.status_code >= 400:
        raise ReplicateProviderError(
            f"Modelo Replicate nao encontrado ou indisponivel: {response.status_code} {response.text}"
        )

    data = response.json()
    latest_version = data.get("latest_version")
    if isinstance(latest_version, dict):
        version_id = latest_version.get("id")
    else:
        version_id = latest_version

    if not isinstance(version_id, str) or not version_id:
        raise ReplicateProviderError(
            "Modelo Replicate sem latest_version. Defina REPLICATE_VERSION explicitamente."
        )

    return version_id


async def _poll_prediction(prediction_id: str) -> Dict[str, Any]:
    headers = _get_headers()

    timeout_seconds = _env_int("REPLICATE_POLL_TIMEOUT_SECONDS", 180)
    interval_seconds = float(os.getenv("REPLICATE_POLL_INTERVAL_SECONDS", "3"))

    deadline = time.time() + timeout_seconds

    async with httpx.AsyncClient(timeout=60) as client:
        while time.time() < deadline:
            response = await client.get(
                f"{REPLICATE_BASE_URL}/predictions/{prediction_id}",
                headers=headers,
            )

            if response.status_code >= 400:
                raise ReplicateProviderError(
                    f"Erro ao consultar prediction: {response.status_code} {response.text}"
                )

            data = response.json()
            status = data.get("status")

            if status == "succeeded":
                return data

            if status in {"failed", "canceled"}:
                raise ReplicateProviderError(
                    f"Prediction terminou com status {status}: {data}"
                )

            await asyncio.sleep(interval_seconds)

    raise ReplicateProviderError(
        f"Timeout aguardando prediction {prediction_id}."
    )


def extract_replicate_result_url(raw_response: Dict[str, Any]) -> Optional[str]:
    output = raw_response.get("output")

    if isinstance(output, str) and output.startswith(("http://", "https://", "/")):
        return output

    if isinstance(output, list):
        for item in output:
            if isinstance(item, str) and item.startswith(("http://", "https://", "/")):
                return item
            if isinstance(item, dict):
                for key in ["url", "image", "image_url", "output_url", "result_url"]:
                    value = item.get(key)
                    if isinstance(value, str) and value.startswith(("http://", "https://", "/")):
                        return value

    if isinstance(output, dict):
        for key in ["url", "image", "image_url", "output_url", "result_url"]:
            value = output.get(key)
            if isinstance(value, str) and value.startswith(("http://", "https://", "/")):
                return value

    for key in ["result_url", "image_url", "output_url", "url"]:
        value = raw_response.get(key)
        if isinstance(value, str) and value.startswith(("http://", "https://", "/")):
            return value

    return None
