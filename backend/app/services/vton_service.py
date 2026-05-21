from pathlib import Path
from uuid import uuid4
import asyncio
from typing import Dict, List, Optional

from PIL import Image, ImageDraw

from app.models.vton import (
    VtonPrepareInput,
    VtonPayload,
    VtonMockInput,
    VtonMockResult,
    VtonRunInput,
    VtonRunResult,
    VtonTaskCreated,
    VtonTaskStatusResponse,
)
from app.models.product import FitZone
from app.services.external_vton_provider import (
    ExternalVtonNotConfigured,
    ExternalVtonProviderError,
    extract_result_url,
    get_vton_provider_name,
    is_external_vton_configured,
    run_external_vton,
)
from app.services.url_utils import absolute_url


UPLOAD_DIR = Path("uploads")
VTON_DIR = UPLOAD_DIR / "vton"
VTON_DIR.mkdir(parents=True, exist_ok=True)
VTON_TASK_POLL_SECONDS = 2
_VTON_TASKS: Dict[str, VtonTaskStatusResponse] = {}


def prepare_vton_payload(data: VtonPrepareInput) -> VtonPayload:
    garment_processed_url = (
        absolute_url(data.garment_processed_url)
        if data.garment_processed_url
        else None
    )
    garment_original_url = (
        absolute_url(data.garment_original_url)
        if data.garment_original_url
        else None
    )
    person_image_url = (
        absolute_url(data.person_image_url)
        if data.person_image_url
        else None
    )

    notes = [
        "Payload preparado para integração futura com API VTON.",
        "Para MVP, recomenda-se começar com render frontal 2D antes de tentar projeção 3D real.",
    ]

    if data.fit_zones:
        notes.append("Fit zones incluídas para futura orientação de caimento e heatmap.")

    if garment_processed_url:
        notes.append("Imagem de roupa sem fundo disponível para composição/VTON.")

    if person_image_url:
        notes.append("Imagem frontal do manequim adicionada ao payload como person_image_url.")

    api_ready_payload = {
        "person_representation": {
            "type": "parametric_mannequin",
            "height_cm": data.mannequin.height_cm,
            "chest_cm": data.mannequin.chest_cm,
            "waist_cm": data.mannequin.waist_cm,
            "hip_cm": data.mannequin.hip_cm,
            "skin_tone": data.mannequin.skin_tone,
            "base_model_id": data.mannequin.base_model_id,
        },
        "person_image_url": person_image_url,
        "garment": {
            "processed_url": garment_processed_url,
            "original_url": garment_original_url,
        },
        "fit_analysis": [
            {
                "zone": zone.zone,
                "status": zone.status,
                "color": zone.color,
                "difference_cm": zone.difference_cm,
                "message": zone.message,
            }
            for zone in data.fit_zones
        ],
        "future_vton_mode": "front_view_diffusion",
    }

    return VtonPayload(
        mannequin=data.mannequin,
        garment_processed_url=garment_processed_url,
        garment_original_url=garment_original_url,
        person_image_url=person_image_url,
        fit_zones=data.fit_zones,
        render_mode="front_view",
        recommended_view_count=4,
        notes=notes,
        api_ready_payload=api_ready_payload,
    )


def create_mock_vton_result(data: VtonMockInput) -> VtonMockResult:
    filename = f"vton_mock_{uuid4().hex}.png"
    output_path = VTON_DIR / filename

    image = Image.new("RGBA", (900, 1200), "#170b25")
    draw = ImageDraw.Draw(image)

    _draw_background(draw)
    _draw_mannequin(draw, data.payload)
    _draw_garment_overlay(draw, data.payload)
    _draw_fit_labels(draw, data.payload.fit_zones)

    image.save(output_path, "PNG")

    return VtonMockResult(
        result_url=absolute_url(f"/uploads/vton/{filename}"),
        result_path=str(output_path),
        message="Resultado VTON mock gerado com sucesso.",
    )


async def run_vton(data: VtonRunInput) -> VtonRunResult:
    provider = get_vton_provider_name()

    if data.mode == "mock":
        mock = create_mock_vton_result(VtonMockInput(payload=data.payload))

        return VtonRunResult(
            result_url=mock.result_url,
            result_path=mock.result_path,
            provider="local_mock",
            mode_requested=data.mode,
            status="succeeded",
            used_fallback=False,
            success=True,
            message=mock.message,
            raw_response=None,
        )

    if data.mode == "external":
        return await _run_external_only(data, provider)

    if data.mode == "auto":
        if is_external_vton_configured():
            try:
                return await _run_external_only(data, provider)
            except Exception as error:
                mock = create_mock_vton_result(VtonMockInput(payload=data.payload))

                return VtonRunResult(
                    result_url=mock.result_url,
                    result_path=mock.result_path,
                    provider="local_mock",
                    mode_requested=data.mode,
                    status="succeeded",
                    used_fallback=True,
                    success=True,
                    message=f"API externa falhou. Fallback mock usado. Erro original: {error}",
                    raw_response=None,
                )

        mock = create_mock_vton_result(VtonMockInput(payload=data.payload))

        return VtonRunResult(
            result_url=mock.result_url,
            result_path=mock.result_path,
            provider="local_mock",
            mode_requested=data.mode,
            status="succeeded",
            used_fallback=True,
            success=True,
            message="API VTON externa não configurada. Fallback mock usado.",
            raw_response=None,
        )

    mock = create_mock_vton_result(VtonMockInput(payload=data.payload))

    return VtonRunResult(
        result_url=mock.result_url,
        result_path=mock.result_path,
        provider="local_mock",
        mode_requested="mock",
        status="succeeded",
        used_fallback=True,
        success=True,
        message="Modo inválido. Fallback mock usado.",
        raw_response=None,
    )


def create_vton_task(data: VtonRunInput) -> VtonTaskCreated:
    task_id = uuid4().hex
    _VTON_TASKS[task_id] = VtonTaskStatusResponse(
        task_id=task_id,
        state="queued",
        poll_after_seconds=VTON_TASK_POLL_SECONDS,
    )

    asyncio.create_task(_execute_vton_task(task_id, data))

    return VtonTaskCreated(
        task_id=task_id,
        state="queued",
        poll_after_seconds=VTON_TASK_POLL_SECONDS,
        message="Tarefa VTON criada. Consulte o status ate o resultado ficar pronto.",
    )


def get_vton_task(task_id: str) -> Optional[VtonTaskStatusResponse]:
    return _VTON_TASKS.get(task_id)


async def _execute_vton_task(task_id: str, data: VtonRunInput) -> None:
    _VTON_TASKS[task_id] = VtonTaskStatusResponse(
        task_id=task_id,
        state="running",
        poll_after_seconds=VTON_TASK_POLL_SECONDS,
    )

    try:
        result = await run_vton(data)
        _VTON_TASKS[task_id] = VtonTaskStatusResponse(
            task_id=task_id,
            state="succeeded",
            result=result,
            poll_after_seconds=VTON_TASK_POLL_SECONDS,
        )
    except ExternalVtonNotConfigured as error:
        _VTON_TASKS[task_id] = VtonTaskStatusResponse(
            task_id=task_id,
            state="failed",
            error=f"Provider externo nao configurado: {error}",
            poll_after_seconds=VTON_TASK_POLL_SECONDS,
        )
    except ExternalVtonProviderError as error:
        _VTON_TASKS[task_id] = VtonTaskStatusResponse(
            task_id=task_id,
            state="failed",
            error=f"Falha do provider VTON externo: {error}",
            poll_after_seconds=VTON_TASK_POLL_SECONDS,
        )
    except Exception as error:
        _VTON_TASKS[task_id] = VtonTaskStatusResponse(
            task_id=task_id,
            state="failed",
            error=f"Erro ao executar VTON: {type(error).__name__}: {error}",
            poll_after_seconds=VTON_TASK_POLL_SECONDS,
        )


async def _run_external_only(data: VtonRunInput, provider: str) -> VtonRunResult:
    raw_response = await run_external_vton(data.payload)
    result_url = extract_result_url(raw_response)
    status = None

    if isinstance(raw_response, dict):
        status = raw_response.get("status")

    if not result_url:
        raise ExternalVtonProviderError(
            "API externa respondeu, mas nenhuma URL de resultado foi encontrada."
        )

    result_url = absolute_url(result_url)

    return VtonRunResult(
        result_url=result_url,
        result_path=None,
        provider=provider,
        mode_requested=data.mode,
        status=status,
        used_fallback=False,
        success=True,
        message=f"Resultado VTON externo recebido com sucesso via {provider}.",
        raw_response=raw_response,
    )


def _draw_background(draw: ImageDraw.ImageDraw) -> None:
    draw.rectangle((0, 0, 900, 1200), fill="#170b25")
    draw.ellipse((-200, -160, 520, 520), fill="#3b1c5c")
    draw.ellipse((420, 760, 1100, 1380), fill="#2e1065")
    draw.text((40, 40), "VTON MOCK", fill="#e9d5ff")


def _draw_mannequin(draw: ImageDraw.ImageDraw, payload: VtonPayload) -> None:
    mannequin = payload.mannequin
    skin = _skin_color(mannequin.skin_tone)

    center_x = 450
    head_y = 180

    shoulder_width = int(210 * getattr(mannequin, "shoulder_scale", 1))
    chest_width = int(190 * getattr(mannequin, "chest_scale", 1))
    waist_width = int(145 * getattr(mannequin, "waist_scale", 1))
    hip_width = int(205 * getattr(mannequin, "hip_scale", 1))

    draw.ellipse((center_x - 65, head_y - 65, center_x + 65, head_y + 65), fill=skin)

    draw.polygon(
        [
            (center_x - shoulder_width, 310),
            (center_x + shoulder_width, 310),
            (center_x + chest_width, 510),
            (center_x + waist_width, 650),
            (center_x - waist_width, 650),
            (center_x - chest_width, 510),
        ],
        fill=skin,
    )

    draw.polygon(
        [
            (center_x - waist_width, 650),
            (center_x + waist_width, 650),
            (center_x + hip_width, 780),
            (center_x + 90, 850),
            (center_x - 90, 850),
            (center_x - hip_width, 780),
        ],
        fill=skin,
    )

    draw.rounded_rectangle((center_x - 250, 320, center_x - 180, 760), radius=35, fill=skin)
    draw.rounded_rectangle((center_x + 180, 320, center_x + 250, 760), radius=35, fill=skin)

    draw.rounded_rectangle((center_x - 110, 820, center_x - 35, 1110), radius=35, fill=skin)
    draw.rounded_rectangle((center_x + 35, 820, center_x + 110, 1110), radius=35, fill=skin)


def _draw_garment_overlay(draw: ImageDraw.ImageDraw, payload: VtonPayload) -> None:
    center_x = 450
    has_garment = payload.garment_processed_url is not None

    garment_color = "#8b5cf6" if has_garment else "#6d28d9"
    outline = "#f5d0fe"

    draw.polygon(
        [
            (center_x - 210, 300),
            (center_x + 210, 300),
            (center_x + 170, 660),
            (center_x + 95, 760),
            (center_x - 95, 760),
            (center_x - 170, 660),
        ],
        fill=garment_color,
        outline=outline,
    )

    draw.text((center_x - 155, 455), "ROUPA MOCK", fill="#ffffff")

    if not has_garment:
        draw.text((center_x - 205, 500), "sem imagem processada", fill="#fef3c7")


def _draw_fit_labels(draw: ImageDraw.ImageDraw, zones: List[FitZone]) -> None:
    y_map = {
        "chest": 370,
        "waist": 600,
        "hip": 760,
    }

    label_map = {
        "chest": "Tórax",
        "waist": "Cintura",
        "hip": "Quadril",
    }

    for zone in zones:
        y = y_map.get(zone.zone, 920)
        color = _heat_color(zone.color)

        draw.rounded_rectangle((40, y, 290, y + 58), radius=16, fill=color)
        draw.text(
            (58, y + 16),
            f"{label_map.get(zone.zone, zone.zone)}: {zone.status}",
            fill="#111827",
        )


def _skin_color(tone: str) -> str:
    if tone == "light":
        return "#f2c7a5"
    if tone == "medium":
        return "#c6865a"
    if tone == "dark":
        return "#6b3f2a"
    if tone == "deep":
        return "#3a241c"
    return "#c6865a"


def _heat_color(color: str) -> str:
    if color == "red":
        return "#fca5a5"
    if color == "yellow":
        return "#fde68a"
    if color == "green":
        return "#86efac"
    if color == "gray":
        return "#d1d5db"
    return "#c4b5fd"
