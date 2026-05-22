import os
from typing import Any, Dict, Optional

import httpx

from app.models.vton import VtonPayload
from app.services.replicate_vton_provider import (
    ReplicateNotConfigured,
    ReplicateProviderError,
    extract_replicate_result_url,
    is_replicate_configured,
    run_replicate_vton,
)


class ExternalVtonNotConfigured(Exception):
    pass


class ExternalVtonProviderError(Exception):
    pass


def get_vton_provider_name() -> str:
    configured_provider = os.getenv("VTON_PROVIDER", "mock").strip().lower() or "mock"

    if configured_provider == "auto":
        if is_replicate_configured():
            return "replicate"

        api_url = os.getenv("VTON_API_URL", "").strip()
        api_key = os.getenv("VTON_API_KEY", "").strip()
        if api_url and api_key:
            return "generic"

        return "mock"

    return configured_provider


def is_external_vton_configured() -> bool:
    provider = get_vton_provider_name()

    if provider == "replicate":
        return is_replicate_configured()

    if provider == "mock":
        return False

    api_url = os.getenv("VTON_API_URL", "").strip()
    api_key = os.getenv("VTON_API_KEY", "").strip()

    return bool(api_url and api_key)


async def run_external_vton(payload: VtonPayload) -> Dict[str, Any]:
    provider = get_vton_provider_name()

    if provider == "replicate":
        try:
            return await run_replicate_vton(payload)
        except ReplicateNotConfigured as error:
            raise ExternalVtonNotConfigured(str(error))
        except ReplicateProviderError as error:
            raise ExternalVtonProviderError(str(error))

    return await _run_generic_http_vton(payload)


async def _run_generic_http_vton(payload: VtonPayload) -> Dict[str, Any]:
    api_url = os.getenv("VTON_API_URL", "").strip()
    api_key = os.getenv("VTON_API_KEY", "").strip()
    provider = get_vton_provider_name()

    if not api_url or not api_key:
        raise ExternalVtonNotConfigured(
            "VTON_API_URL ou VTON_API_KEY não configurados."
        )

    request_body = {
        "provider": provider,
        "task": "virtual_try_on",
        "payload": payload.model_dump(),
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            api_url,
            json=request_body,
            headers=headers,
        )

    if response.status_code >= 400:
        raise ExternalVtonProviderError(
            f"API VTON externa retornou status {response.status_code}: {response.text}"
        )

    try:
        return response.json()
    except Exception as error:
        raise ExternalVtonProviderError(
            f"API VTON externa não retornou JSON válido: {error}"
        )


def extract_result_url(raw_response: Dict[str, Any]) -> Optional[str]:
    provider = get_vton_provider_name()

    if provider == "replicate":
        return extract_replicate_result_url(raw_response)

    direct_keys = [
        "result_url",
        "image_url",
        "output_url",
        "url",
    ]

    for key in direct_keys:
        value = raw_response.get(key)
        if isinstance(value, str) and value.startswith(("http://", "https://", "/")):
            return value

    output = raw_response.get("output")

    if isinstance(output, str) and output.startswith(("http://", "https://", "/")):
        return output

    if isinstance(output, list):
        for item in output:
            if isinstance(item, str) and item.startswith(("http://", "https://", "/")):
                return item

    if isinstance(output, dict):
        for key in direct_keys:
            value = output.get(key)
            if isinstance(value, str) and value.startswith(("http://", "https://", "/")):
                return value

    return None
