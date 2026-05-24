# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

from app.models.body import MannequinParams
from app.models.product import FitZone


@dataclass(frozen=True)
class GarmentRenderContext:
    """Inputs used by the local fit diagram renderer.

    This renderer is intentionally honest: it does not try to mimic neural VTON.
    It keeps the garment mostly planar, applies subtle lighting, and emphasizes
    fit zones so the user understands where the piece may feel close or loose.
    """

    mannequin: MannequinParams
    body_alpha: Image.Image
    shadow_map_alpha: Image.Image
    light_map_rgba: Optional[Image.Image] = None
    occlusion_mask_alpha: Optional[Image.Image] = None
    fit_zones: Sequence[FitZone] = ()
    shadow_intensity: float = 0.58
    highlight_intensity: float = 0.30
    curve_hem: bool = True


class MannequinGarmentRenderer:
    """Renderer for the local fit diagram garment layer."""

    def render(
        self,
        garment_rgba: Image.Image,
        context: GarmentRenderContext,
    ) -> Image.Image:
        """Render a garment through planar overlay, lighting and fit-zone passes."""

        output = garment_rgba.convert("RGBA")
        traits = _fit_render_traits(context.fit_zones)

        # The local fallback is a fit diagram, not a synthetic VTON attempt.
        # Keep the garment planar so the output remains visually honest.

        if context.curve_hem:
            output = curve_garment_hem(output, context.mannequin)

        output = apply_mannequin_shading(
            garment_rgba=output,
            shadow_map_alpha=context.shadow_map_alpha,
            light_map_rgba=context.light_map_rgba,
            body_alpha=context.body_alpha,
            shadow_intensity=context.shadow_intensity * traits["shadow_multiplier"],
            highlight_intensity=context.highlight_intensity * traits["highlight_multiplier"],
        )

        output = apply_fit_pressure_to_garment(output, context.fit_zones)

        return apply_occlusion_mask(output, context.occlusion_mask_alpha)


def apply_mannequin_shading(
    garment_rgba: Image.Image,
    shadow_map_alpha: Image.Image,
    light_map_rgba: Optional[Image.Image] = None,
    body_alpha: Optional[Image.Image] = None,
    shadow_intensity: float = 0.58,
    highlight_intensity: float = 0.30,
) -> Image.Image:
    """Apply mannequin volume to a garment with Multiply + Screen passes.

    `shadow_map_alpha` darkens recessed areas through Multiply. `light_map_rgba`
    brightens raised body volumes through Screen, which keeps dark garments from
    becoming flat black patches.
    """

    garment = garment_rgba.convert("RGBA")
    garment_alpha = garment.getchannel("A")
    shadow_map = _map_to_l(shadow_map_alpha, garment.size)
    body_mask = _map_to_l(body_alpha, garment.size) if body_alpha else None

    shadow_signal = ImageChops.multiply(shadow_map, garment_alpha)
    if body_mask is not None:
        shadow_signal = ImageChops.multiply(shadow_signal, body_mask)

    shadow_intensity = _clamp_float(shadow_intensity, 0.0, 1.0)
    shadow_factor = shadow_signal.point(
        lambda value: max(0, 255 - int(value * shadow_intensity))
    )
    shaded_rgb = ImageChops.multiply(
        garment.convert("RGB"),
        Image.merge("RGB", (shadow_factor, shadow_factor, shadow_factor)),
    )

    if light_map_rgba is not None and highlight_intensity > 0:
        light_map = _map_to_l(light_map_rgba, garment.size)
        light_signal = ImageChops.multiply(light_map, garment_alpha)
        if body_mask is not None:
            light_signal = ImageChops.multiply(light_signal, body_mask)

        highlight_intensity = _clamp_float(highlight_intensity, 0.0, 1.0)
        highlight = light_signal.point(lambda value: int(value * highlight_intensity))
        shaded_rgb = ImageChops.screen(
            shaded_rgb,
            Image.merge("RGB", (highlight, highlight, highlight)),
        )

    return Image.merge("RGBA", (*shaded_rgb.split(), garment_alpha))


def apply_occlusion_mask(
    garment_rgba: Image.Image,
    occlusion_mask_alpha: Optional[Image.Image],
    strength: float = 1.0,
) -> Image.Image:
    """Subtract foreground body alpha from the garment alpha channel."""

    if occlusion_mask_alpha is None:
        return garment_rgba.convert("RGBA")

    garment = garment_rgba.convert("RGBA")
    occlusion = _map_to_l(occlusion_mask_alpha, garment.size)
    strength = _clamp_float(strength, 0.0, 1.0)
    occlusion = occlusion.point(lambda value: int(value * strength))
    alpha = ImageChops.subtract(garment.getchannel("A"), occlusion)
    return Image.merge("RGBA", (*garment.convert("RGB").split(), alpha))


def apply_fit_pressure_to_garment(
    garment_rgba: Image.Image,
    fit_zones: Sequence[FitZone],
) -> Image.Image:
    """Draw fit-pressure cues directly on the rendered garment.

    The body heatmap can be hidden by opaque clothing. This pass paints a
    subtle textile overlay on top of the garment itself so tight, close,
    relaxed and unknown measurements remain visible in the final mock image.
    """

    if not fit_zones:
        return garment_rgba.convert("RGBA")

    garment = garment_rgba.convert("RGBA")
    garment_alpha = garment.getchannel("A")
    overlay = Image.new("RGBA", garment.size, (0, 0, 0, 0))
    details = Image.new("RGBA", garment.size, (0, 0, 0, 0))
    details_draw = ImageDraw.Draw(details)

    for zone in fit_zones:
        for box in _garment_zone_boxes(zone.zone, garment.size):
            mask = Image.new("L", garment.size, 0)
            draw = ImageDraw.Draw(mask)
            radius = max(10, int((box[2] - box[0]) * 0.10))
            draw.rounded_rectangle(box, radius=radius, fill=_zone_alpha(zone))
            mask = mask.filter(ImageFilter.GaussianBlur(radius=max(3, garment.width // 90)))
            mask = ImageChops.multiply(mask, garment_alpha)

            color = _fit_zone_rgb(zone.color)
            layer = Image.new("RGBA", garment.size, (*color, 0))
            layer.putalpha(mask)
            overlay = Image.alpha_composite(overlay, layer)

            _draw_pressure_detail(details_draw, box, zone)

    details.putalpha(ImageChops.multiply(details.getchannel("A"), garment_alpha))
    garment = Image.alpha_composite(garment, overlay)
    return Image.alpha_composite(garment, details)


def _fit_render_traits(fit_zones: Sequence[FitZone]) -> dict[str, float]:
    tightness = 0.0
    looseness = 0.0

    for zone in fit_zones:
        pressure = abs(float(zone.pressure_score or 0.0))
        if _is_tight_zone(zone):
            tightness = max(tightness, 0.45 + pressure)
        elif _is_loose_zone(zone):
            looseness = max(looseness, 0.30 + pressure * 0.35)

    tightness = _clamp_float(tightness, 0.0, 1.0)
    looseness = _clamp_float(looseness, 0.0, 1.0)

    return {
        "shadow_multiplier": _clamp_float(1.0 + tightness * 0.20 - looseness * 0.08, 0.82, 1.26),
        "highlight_multiplier": _clamp_float(1.0 + tightness * 0.16 + looseness * 0.08, 0.86, 1.24),
    }


def _garment_zone_boxes(zone_name: str, size: tuple[int, int]) -> list[tuple[int, int, int, int]]:
    width, height = size
    zones = {
        "shoulder": [(0.12, 0.03, 0.88, 0.22)],
        "chest": [(0.16, 0.18, 0.84, 0.43)],
        "waist": [(0.22, 0.45, 0.78, 0.66)],
        "hip": [(0.18, 0.66, 0.82, 0.92)],
        "top_length": [(0.22, 0.72, 0.78, 0.98)],
        "length": [(0.18, 0.72, 0.82, 0.98)],
        "biceps": [(0.02, 0.15, 0.24, 0.54), (0.76, 0.15, 0.98, 0.54)],
        "sleeve": [(0.00, 0.18, 0.27, 0.72), (0.73, 0.18, 1.00, 0.72)],
        "thigh": [(0.28, 0.58, 0.48, 0.98), (0.52, 0.58, 0.72, 0.98)],
        "inseam": [(0.32, 0.60, 0.46, 0.98), (0.54, 0.60, 0.68, 0.98)],
    }

    boxes = []
    for left, top, right, bottom in zones.get(zone_name, []):
        boxes.append(
            (
                int(width * left),
                int(height * top),
                int(width * right),
                int(height * bottom),
            )
        )
    return boxes


def _draw_pressure_detail(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    zone: FitZone,
) -> None:
    left, top, right, bottom = box
    width = max(1, right - left)
    height = max(1, bottom - top)

    if _is_tight_zone(zone):
        color = (255, 244, 214, 90)
        step = max(16, width // 6)
        for x in range(left - height, right + height, step):
            draw.line((x, bottom, x + height, top), fill=color, width=max(2, width // 90))
        return

    if _is_unknown_zone(zone):
        color = (255, 255, 255, 82)
        dot_radius = max(2, width // 44)
        for index, x in enumerate(range(left + width // 5, right, max(18, width // 4))):
            y = top + height // 2 + ((index % 2) * 2 - 1) * height // 7
            draw.ellipse((x - dot_radius, y - dot_radius, x + dot_radius, y + dot_radius), fill=color)
        return

    if _is_loose_zone(zone):
        color = (226, 232, 255, 62)
        for index in range(3):
            y = top + int(height * (0.34 + index * 0.18))
            draw.arc(
                (
                    int(left + width * 0.10),
                    int(y - height * 0.16),
                    int(right - width * 0.10),
                    int(y + height * 0.16),
                ),
                start=8,
                end=172,
                fill=color,
                width=max(2, width // 100),
            )
        return

    color = (255, 255, 255, 54)
    for x in (left + width // 3, right - width // 3):
        draw.line((x, int(top + height * 0.18), x, int(bottom - height * 0.18)), fill=color, width=max(2, width // 110))


def _zone_alpha(zone: FitZone) -> int:
    pressure = abs(float(zone.pressure_score or 0.0))
    if _is_unknown_zone(zone):
        return 16
    if _is_tight_zone(zone):
        return int(34 + min(18, pressure * 14))
    if _is_loose_zone(zone):
        return int(14 + min(8, pressure * 6))
    return 22


def _fit_zone_rgb(color: str) -> tuple[int, int, int]:
    if color == "red":
        return (239, 68, 68)
    if color == "yellow":
        return (245, 158, 11)
    if color == "green":
        return (34, 197, 94)
    if color == "blue":
        return (56, 189, 248)
    return (156, 163, 175)


def _is_tight_zone(zone: FitZone) -> bool:
    status = (zone.status or "").lower()
    return status in {"apertado", "too_small", "tight"} or zone.color == "red"


def _is_loose_zone(zone: FitZone) -> bool:
    status = (zone.status or "").lower()
    return status in {"folgado", "loose"} or zone.color in {"green", "blue"}


def _is_unknown_zone(zone: FitZone) -> bool:
    status = (zone.status or "").lower()
    return status in {"sem_informacao", "unknown"} or zone.color == "gray"


def curve_garment_hem(
    garment_rgba: Image.Image,
    mannequin: MannequinParams,
) -> Image.Image:
    """Cut a shallow curved hem so shirts do not look like flat rectangles."""

    garment = garment_rgba.convert("RGBA")
    width, height = garment.size
    waist_scale = _bounded_scale(mannequin.waist_scale, 0.72, 1.38)
    curve_depth = int(height * (0.026 + max(0.0, 1.0 - waist_scale) * 0.064))

    if curve_depth <= 1:
        return garment

    hem_mask = Image.new("L", garment.size, 0)
    draw = ImageDraw.Draw(hem_mask)
    center = width / 2
    half = max(1, width / 2)

    for x in range(width):
        normalized = abs((x - center) / half)
        bottom_y = int(height - curve_depth + curve_depth * (1 - normalized**2))
        draw.line((x, 0, x, bottom_y), fill=255)

    alpha = ImageChops.multiply(garment.getchannel("A"), hem_mask)
    return Image.merge("RGBA", (*garment.convert("RGB").split(), alpha))


def _map_to_l(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    if image.size != size:
        image = image.resize(size, Image.Resampling.BILINEAR)

    if image.mode == "RGBA":
        luminance = ImageOps.grayscale(image.convert("RGB"))
        return ImageChops.lighter(luminance, image.getchannel("A"))

    if image.mode == "LA":
        return ImageChops.lighter(image.getchannel("L"), image.getchannel("A"))

    return image.convert("L")


def _bounded_scale(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, float(value or 1.0)))


def _clamp_float(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, float(value)))
