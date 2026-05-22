import asyncio
import logging
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen
from uuid import uuid4

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from app.models.product import FitZone
from app.models.vton import (
    VtonMockInput,
    VtonMockResult,
    VtonPayload,
    VtonPrepareInput,
    VtonRunInput,
    VtonRunResult,
    VtonTaskCreated,
    VtonTaskStatusResponse,
)
from app.services.external_vton_provider import (
    ExternalVtonNotConfigured,
    ExternalVtonProviderError,
    extract_result_url,
    get_vton_provider_name,
    is_external_vton_configured,
    run_external_vton,
)
from app.services.image_processor import UPLOAD_DIR, normalize_garment_visual
from app.services.mannequin_renderer import CANVAS_SIZE, render_mannequin_scene
from app.services.url_utils import absolute_url
from app.services.vton_render_pipeline import (
    GarmentRenderContext,
    MannequinGarmentRenderer,
)


VTON_DIR = UPLOAD_DIR / "vton"
VTON_DIR.mkdir(parents=True, exist_ok=True)
PERSON_RENDER_DIR = UPLOAD_DIR / "mannequin"
PERSON_RENDER_DIR.mkdir(parents=True, exist_ok=True)
VTON_TASK_POLL_SECONDS = 2
_VTON_TASKS: Dict[str, VtonTaskStatusResponse] = {}
_GARMENT_RENDERER = MannequinGarmentRenderer()
LOGGER = logging.getLogger(__name__)


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
        "Payload preparado para integracao futura com API VTON.",
        "O mock local usa composicao por alpha, warp leve e sombra do manequim.",
    ]

    if data.fit_zones:
        notes.append("Fit zones incluidas para futura orientacao de caimento e heatmap.")

    if garment_processed_url:
        notes.append("Imagem de roupa sem fundo disponivel para composicao/VTON.")

    if person_image_url:
        notes.append("Imagem frontal do manequim adicionada ao payload como person_image_url.")

    api_ready_payload = {
        "person_representation": {
            "type": "parametric_mannequin",
            "height_cm": data.mannequin.height_cm,
            "chest_cm": data.mannequin.chest_cm,
            "waist_cm": data.mannequin.waist_cm,
            "hip_cm": data.mannequin.hip_cm,
            "shoulder_cm": data.mannequin.shoulder_cm,
            "sleeve_cm": data.mannequin.sleeve_cm,
            "biceps_cm": data.mannequin.biceps_cm,
            "top_length_cm": data.mannequin.top_length_cm,
            "inseam_cm": data.mannequin.inseam_cm,
            "thigh_cm": data.mannequin.thigh_cm,
            "rise_cm": data.mannequin.rise_cm,
            "wrist_cm": data.mannequin.wrist_cm,
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

    image, body_alpha, body_shadow, body_light = render_mannequin_scene(
        data.payload.mannequin,
        size=CANVAS_SIZE,
        include_label=False,
    )

    image = _apply_fit_heatmap_overlay(image, body_alpha, data.payload.fit_zones)

    image = _composite_garment_on_body(
        image=image,
        body_alpha=body_alpha,
        body_shadow=body_shadow,
        body_light=body_light,
        payload=data.payload,
    )

    draw = ImageDraw.Draw(image)
    _draw_fit_labels(draw, data.payload.fit_zones)

    image.save(output_path, "PNG", optimize=True)

    return VtonMockResult(
        result_url=absolute_url(f"/uploads/vton/{filename}"),
        result_path=str(output_path),
        message="Resultado VTON mock gerado com composicao organica.",
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
                LOGGER.warning(
                    "External VTON provider failed; using local mock fallback: %s",
                    error,
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
                    message=(
                        "A prévia realista não ficou disponível agora. "
                        "Geramos uma prévia rápida para você continuar."
                    ),
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
            message=(
                "A prévia realista ainda não está configurada. "
                "Geramos uma prévia rápida para você continuar."
            ),
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
        message="Modo invalido. Fallback mock usado.",
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
    public_payload = _ensure_public_vton_assets(data.payload)
    raw_response = await run_external_vton(public_payload)
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


def _ensure_public_vton_assets(payload: VtonPayload) -> VtonPayload:
    garment_processed_url = (
        absolute_url(payload.garment_processed_url)
        if payload.garment_processed_url
        else None
    )
    garment_original_url = (
        absolute_url(payload.garment_original_url)
        if payload.garment_original_url
        else None
    )
    person_image_url = (
        absolute_url(payload.person_image_url)
        if payload.person_image_url
        else None
    )

    if not garment_processed_url and garment_original_url:
        garment_processed_url = garment_original_url

    if not person_image_url:
        person_image_url = _create_public_person_image(payload)

    api_ready_payload = dict(payload.api_ready_payload)
    api_ready_payload["person_image_url"] = person_image_url

    garment = dict(api_ready_payload.get("garment") or {})
    garment["processed_url"] = garment_processed_url
    garment["original_url"] = garment_original_url
    api_ready_payload["garment"] = garment

    return payload.model_copy(
        update={
            "garment_processed_url": garment_processed_url,
            "garment_original_url": garment_original_url,
            "person_image_url": person_image_url,
            "api_ready_payload": api_ready_payload,
        }
    )


def _create_public_person_image(payload: VtonPayload) -> str:
    filename = f"replicate_person_{uuid4().hex}.png"
    output_path = PERSON_RENDER_DIR / filename

    image, _, _, _ = render_mannequin_scene(
        payload.mannequin,
        size=CANVAS_SIZE,
        include_label=False,
    )
    image.save(output_path, "PNG", optimize=True)

    return absolute_url(f"/uploads/mannequin/{filename}")


def _composite_garment_on_body(
    image: Image.Image,
    body_alpha: Image.Image,
    body_shadow: Image.Image,
    body_light: Image.Image,
    payload: VtonPayload,
) -> Image.Image:
    garment = _load_processed_garment(payload.garment_processed_url)
    foreground_occlusion = _build_foreground_occlusion_mask(payload.mannequin, image.size)

    if garment is None:
        fallback = _build_parametric_garment_placeholder(payload)
        fallback = _GARMENT_RENDERER.render(
            fallback,
            GarmentRenderContext(
                mannequin=payload.mannequin,
                body_alpha=body_alpha,
                shadow_map_alpha=body_shadow,
                light_map_rgba=body_light,
                occlusion_mask_alpha=foreground_occlusion,
                fit_zones=payload.fit_zones,
                shadow_intensity=0.56,
                highlight_intensity=0.34,
                warp_strength=0.62,
                bump_strength=0.16,
                curve_hem=False,
            ),
        )
        return Image.alpha_composite(image, fallback)

    garment = normalize_garment_visual(_crop_to_alpha(garment))
    if _alpha_is_mostly_opaque(garment):
        garment = _apply_soft_garment_silhouette(garment)

    garment, left, top = _fit_garment_to_body(garment, payload)

    garment_box = (left, top, left + garment.width, top + garment.height)
    garment = _GARMENT_RENDERER.render(
        garment,
        GarmentRenderContext(
            mannequin=payload.mannequin,
            body_alpha=body_alpha.crop(garment_box),
            shadow_map_alpha=body_shadow.crop(garment_box),
            light_map_rgba=body_light.crop(garment_box),
            occlusion_mask_alpha=foreground_occlusion.crop(garment_box),
            fit_zones=payload.fit_zones,
            shadow_intensity=0.62,
            highlight_intensity=0.36,
            warp_strength=1.0,
            bump_strength=0.24,
            curve_hem=True,
        ),
    )

    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    layer.paste(garment, (left, top), garment)
    return Image.alpha_composite(image, layer)


def _load_processed_garment(path_or_url: Optional[str]) -> Optional[Image.Image]:
    local_path = _resolve_upload_path(path_or_url)

    if local_path and local_path.exists():
        try:
            with Image.open(local_path) as image:
                return image.convert("RGBA")
        except Exception:
            return None

    if path_or_url and path_or_url.startswith(("http://", "https://")):
        return _download_garment_image(path_or_url)

    return None


def _download_garment_image(url: str) -> Optional[Image.Image]:
    try:
        request = Request(
            url,
            headers={"User-Agent": "VTON-MVP/1.0 image-preview"},
        )
        with urlopen(request, timeout=12) as response:
            payload = response.read(8 * 1024 * 1024)

        with Image.open(BytesIO(payload)) as image:
            return image.convert("RGBA")
    except Exception:
        return None


def _resolve_upload_path(path_or_url: Optional[str]) -> Optional[Path]:
    if not path_or_url:
        return None

    parsed = urlparse(path_or_url)

    if not parsed.scheme:
        direct_path = Path(path_or_url)
        if direct_path.exists():
            return direct_path

    normalized = parsed.path if parsed.scheme else path_or_url
    normalized = normalized.replace("\\", "/")

    if "uploads/" not in normalized:
        return None

    relative = normalized.split("uploads/", 1)[1].lstrip("/")
    return UPLOAD_DIR / unquote(relative)


def _crop_to_alpha(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    bbox = rgba.getchannel("A").getbbox()

    if not bbox:
        return rgba

    margin = 10
    left = max(0, bbox[0] - margin)
    top = max(0, bbox[1] - margin)
    right = min(rgba.width, bbox[2] + margin)
    bottom = min(rgba.height, bbox[3] + margin)
    return rgba.crop((left, top, right, bottom))


def _alpha_is_mostly_opaque(image: Image.Image) -> bool:
    alpha = image.getchannel("A")
    extrema = alpha.getextrema()

    if extrema[0] < 245:
        return False

    opaque_bbox = alpha.point(lambda value: 255 if value > 245 else 0).getbbox()
    return opaque_bbox == (0, 0, image.width, image.height)


def _apply_soft_garment_silhouette(image: Image.Image) -> Image.Image:
    width, height = image.size
    mask = Image.new("L", image.size, 0)
    draw = ImageDraw.Draw(mask)

    body_points = [
        (width * 0.20, height * 0.08),
        (width * 0.80, height * 0.08),
        (width * 0.88, height * 0.32),
        (width * 0.78, height * 0.88),
        (width * 0.58, height * 0.98),
        (width * 0.42, height * 0.98),
        (width * 0.22, height * 0.88),
        (width * 0.12, height * 0.32),
    ]
    draw.polygon([(int(x), int(y)) for x, y in body_points], fill=255)

    left_sleeve = [
        (width * 0.20, height * 0.10),
        (width * 0.06, height * 0.20),
        (width * 0.12, height * 0.48),
        (width * 0.26, height * 0.40),
    ]
    right_sleeve = [(width - x, y) for x, y in left_sleeve]
    draw.polygon([(int(x), int(y)) for x, y in left_sleeve], fill=255)
    draw.polygon([(int(x), int(y)) for x, y in right_sleeve], fill=255)
    draw.ellipse((width * 0.39, height * -0.04, width * 0.61, height * 0.18), fill=0)

    mask = mask.filter(ImageFilter.GaussianBlur(radius=max(1.0, width * 0.005)))
    alpha = ImageChops.multiply(image.getchannel("A"), mask)
    return Image.merge("RGBA", (*image.convert("RGB").split(), alpha))


def _fit_garment_to_body(
    garment: Image.Image,
    payload: VtonPayload,
) -> tuple[Image.Image, int, int]:
    target_left, target_top, target_right, target_bottom = _garment_target_box(payload)
    target_width = target_right - target_left
    target_height = target_bottom - target_top

    scale = min(
        target_width / max(1, garment.width),
        target_height / max(1, garment.height),
    )
    scale = max(0.1, scale)
    new_size = (
        max(1, int(garment.width * scale)),
        max(1, int(garment.height * scale)),
    )

    resized = garment.resize(new_size, Image.Resampling.LANCZOS)
    left = target_left + (target_width - resized.width) // 2
    top = target_top + int((target_height - resized.height) * 0.18)
    return resized, left, top


def _garment_target_box(payload: VtonPayload) -> tuple[int, int, int, int]:
    mannequin = payload.mannequin
    center_x = CANVAS_SIZE[0] // 2

    shoulder_half = int(172 * _bounded_scale(getattr(mannequin, "shoulder_scale", 1.0), 0.74, 1.32))
    chest_half = int(164 * _bounded_scale(getattr(mannequin, "chest_scale", 1.0), 0.74, 1.36))
    waist_half = int(122 * _bounded_scale(getattr(mannequin, "waist_scale", 1.0), 0.72, 1.42))

    width_multiplier, bottom_offset = _fit_target_adjustments(payload.fit_zones)

    target_width = int(max(300, shoulder_half * 1.92, chest_half * 2.06, waist_half * 2.20))
    target_width = int(target_width * width_multiplier)
    target_width = min(500, target_width)
    target_top = 310
    target_bottom = min(820, 760 + bottom_offset)

    return (
        center_x - target_width // 2,
        target_top,
        center_x + target_width // 2,
        target_bottom,
    )


def _fit_target_adjustments(zones: List[FitZone]) -> tuple[float, int]:
    tightness = 0.0
    looseness = 0.0

    for zone in zones:
        status = (zone.status or "").lower()
        pressure = abs(float(zone.pressure_score or 0.0))
        if status in {"apertado", "too_small", "tight"} or zone.color == "red":
            tightness = max(tightness, 0.40 + pressure * 0.35)
        elif status in {"folgado", "loose"} or zone.color in {"green", "blue"}:
            looseness = max(looseness, 0.30 + pressure * 0.26)

    tightness = min(1.0, tightness)
    looseness = min(1.0, looseness)
    width_multiplier = max(0.96, min(1.10, 1.0 + looseness * 0.075 - tightness * 0.025))
    bottom_offset = int(looseness * 34 - tightness * 8)
    return width_multiplier, bottom_offset


def _build_foreground_occlusion_mask(mannequin, size: tuple[int, int]) -> Image.Image:
    width, height = size
    center_x = width // 2
    shoulder_half = int(172 * _bounded_scale(getattr(mannequin, "shoulder_scale", 1.0), 0.74, 1.32))
    arm_scale = _bounded_scale(getattr(mannequin, "arm_scale", 1.0), 0.82, 1.22)
    biceps_scale = _bounded_scale(getattr(mannequin, "biceps_scale", 1.0), 0.72, 1.55)
    forearm_half = int(26 * arm_scale)
    hand_half = int(32 * arm_scale)
    y0 = int(height * 0.43)
    y1 = int(height * 0.66)
    hand_y = int(height * 0.675)

    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)

    for side in (-1, 1):
        arm_x = center_x + side * int(shoulder_half * 1.04)
        elbow_x = center_x + side * int(shoulder_half * (1.08 + (biceps_scale - 1.0) * 0.04))
        draw.line((arm_x, y0, elbow_x, y1), fill=82, width=max(18, forearm_half * 2))
        draw.ellipse(
            (
                elbow_x - hand_half,
                hand_y - hand_half,
                elbow_x + hand_half,
                hand_y + hand_half * 1.25,
            ),
            fill=116,
        )

    return mask.filter(ImageFilter.GaussianBlur(radius=7))


def _build_parametric_garment_placeholder(payload: VtonPayload) -> Image.Image:
    mask = Image.new("L", CANVAS_SIZE, 0)
    draw = ImageDraw.Draw(mask)
    center_x = CANVAS_SIZE[0] // 2
    left, top, right, bottom = _garment_target_box(payload)
    width = right - left
    height = bottom - top
    hem_curve = int(height * 0.055)

    points = [
        (left + width * 0.18, top + height * 0.035),
        (right - width * 0.18, top + height * 0.035),
        (right - width * 0.08, top + height * 0.28),
        (right - width * 0.13, top + height * 0.62),
        (right - width * 0.20, bottom - hem_curve),
        (center_x + width * 0.10, bottom),
        (center_x - width * 0.10, bottom),
        (left + width * 0.20, bottom - hem_curve),
        (left + width * 0.13, top + height * 0.62),
        (left + width * 0.08, top + height * 0.28),
    ]

    left_sleeve = [
        (left + width * 0.19, top + height * 0.055),
        (left - width * 0.02, top + height * 0.17),
        (left + width * 0.04, top + height * 0.43),
        (left + width * 0.25, top + height * 0.34),
    ]
    right_sleeve = [(center_x + (center_x - x), y) for x, y in left_sleeve]

    draw.polygon([(int(x), int(y)) for x, y in points], fill=238)
    draw.polygon([(int(x), int(y)) for x, y in left_sleeve], fill=238)
    draw.polygon([(int(x), int(y)) for x, y in right_sleeve], fill=238)
    draw.ellipse(
        (
            center_x - width * 0.125,
            top - height * 0.030,
            center_x + width * 0.125,
            top + height * 0.130,
        ),
        fill=0,
    )
    mask = mask.filter(ImageFilter.GaussianBlur(radius=1.2))

    base = Image.new("RGBA", CANVAS_SIZE, (122, 64, 188, 0))
    base.putalpha(mask)

    texture = Image.new("L", CANVAS_SIZE, 0)
    texture_draw = ImageDraw.Draw(texture)
    texture_draw.ellipse(
        (
            left + width * 0.22,
            top + height * 0.05,
            right - width * 0.22,
            bottom - height * 0.15,
        ),
        fill=54,
    )
    texture = texture.filter(ImageFilter.GaussianBlur(radius=46))
    light = Image.new("RGBA", CANVAS_SIZE, (255, 236, 255, 0))
    light.putalpha(ImageChops.multiply(texture, mask).point(lambda value: int(value * 0.50)))

    edge = ImageChops.subtract(mask, mask.filter(ImageFilter.MinFilter(13)))
    outline = Image.new("RGBA", CANVAS_SIZE, (245, 208, 254, 0))
    outline.putalpha(edge.point(lambda value: int(value * 0.50)))

    layer = Image.alpha_composite(base, light)
    layer = Image.alpha_composite(layer, outline)
    draw = ImageDraw.Draw(layer)
    seam_color = (255, 246, 255, 54)
    draw.line(
        (
            center_x,
            top + int(height * 0.22),
            center_x,
            bottom - int(height * 0.12),
        ),
        fill=seam_color,
        width=max(2, width // 80),
    )
    return layer


def _apply_fit_heatmap_overlay(
    image: Image.Image,
    body_alpha: Image.Image,
    zones: List[FitZone],
) -> Image.Image:
    if not zones:
        return image

    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    width, height = image.size
    center_x = width // 2

    region_boxes = {
        "shoulder": (center_x - 200, 285, center_x + 200, 390),
        "chest": (center_x - 170, 345, center_x + 170, 535),
        "waist": (center_x - 135, 520, center_x + 135, 670),
        "hip": (center_x - 180, 650, center_x + 180, 815),
        "biceps": (center_x - 280, 360, center_x + 280, 570),
        "sleeve": (center_x - 290, 380, center_x + 290, 760),
        "thigh": (center_x - 130, 770, center_x + 130, 980),
        "inseam": (center_x - 100, 820, center_x + 100, 1120),
    }

    for zone in zones:
        if zone.color == "gray":
            alpha_value = 54
        else:
            alpha_value = 88

        box = region_boxes.get(zone.zone)
        if not box:
            continue

        mask = Image.new("L", image.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle(box, radius=42, fill=alpha_value)
        mask = ImageChops.multiply(mask.filter(ImageFilter.GaussianBlur(radius=18)), body_alpha)

        color = _heat_rgba(zone.color)
        layer = Image.new("RGBA", image.size, (*color, 0))
        layer.putalpha(mask)
        overlay = Image.alpha_composite(overlay, layer)

    return Image.alpha_composite(image, overlay)


def _heat_rgba(color: str) -> tuple[int, int, int]:
    if color == "red":
        return (239, 68, 68)
    if color == "yellow":
        return (245, 158, 11)
    if color == "green":
        return (34, 197, 94)
    if color == "blue":
        return (56, 189, 248)
    return (156, 163, 175)


def _draw_fit_labels(draw: ImageDraw.ImageDraw, zones: List[FitZone]) -> None:
    y_map = {
        "chest": 370,
        "waist": 600,
        "hip": 760,
        "biceps": 480,
        "sleeve": 540,
        "thigh": 850,
        "inseam": 920,
        "shoulder": 310,
    }

    label_map = {
        "chest": "Busto",
        "waist": "Cintura",
        "hip": "Quadril",
        "biceps": "Braço",
        "sleeve": "Manga",
        "thigh": "Coxa",
        "inseam": "Entrepernas",
        "shoulder": "Ombros",
    }

    for zone in zones:
        y = y_map.get(zone.zone, 920)
        color = _heat_color(zone.color)

        draw.rounded_rectangle((40, y, 290, y + 58), radius=16, fill=color)
        draw.text(
            (58, y + 16),
            f"{label_map.get(zone.zone, zone.zone)}: {_friendly_fit_status(zone)}",
            fill="#111827",
        )


def _bounded_scale(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, float(value or 1.0)))


def _heat_color(color: str) -> str:
    if color == "red":
        return "#fca5a5"
    if color == "yellow":
        return "#fde68a"
    if color == "green":
        return "#86efac"
    if color == "blue":
        return "#7dd3fc"
    if color == "gray":
        return "#d1d5db"
    return "#c4b5fd"


def _friendly_fit_status(zone: FitZone) -> str:
    status = (zone.status or "").lower()
    if status in {"apertado", "too_small"} or zone.color == "red":
        return "pouca folga"
    if status in {"justo", "tight", "balanced"} or zone.color == "yellow":
        return "caimento proximo"
    if status in {"folgado", "loose"} or zone.color in {"green", "blue"}:
        return "folga confortavel"
    return "medida ausente"
