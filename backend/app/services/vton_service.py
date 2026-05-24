import asyncio
import logging
import os
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
    VtonRenderMethod,
    VtonRunMode,
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
from app.services.huggingface_vton_provider import (
    HuggingFaceNotConfigured,
    HuggingFaceProviderError,
    extract_huggingface_result_url,
    is_huggingface_configured,
    run_huggingface_vton,
)
from app.services.human_template_bank import select_human_template_path
from app.services.humanized_person_renderer import render_humanized_tryon_person
from app.services.image_processor import UPLOAD_DIR, normalize_garment_visual
from app.services.mannequin_renderer import (
    CANVAS_SIZE,
    render_mannequin_scene,
    render_tryon_person_scene,
)
from app.services.url_utils import absolute_url
from app.services.vton_render_pipeline import (
    GarmentRenderContext,
    MannequinGarmentRenderer,
)


VTON_DIR = UPLOAD_DIR / "vton"
VTON_DIR.mkdir(parents=True, exist_ok=True)
PERSON_RENDER_DIR = UPLOAD_DIR / "person"
PERSON_RENDER_DIR.mkdir(parents=True, exist_ok=True)
VTON_TASK_POLL_SECONDS = 2
_VTON_TASKS: Dict[str, VtonTaskStatusResponse] = {}
_GARMENT_RENDERER = MannequinGarmentRenderer()
LOGGER = logging.getLogger(__name__)
LOCAL_FIT_DIAGRAM: VtonRenderMethod = "LOCAL_FIT_DIAGRAM"
NEURAL_REALISTIC: VtonRenderMethod = "NEURAL_REALISTIC"


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

    if _should_draw_fit_labels():
        draw = ImageDraw.Draw(image)
        _draw_fit_labels(draw, data.payload.fit_zones)

    image.save(output_path, "PNG", optimize=True)

    return VtonMockResult(
        result_url=absolute_url(f"/uploads/vton/{filename}"),
        result_path=str(output_path),
        render_method=LOCAL_FIT_DIAGRAM,
        message="Diagrama de caimento gerado com base nas medidas disponiveis.",
    )


async def run_vton(data: VtonRunInput) -> VtonRunResult:
    provider = get_vton_provider_name()

    if data.mode == "mock":
        return _local_fit_diagram_result(data, used_fallback=False)

    if data.mode == "external":
        return await _run_external_only(data, provider)

    if data.mode == "auto":
        fallback_errors = []

        if not _payload_has_provider_ready_garment(data.payload):
            LOGGER.info("Skipping external VTON providers because no garment image is available.")
            fallback_errors.append(
                {
                    "provider": "preflight",
                    "error_type": "MissingGarmentImage",
                    "message": "No garment image available for real VTON; using local fit diagram.",
                }
            )
            return _local_fit_diagram_result(
                data,
                used_fallback=True,
                message=(
                    "Nao encontramos uma imagem utilizavel da peca. "
                    "Mostramos um diagrama de caimento para voce continuar."
                ),
                fallback_errors=fallback_errors,
            )

        if is_external_vton_configured():
            try:
                return await _run_external_only(data, provider)
            except Exception as error:
                LOGGER.warning(
                    "External VTON provider failed; trying Hugging Face fallback: %s",
                    error,
                )
                fallback_errors.append(_fallback_error(provider, error))

        if is_huggingface_configured():
            try:
                return await _run_huggingface_only(data)
            except (HuggingFaceNotConfigured, HuggingFaceProviderError, Exception) as error:
                LOGGER.warning(
                    "Hugging Face VTON provider failed; using local fit diagram fallback: %s",
                    error,
                )
                fallback_errors.append(_fallback_error("huggingface", error))

        return _local_fit_diagram_result(
            data,
            used_fallback=True,
            message=(
                "Previa realista indisponivel no momento. "
                "Mostramos um diagrama de caimento para voce continuar."
            ),
            fallback_errors=fallback_errors,
        )

    return _local_fit_diagram_result(
        data,
        used_fallback=True,
        mode_requested="mock",
        message="Modo invalido. Mostramos o diagrama de caimento.",
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
    public_payload = _ensure_public_vton_assets(
        data.payload,
        require_neural_safe_person=True,
    )
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
        render_method=NEURAL_REALISTIC,
        status=status,
        used_fallback=False,
        success=True,
        message=f"Resultado VTON externo recebido com sucesso via {provider}.",
        raw_response=raw_response,
    )


async def _run_huggingface_only(data: VtonRunInput) -> VtonRunResult:
    public_payload = _ensure_public_vton_assets(
        data.payload,
        refresh_person_image=False,
        create_missing_person=True,
        require_neural_safe_person=True,
    )
    raw_response = await run_huggingface_vton(public_payload)
    result_url = extract_huggingface_result_url(raw_response)

    if not result_url:
        raise ExternalVtonProviderError(
            "Hugging Face respondeu, mas nenhuma URL de resultado foi encontrada."
        )

    return VtonRunResult(
        result_url=absolute_url(result_url),
        result_path=None,
        provider="huggingface",
        mode_requested=data.mode,
        render_method=NEURAL_REALISTIC,
        status=raw_response.get("status"),
        used_fallback=False,
        success=True,
        message="Prévia realista gerada via Hugging Face Spaces.",
        raw_response=raw_response,
    )



def _local_fit_diagram_result(
    data: VtonRunInput,
    used_fallback: bool,
    message: Optional[str] = None,
    fallback_errors: Optional[List[Dict[str, str]]] = None,
    mode_requested: Optional[VtonRunMode] = None,
) -> VtonRunResult:
    mock = create_mock_vton_result(VtonMockInput(payload=data.payload))
    return VtonRunResult(
        result_url=mock.result_url,
        result_path=mock.result_path,
        provider="local_mock",
        mode_requested=mode_requested or data.mode,
        render_method=LOCAL_FIT_DIAGRAM,
        status="succeeded",
        used_fallback=used_fallback,
        success=True,
        message=message or mock.message,
        raw_response={"fallback_errors": fallback_errors} if fallback_errors else None,
    )


def _payload_has_provider_ready_garment(payload: VtonPayload) -> bool:
    """Real VTON providers need an actual garment image, not just fit data."""

    return bool(payload.garment_processed_url or payload.garment_original_url)


def _fallback_error(provider: str, error: Exception) -> Dict[str, str]:
    message = str(error)
    return {
        "provider": provider,
        "error_type": type(error).__name__,
        "message": message[:500],
    }


def _ensure_public_vton_assets(
    payload: VtonPayload,
    refresh_person_image: bool = False,
    create_missing_person: bool = True,
    require_neural_safe_person: bool = False,
) -> VtonPayload:
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

    should_replace_mock_person = create_missing_person and _is_procedural_person_url(person_image_url)

    if require_neural_safe_person:
        person_image_url = _resolve_neural_person_image_url(payload, person_image_url)
    elif refresh_person_image or (
        create_missing_person and (not person_image_url or should_replace_mock_person)
    ):
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


def _resolve_neural_person_image_url(
    payload: VtonPayload,
    person_image_url: Optional[str],
) -> str:
    if _is_neural_safe_person_url(person_image_url):
        return person_image_url

    template_url = _create_public_human_template_image(payload)
    if template_url:
        return template_url

    raise ExternalVtonProviderError(
        "Nenhuma foto humana real ou template humano local esta disponivel para VTON neural."
    )


def _is_neural_safe_person_url(person_image_url: Optional[str]) -> bool:
    if not person_image_url:
        return False

    normalized = unquote(urlparse(person_image_url).path).replace("\\", "/")
    internal_generated_markers = (
        "/uploads/mannequin/",
        "/uploads/person/provider_person_",
        "/uploads/person/humanized_person_",
    )
    return not any(marker in normalized for marker in internal_generated_markers)


def _create_public_human_template_image(payload: VtonPayload) -> Optional[str]:
    template_path = _select_human_template_path(payload)
    if template_path is None:
        return None

    filename = f"template_person_{uuid4().hex}.jpg"
    output_path = PERSON_RENDER_DIR / filename

    try:
        with Image.open(template_path) as image:
            image = _fit_template_to_canvas(image.convert("RGBA"), CANVAS_SIZE)
            rgb = Image.new("RGB", image.size, (248, 248, 246))
            rgb.paste(image.convert("RGB"), mask=image.getchannel("A"))
            rgb.save(output_path, "JPEG", quality=90, optimize=True, progressive=False)
    except Exception as error:
        LOGGER.warning("Failed to prepare human template for neural VTON: %s", error)
        return None

    return absolute_url(f"/uploads/person/{filename}")


def _select_human_template_path(payload: VtonPayload) -> Optional[Path]:
    return select_human_template_path(payload)


def _fit_template_to_canvas(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    canvas = Image.new("RGBA", size, (248, 248, 246, 255))
    image.thumbnail((int(size[0] * 0.86), int(size[1] * 0.94)), Image.Resampling.LANCZOS)
    left = (size[0] - image.width) // 2
    top = max(0, int(size[1] * 0.03))
    canvas.alpha_composite(image, (left, top))
    return canvas


def _create_public_person_image(payload: VtonPayload) -> str:
    filename = f"provider_person_{uuid4().hex}.jpg"
    output_path = PERSON_RENDER_DIR / filename

    if os.getenv("VTON_USE_HUMANIZED_PERSON", "true").strip().lower() in {"1", "true", "yes", "sim"}:
        image = render_humanized_tryon_person(payload.mannequin, size=CANVAS_SIZE)
    else:
        image = render_tryon_person_scene(payload.mannequin, size=CANVAS_SIZE)

    rgb = Image.new("RGB", image.size, (248, 248, 246))
    rgba = image.convert("RGBA")
    rgb.paste(rgba.convert("RGB"), mask=rgba.getchannel("A"))
    rgb.save(output_path, "JPEG", quality=90, optimize=True, progressive=False)

    return absolute_url(f"/uploads/person/{filename}")


def _is_procedural_person_url(person_image_url: Optional[str]) -> bool:
    if not person_image_url:
        return False
    if os.getenv("VTON_REPLACE_MOCK_PERSON_FOR_EXTERNAL", "true").strip().lower() not in {
        "1",
        "true",
        "yes",
        "sim",
    }:
        return False
    normalized = person_image_url.replace("\\", "/")
    return "/uploads/mannequin/" in normalized or normalized.startswith("uploads/mannequin/")


def _composite_garment_on_body(
    image: Image.Image,
    body_alpha: Image.Image,
    body_shadow: Image.Image,
    body_light: Image.Image,
    payload: VtonPayload,
) -> Image.Image:
    garment = _load_processed_garment(payload.garment_processed_url)
    foreground_occlusion = _build_foreground_occlusion_mask(payload.mannequin, image.size)

    if garment is not None and _looks_like_screen_capture(garment):
        LOGGER.warning("Uploaded garment looks like a screenshot/table instead of a garment; using parametric fallback.")
        garment = None

    garment_kind = _infer_garment_kind(garment, payload)

    if garment is None:
        fallback = _build_parametric_garment_placeholder(payload, body_alpha=body_alpha, garment_kind=garment_kind)
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
                curve_hem=garment_kind != "bottom",
            ),
        )
        return Image.alpha_composite(image, fallback)

    garment = normalize_garment_visual(_crop_to_visual_content(garment))
    garment_kind = _infer_garment_kind(garment, payload)
    if _alpha_is_mostly_opaque(garment):
        garment = _apply_soft_garment_silhouette(garment, garment_kind)

    garment, left, top = _fit_garment_to_body(garment, payload, body_alpha=body_alpha, garment_kind=garment_kind)

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
            curve_hem=garment_kind != "bottom",
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

    direct_path = Path(path_or_url)
    if direct_path.exists():
        return direct_path

    parsed = urlparse(path_or_url)
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


def _crop_to_visual_content(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    alpha_bbox = rgba.getchannel("A").getbbox()
    if alpha_bbox and alpha_bbox != (0, 0, rgba.width, rgba.height):
        return _crop_to_alpha(rgba)

    rgb = rgba.convert("RGB")
    sample_points = [
        (0, 0),
        (rgba.width - 1, 0),
        (0, rgba.height - 1),
        (rgba.width - 1, rgba.height - 1),
    ]
    colors = [rgb.getpixel(point) for point in sample_points]
    background = max(colors, key=lambda color: color[0] + color[1] + color[2])
    background_layer = Image.new("RGB", rgba.size, background)
    diff = ImageChops.difference(rgb, background_layer).convert("L")

    content_mask = diff.point(lambda value: 255 if value > 24 else 0)
    content_mask = content_mask.filter(ImageFilter.MaxFilter(7))
    content_mask = content_mask.filter(ImageFilter.GaussianBlur(radius=0.8))
    bbox = content_mask.getbbox()

    if not bbox:
        return rgba

    margin_x = int(rgba.width * 0.035)
    margin_y = int(rgba.height * 0.035)
    left = max(0, bbox[0] - margin_x)
    top = max(0, bbox[1] - margin_y)
    right = min(rgba.width, bbox[2] + margin_x)
    bottom = min(rgba.height, bbox[3] + margin_y)

    cropped = rgba.crop((left, top, right, bottom))
    cropped_mask = content_mask.crop((left, top, right, bottom))
    soft_alpha = cropped_mask.point(lambda value: 255 if value > 44 else 0)
    soft_alpha = soft_alpha.filter(ImageFilter.GaussianBlur(radius=max(0.6, cropped.width // 260)))

    original_alpha = cropped.getchannel("A")
    if original_alpha.getextrema()[0] >= 245:
        return Image.merge("RGBA", (*cropped.convert("RGB").split(), soft_alpha))

    return Image.merge("RGBA", (*cropped.convert("RGB").split(), ImageChops.multiply(original_alpha, soft_alpha)))


def _alpha_is_mostly_opaque(image: Image.Image) -> bool:
    alpha = image.getchannel("A")
    extrema = alpha.getextrema()

    if extrema[0] < 245:
        return False

    opaque_bbox = alpha.point(lambda value: 255 if value > 245 else 0).getbbox()
    return opaque_bbox == (0, 0, image.width, image.height)


def _looks_like_screen_capture(image: Image.Image) -> bool:
    """Detect accidental phone screenshots before treating them as garments."""

    rgba = image.convert("RGBA")
    return _looks_like_app_screen_capture(rgba) or _looks_like_size_table_capture(rgba)


def _looks_like_app_screen_capture(rgba: Image.Image) -> bool:
    aspect = rgba.height / max(1, rgba.width)
    if aspect < 1.35:
        return False

    sample = rgba.convert("RGB").resize((36, 64), Image.Resampling.BILINEAR)
    pixels = list(sample.getdata())
    total = max(1, len(pixels))
    dark_purple = sum(
        1
        for red, green, blue in pixels
        if red < 70 and green < 55 and blue > 45 and blue >= red
    )
    bright_text = sum(1 for red, green, blue in pixels if red > 215 and green > 210 and blue > 215)
    saturated_ui = sum(
        1
        for red, green, blue in pixels
        if blue > 110 and red > 85 and green < 95 and abs(red - blue) < 110
    )

    return (
        dark_purple / total > 0.22
        and bright_text / total > 0.012
        and saturated_ui / total > 0.030
    )


def _looks_like_size_table_capture(rgba: Image.Image) -> bool:
    """Detect screenshots of size tables so they are not pasted as garments."""

    sample = rgba.convert("RGB").resize((72, 72), Image.Resampling.BILINEAR)
    pixels = list(sample.getdata())
    total = max(1, len(pixels))
    light_ratio = sum(1 for red, green, blue in pixels if red > 218 and green > 218 and blue > 218) / total
    dark_ratio = sum(1 for red, green, blue in pixels if red < 80 and green < 80 and blue < 80) / total
    neutral_ratio = sum(1 for red, green, blue in pixels if abs(red - green) < 18 and abs(green - blue) < 18) / total

    if not (light_ratio > 0.62 and 0.010 < dark_ratio < 0.18 and neutral_ratio > 0.78):
        return False

    gray = sample.convert("L")
    horizontal_edges = 0
    vertical_edges = 0
    for y in range(1, gray.height):
        row_diff = 0
        for x in range(gray.width):
            row_diff += abs(gray.getpixel((x, y)) - gray.getpixel((x, y - 1)))
        if row_diff / gray.width > 20:
            horizontal_edges += 1
    for x in range(1, gray.width):
        col_diff = 0
        for y in range(gray.height):
            col_diff += abs(gray.getpixel((x, y)) - gray.getpixel((x - 1, y)))
        if col_diff / gray.height > 18:
            vertical_edges += 1

    return horizontal_edges >= 4 and vertical_edges >= 2


def _apply_soft_garment_silhouette(image: Image.Image, garment_kind: str = "top") -> Image.Image:
    rgba = image.convert("RGBA")
    rgb = rgba.convert("RGB")
    width, height = rgba.size

    sample_points = [
        (0, 0),
        (width - 1, 0),
        (0, height - 1),
        (width - 1, height - 1),
        (width // 2, 0),
        (width // 2, height - 1),
    ]
    colors = [rgb.getpixel(point) for point in sample_points]
    background = max(colors, key=lambda color: color[0] + color[1] + color[2])
    background_layer = Image.new("RGB", rgba.size, background)
    diff = ImageChops.difference(rgb, background_layer).convert("L")

    # Preserve real garment texture from opaque product photos by turning the
    # studio/light background into transparency instead of replacing the piece
    # with a generic silhouette. This is intentionally lightweight for Render.
    color_mask = diff.point(lambda value: 255 if value > 18 else 0)
    color_mask = color_mask.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(radius=1.1))
    bbox = color_mask.getbbox()
    if bbox:
        coverage = ((bbox[2] - bbox[0]) * (bbox[3] - bbox[1])) / max(1, width * height)
        if coverage > 0.08:
            alpha = ImageChops.multiply(rgba.getchannel("A"), color_mask)
            alpha = alpha.point(lambda value: 255 if value > 220 else value)
            return Image.merge("RGBA", (*rgb.split(), alpha))

    mask = Image.new("L", rgba.size, 0)
    draw = ImageDraw.Draw(mask)
    if garment_kind == "bottom":
        draw.rounded_rectangle(
            (width * 0.24, height * 0.03, width * 0.76, height * 0.20),
            radius=max(4, int(width * 0.035)),
            fill=255,
        )
        skirt_points = [
            (width * 0.25, height * 0.16),
            (width * 0.75, height * 0.16),
            (width * 0.95, height * 0.60),
            (width * 0.82, height * 0.95),
            (width * 0.56, height * 0.80),
            (width * 0.50, height * 0.70),
            (width * 0.44, height * 0.82),
            (width * 0.18, height * 0.98),
            (width * 0.05, height * 0.62),
        ]
        draw.polygon([(int(x), int(y)) for x, y in skirt_points], fill=255)
    else:
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
        if garment_kind != "long":
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
    alpha = ImageChops.multiply(rgba.getchannel("A"), mask)
    return Image.merge("RGBA", (*rgb.split(), alpha))

def _fit_garment_to_body(
    garment: Image.Image,
    payload: VtonPayload,
    body_alpha: Optional[Image.Image] = None,
    garment_kind: Optional[str] = None,
) -> tuple[Image.Image, int, int]:
    garment_kind = garment_kind or _infer_garment_kind(garment, payload)
    target_left, target_top, target_right, target_bottom = _garment_target_box(payload, garment, body_alpha, garment_kind=garment_kind)
    target_width = max(1, target_right - target_left)
    target_height = max(1, target_bottom - target_top)

    width_scale = target_width / max(1, garment.width)
    height_scale = target_height / max(1, garment.height)

    if garment_kind == "long":
        scale = min(width_scale, height_scale)
        if garment.height > garment.width:
            scale = min(max(scale, height_scale * 0.90), width_scale * 1.08)
        top_bias = 0.03
    elif garment_kind == "bottom":
        # Bottom pieces should anchor at the waist/hip, not the chest. Width is
        # allowed to lead the fit so asymmetric hems keep their character.
        scale = min(width_scale * 1.02, height_scale * 1.22)
        top_bias = 0.00
    else:
        scale = min(width_scale, height_scale)
        top_bias = 0.10

    scale = max(0.1, scale)
    new_size = (
        max(1, int(garment.width * scale)),
        max(1, int(garment.height * scale)),
    )

    resized = garment.resize(new_size, Image.Resampling.LANCZOS)
    left = target_left + (target_width - resized.width) // 2
    top = target_top + int((target_height - resized.height) * top_bias)
    return resized, left, top


def _garment_target_box(
    payload: VtonPayload,
    garment: Optional[Image.Image] = None,
    body_alpha: Optional[Image.Image] = None,
    garment_kind: Optional[str] = None,
) -> tuple[int, int, int, int]:
    mannequin = payload.mannequin
    center_x = CANVAS_SIZE[0] // 2
    garment_kind = garment_kind or _infer_garment_kind(garment, payload)

    body_bbox = body_alpha.getbbox() if body_alpha else None
    if body_bbox:
        body_left, body_top, body_right, body_bottom = body_bbox
        body_width = body_right - body_left
        body_height = body_bottom - body_top
        shoulder_span = _body_span_at_ratio(body_alpha, body_bbox, 0.315)
        chest_span = _body_span_at_ratio(body_alpha, body_bbox, 0.405)
        waist_span = _body_span_at_ratio(body_alpha, body_bbox, 0.510)
        hip_span = _body_span_at_ratio(body_alpha, body_bbox, 0.620)
        thigh_span = _body_span_at_ratio(body_alpha, body_bbox, 0.735)
        center_x = _weighted_center_from_spans([chest_span, waist_span, hip_span]) or (body_left + body_right) // 2

        shoulder_width = shoulder_span[2]
        chest_width = chest_span[2]
        waist_width = waist_span[2]
        hip_width = hip_span[2]
        thigh_width = thigh_span[2]

        if garment_kind == "bottom":
            target_top = int(body_top + body_height * 0.432)
            target_bottom = int(body_top + body_height * 0.812)
            target_width = int(max(waist_width * 1.65, hip_width * 1.32, thigh_width * 1.18, 318))
            max_width_ratio = 0.76
            min_width = 302
        elif garment_kind == "long":
            target_top = int(body_top + body_height * 0.258)
            target_bottom = int(body_top + body_height * 0.825)
            target_width = int(max(shoulder_width * 0.96, chest_width * 1.12, waist_width * 1.22, hip_width * 1.10, 318))
            max_width_ratio = 0.66
            min_width = 292
        else:
            target_top = int(body_top + body_height * 0.275)
            target_bottom = int(body_top + body_height * 0.565)
            target_width = int(max(shoulder_width * 0.94, chest_width * 1.12, waist_width * 1.22, 300))
            max_width_ratio = 0.60
            min_width = 280

        shoulder_factor = _bounded_scale(getattr(mannequin, "shoulder_scale", 1.0), 0.74, 1.32)
        chest_factor = _bounded_scale(getattr(mannequin, "chest_scale", 1.0), 0.74, 1.36)
        hip_factor = _bounded_scale(getattr(mannequin, "hip_scale", 1.0), 0.74, 1.38)
        region_factor = hip_factor if garment_kind == "bottom" else (shoulder_factor + chest_factor + hip_factor) / 3
        target_width = int(target_width * max(0.94, min(1.14, region_factor)))

        width_multiplier, bottom_offset = _fit_target_adjustments(payload.fit_zones)
        target_width = int(target_width * width_multiplier)
        target_bottom = min(body_bottom, target_bottom + bottom_offset)
        target_width = max(min_width, min(int(body_width * max_width_ratio), target_width))
        target_left = max(0, center_x - target_width // 2)
        target_right = min(CANVAS_SIZE[0], center_x + target_width // 2)

        return (target_left, target_top, target_right, target_bottom)

    shoulder_half = int(172 * _bounded_scale(getattr(mannequin, "shoulder_scale", 1.0), 0.74, 1.32))
    chest_half = int(164 * _bounded_scale(getattr(mannequin, "chest_scale", 1.0), 0.74, 1.36))
    waist_half = int(122 * _bounded_scale(getattr(mannequin, "waist_scale", 1.0), 0.72, 1.42))
    hip_half = int(150 * _bounded_scale(getattr(mannequin, "hip_scale", 1.0), 0.74, 1.38))

    width_multiplier, bottom_offset = _fit_target_adjustments(payload.fit_zones)

    if garment_kind == "bottom":
        target_width = int(max(300, waist_half * 2.02, hip_half * 1.92))
        target_top = 520
        target_bottom = min(1030, 955 + bottom_offset)
    elif garment_kind == "long":
        target_width = int(max(330, shoulder_half * 1.70, chest_half * 1.95, hip_half * 1.82))
        target_top = 295
        target_bottom = min(1040, 965 + bottom_offset)
    else:
        target_width = int(max(320, shoulder_half * 1.76, chest_half * 2.00, waist_half * 2.08))
        target_top = 310
        target_bottom = min(820, 745 + bottom_offset)

    target_width = int(target_width * width_multiplier)
    target_width = min(500 if garment_kind == "bottom" else 540 if garment_kind == "long" else 500, target_width)

    return (
        center_x - target_width // 2,
        target_top,
        center_x + target_width // 2,
        target_bottom,
    )


def _garment_kind(garment: Optional[Image.Image]) -> str:
    if garment is None:
        return "top"

    aspect = garment.height / max(1, garment.width)
    if aspect >= 1.18:
        return "long"
    return "top"


def _infer_garment_kind(garment: Optional[Image.Image], payload: VtonPayload) -> str:
    zone_names = _fit_zone_names(payload.fit_zones)
    bottom_score = len(zone_names & {"waist", "hip", "thigh", "inseam", "rise"})
    upper_score = len(zone_names & {"chest", "bust", "busto", "torax", "tórax", "shoulder", "sleeve", "biceps", "top_length"})

    if garment is not None:
        aspect = garment.height / max(1, garment.width)
        if _alpha_shape_suggests_skirt(garment):
            return "bottom"
        if bottom_score >= 1 and upper_score == 0 and aspect <= 1.55:
            return "bottom"
        if aspect >= 1.42:
            return "long"
        if bottom_score >= 2 and aspect <= 1.32:
            return "bottom"

    if bottom_score >= 1 and upper_score == 0:
        return "bottom"
    if {"chest", "waist", "hip"}.issubset(zone_names):
        return "long"
    return _garment_kind(garment)


def _fit_zone_names(zones: List[FitZone]) -> set[str]:
    return {str(zone.zone or "").strip().lower().replace("/", "_") for zone in zones}


def _alpha_shape_suggests_skirt(image: Image.Image) -> bool:
    alpha = image.convert("RGBA").getchannel("A")
    if not alpha.getbbox():
        return False
    small = alpha.resize((80, 100), Image.Resampling.BILINEAR)
    top_width = _alpha_row_width(small, int(small.height * 0.15))
    mid_width = _alpha_row_width(small, int(small.height * 0.54))
    low_width = _alpha_row_width(small, int(small.height * 0.78))
    if top_width <= 0:
        return False
    return (
        mid_width > top_width * 1.22
        and low_width > top_width * 1.05
        and top_width < small.width * 0.78
    )


def _alpha_row_width(alpha: Image.Image, y: int) -> int:
    values = [x for x in range(alpha.width) if alpha.getpixel((x, max(0, min(alpha.height - 1, y)))) > 32]
    if not values:
        return 0
    return values[-1] - values[0] + 1


def _body_span_at_ratio(alpha: Image.Image, bbox: tuple[int, int, int, int], y_ratio: float) -> tuple[int, int, int]:
    left, top, right, bottom = bbox
    height = max(1, bottom - top)
    y_center = int(top + height * y_ratio)
    band = max(2, int(height * 0.012))
    best: tuple[int, int, int] | None = None
    for y in range(max(top, y_center - band), min(bottom, y_center + band + 1)):
        values = [x for x in range(left, right) if alpha.getpixel((x, y)) > 36]
        if not values:
            continue
        span = (values[0], values[-1], values[-1] - values[0] + 1)
        if best is None or span[2] > best[2]:
            best = span
    if best is not None:
        return best
    return (left, right, max(1, right - left))


def _weighted_center_from_spans(spans: list[tuple[int, int, int]]) -> int | None:
    usable = [span for span in spans if span[2] > 0]
    if not usable:
        return None
    total = sum(span[2] for span in usable)
    return int(sum(((span[0] + span[1]) / 2) * span[2] for span in usable) / max(1, total))
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


def _should_draw_fit_labels() -> bool:
    return os.getenv("VTON_DRAW_FIT_LABELS", "").strip().lower() in {"1", "true", "yes", "sim"}


def _build_parametric_garment_placeholder(
    payload: VtonPayload,
    body_alpha: Optional[Image.Image] = None,
    garment_kind: Optional[str] = None,
) -> Image.Image:
    garment_kind = garment_kind or _infer_garment_kind(None, payload)
    mask = Image.new("L", CANVAS_SIZE, 0)
    draw = ImageDraw.Draw(mask)
    center_x = CANVAS_SIZE[0] // 2
    left, top, right, bottom = _garment_target_box(payload, body_alpha=body_alpha, garment_kind=garment_kind)
    width = right - left
    height = bottom - top

    if garment_kind == "bottom":
        draw.rounded_rectangle(
            (left + width * 0.24, top + height * 0.02, right - width * 0.24, top + height * 0.18),
            radius=max(8, int(width * 0.04)),
            fill=238,
        )
        points = [
            (left + width * 0.24, top + height * 0.15),
            (right - width * 0.24, top + height * 0.15),
            (right - width * 0.03, top + height * 0.58),
            (right - width * 0.17, bottom - height * 0.04),
            (center_x + width * 0.08, bottom - height * 0.18),
            (center_x, bottom - height * 0.30),
            (center_x - width * 0.08, bottom - height * 0.16),
            (left + width * 0.17, bottom),
            (left + width * 0.03, top + height * 0.60),
        ]
        draw.polygon([(int(x), int(y)) for x, y in points], fill=224)
    else:
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
        draw.polygon([(int(x), int(y)) for x, y in points], fill=238)
        if garment_kind != "long":
            left_sleeve = [
                (left + width * 0.19, top + height * 0.055),
                (left - width * 0.02, top + height * 0.17),
                (left + width * 0.04, top + height * 0.43),
                (left + width * 0.25, top + height * 0.34),
            ]
            right_sleeve = [(center_x + (center_x - x), y) for x, y in left_sleeve]
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

    base_color = (36, 29, 40, 0) if garment_kind == "bottom" else (122, 64, 188, 0)
    base = Image.new("RGBA", CANVAS_SIZE, base_color)
    base.putalpha(mask)

    texture = Image.new("L", CANVAS_SIZE, 0)
    texture_draw = ImageDraw.Draw(texture)
    texture_draw.ellipse(
        (
            left + width * 0.18,
            top + height * 0.05,
            right - width * 0.18,
            bottom - height * 0.12,
        ),
        fill=54,
    )
    texture = texture.filter(ImageFilter.GaussianBlur(radius=42 if garment_kind == "bottom" else 46))
    light = Image.new("RGBA", CANVAS_SIZE, (255, 236, 255, 0))
    light.putalpha(ImageChops.multiply(texture, mask).point(lambda value: int(value * 0.45)))

    edge = ImageChops.subtract(mask, mask.filter(ImageFilter.MinFilter(13)))
    outline = Image.new("RGBA", CANVAS_SIZE, (245, 208, 254, 0))
    outline.putalpha(edge.point(lambda value: int(value * 0.45)))

    layer = Image.alpha_composite(base, light)
    layer = Image.alpha_composite(layer, outline)
    draw = ImageDraw.Draw(layer)
    seam_color = (255, 246, 255, 52)
    if garment_kind == "bottom":
        for offset in (-0.22, 0, 0.22):
            draw.line(
                (
                    center_x + int(width * offset),
                    top + int(height * 0.20),
                    center_x + int(width * offset * 0.35),
                    bottom - int(height * 0.10),
                ),
                fill=seam_color,
                width=2,
            )
    else:
        draw.line(
            (
                center_x,
                top + int(height * 0.22),
                center_x,
                bottom - int(height * 0.12),
            ),
            fill=seam_color,
            width=2,
        )
        draw.arc(
            (
                center_x - int(width * 0.26),
                top + int(height * 0.18),
                center_x + int(width * 0.26),
                top + int(height * 0.58),
            ),
            start=195,
            end=345,
            fill=seam_color,
            width=2,
        )

    if _should_draw_fit_labels():
        _draw_fit_labels(draw, payload.fit_zones)

    return layer

def _apply_fit_heatmap_overlay(
    image: Image.Image,
    body_alpha: Image.Image,
    zones: List[FitZone],
) -> Image.Image:
    if not zones:
        return image

    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    width, _height = image.size
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
        "length": (center_x - 165, 610, center_x + 165, 980),
    }

    for zone in zones:
        alpha_value = 26 if zone.color == "gray" else 44
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
        return "caimento próximo"
    if status in {"folgado", "loose"} or zone.color in {"green", "blue"}:
        return "folga confortável"
    return "medida ausente"
