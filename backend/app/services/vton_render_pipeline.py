from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from PIL import Image, ImageChops, ImageDraw, ImageOps

from app.models.body import MannequinParams
from app.utils.tiered_cache import get_cache, set_cache, stable_hash

try:
    import numpy as np
except Exception:  # pragma: no cover - keeps Render/local startup resilient.
    np = None  # type: ignore[assignment]

if TYPE_CHECKING:
    import numpy.typing as npt


@dataclass(frozen=True)
class GarmentRenderContext:
    """Inputs used by the 2.5D garment projection pipeline.

    The pipeline order is intentionally fixed: warp first, optional fabric
    bump/displacement second, mannequin shadow/highlight third, and foreground
    occlusion last.
    """

    mannequin: MannequinParams
    body_alpha: Image.Image
    shadow_map_alpha: Image.Image
    light_map_rgba: Optional[Image.Image] = None
    occlusion_mask_alpha: Optional[Image.Image] = None
    shadow_intensity: float = 0.58
    highlight_intensity: float = 0.30
    warp_strength: float = 1.00
    bump_strength: float = 0.26
    curve_hem: bool = True


class MannequinGarmentRenderer:
    """2.5D renderer for placing a 2D garment over a parametric mannequin."""

    def render(
        self,
        garment_rgba: Image.Image,
        context: GarmentRenderContext,
    ) -> Image.Image:
        """Render a garment through warp, lighting and occlusion passes."""

        output = garment_rgba.convert("RGBA")

        if context.warp_strength > 0:
            displacement_map = build_cached_measurement_displacement_map(
                output.size,
                context.mannequin,
                strength=context.warp_strength,
            )
            bump_map = build_fabric_bump_displacement_map(
                output.size,
                context.mannequin,
                strength=context.bump_strength,
            )
            displacement_map = combine_displacement_maps(displacement_map, bump_map)

            if displacement_map is not None:
                output = warp_garment_to_body(output, displacement_map)
            else:
                output = warp_garment_by_profile_bands(
                    output,
                    context.mannequin,
                    strength=context.warp_strength,
                )

        if context.curve_hem:
            output = curve_garment_hem(output, context.mannequin)

        output = apply_mannequin_shading(
            garment_rgba=output,
            shadow_map_alpha=context.shadow_map_alpha,
            light_map_rgba=context.light_map_rgba,
            body_alpha=context.body_alpha,
            shadow_intensity=context.shadow_intensity,
            highlight_intensity=context.highlight_intensity,
        )

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


def warp_garment_to_body(
    garment_rgba: Image.Image,
    displacement_map: Optional["npt.NDArray[np.float32]"],
) -> Image.Image:
    """Warp an RGBA garment with a dense displacement map.

    The displacement map shape is `(height, width, 2)` and stores `(dx, dy)`.
    The output pixel samples the source image at `(x - dx, y - dy)`, matching a
    standard inverse-remap workflow.
    """

    if displacement_map is None or np is None:
        return garment_rgba.convert("RGBA")

    image = garment_rgba.convert("RGBA")
    source = np.asarray(image, dtype=np.float32)
    height, width = source.shape[:2]

    if displacement_map.shape[:2] != (height, width) or displacement_map.shape[-1] != 2:
        raise ValueError(
            "displacement_map must have shape (height, width, 2) matching garment size"
        )

    grid_y, grid_x = np.mgrid[0:height, 0:width].astype(np.float32)
    source_x = grid_x - displacement_map[..., 0]
    source_y = grid_y - displacement_map[..., 1]

    valid = (
        (source_x >= 0)
        & (source_x <= width - 1)
        & (source_y >= 0)
        & (source_y <= height - 1)
    )

    x0 = np.floor(np.clip(source_x, 0, width - 1)).astype(np.int32)
    y0 = np.floor(np.clip(source_y, 0, height - 1)).astype(np.int32)
    x1 = np.clip(x0 + 1, 0, width - 1)
    y1 = np.clip(y0 + 1, 0, height - 1)

    wx = (source_x - x0)[..., None]
    wy = (source_y - y0)[..., None]

    top = source[y0, x0] * (1 - wx) + source[y0, x1] * wx
    bottom = source[y1, x0] * (1 - wx) + source[y1, x1] * wx
    remapped = top * (1 - wy) + bottom * wy
    remapped[..., 3] *= valid.astype(np.float32)

    return Image.fromarray(np.clip(remapped, 0, 255).astype("uint8"), "RGBA")


def build_measurement_displacement_map(
    size: tuple[int, int],
    mannequin: MannequinParams,
    strength: float = 1.0,
) -> Optional["npt.NDArray[np.float32]"]:
    """Build a dense horizontal flow from mannequin chest/waist/hip ratios."""

    if np is None or strength <= 0:
        return None

    width, height = size
    grid_y, grid_x = np.mgrid[0:height, 0:width].astype(np.float32)
    t = grid_y / max(1, height - 1)
    center_x = (width - 1) / 2

    shoulder = 1.00 + (_bounded_scale(mannequin.shoulder_scale, 0.80, 1.26) - 1.00) * 0.16
    chest = 0.99 + (_bounded_scale(mannequin.chest_scale, 0.80, 1.30) - 1.00) * 0.18
    waist = 0.91 + (_bounded_scale(mannequin.waist_scale, 0.74, 1.34) - 1.00) * 0.24
    hip = 0.98 + (_bounded_scale(mannequin.hip_scale, 0.78, 1.32) - 1.00) * 0.14
    thigh_scale = _bounded_scale(getattr(mannequin, "thigh_scale", 1.0), 0.76, 1.42)

    profile = np.empty((height, width), dtype=np.float32)
    first = t < 0.22
    second = (t >= 0.22) & (t < 0.66)
    third = ~first & ~second

    profile[first] = _lerp_np(shoulder, chest, _smooth_step_np(t[first] / 0.22))
    profile[second] = _lerp_np(
        chest,
        waist,
        _smooth_step_np((t[second] - 0.22) / 0.44),
    )
    profile[third] = _lerp_np(
        waist,
        hip + (thigh_scale - 1.0) * 0.05,
        _smooth_step_np((t[third] - 0.66) / 0.34),
    )

    profile = np.clip(profile, 0.72, 1.28)
    dx = (grid_x - center_x) * (1.0 - (1.0 / profile)) * strength
    dy = np.zeros_like(dx, dtype=np.float32)
    return np.dstack((dx, dy)).astype(np.float32)


def build_cached_measurement_displacement_map(
    size: tuple[int, int],
    mannequin: MannequinParams,
    strength: float = 1.0,
) -> Optional["npt.NDArray[np.float32]"]:
    """Cache the dense morphing vector field for repeated size/product visits."""

    key = "morph:" + stable_hash(
        {
            "size": size,
            "strength": strength,
            "measurements": {
                "shoulder": mannequin.shoulder_scale,
                "chest": mannequin.chest_scale,
                "waist": mannequin.waist_scale,
                "hip": mannequin.hip_scale,
                "biceps": getattr(mannequin, "biceps_scale", 1.0),
                "thigh": getattr(mannequin, "thigh_scale", 1.0),
            },
        }
    )
    cached = get_cache(key)
    if cached is not None:
        return cached

    computed = build_measurement_displacement_map(size, mannequin, strength=strength)
    if computed is not None:
        set_cache(key, computed)
    return computed


def build_fabric_bump_displacement_map(
    size: tuple[int, int],
    mannequin: MannequinParams,
    strength: float = 0.26,
) -> Optional["npt.NDArray[np.float32]"]:
    """Generate subtle procedural fabric displacement for tight garments."""

    if np is None or strength <= 0:
        return None

    width, height = size
    grid_y, grid_x = np.mgrid[0:height, 0:width].astype(np.float32)
    x_norm = (grid_x - (width - 1) / 2) / max(1, width / 2)
    t = grid_y / max(1, height - 1)

    waist_delta = abs(_bounded_scale(mannequin.waist_scale, 0.74, 1.34) - 1.0)
    chest_delta = abs(_bounded_scale(mannequin.chest_scale, 0.80, 1.30) - 1.0)
    biceps_delta = abs(_bounded_scale(getattr(mannequin, "biceps_scale", 1.0), 0.72, 1.55) - 1.0)
    envelope = np.exp(-((t - 0.52) / 0.18) ** 2) * (1.0 + waist_delta)
    envelope += np.exp(-((t - 0.30) / 0.14) ** 2) * (0.55 + chest_delta)
    envelope += np.exp(-((t - 0.20) / 0.10) ** 2) * biceps_delta * 0.35
    envelope = np.clip(envelope, 0.0, 1.8)

    wave_x = np.sin((x_norm * 3.5 + t * 1.2) * np.pi)
    wave_y = np.sin((x_norm * 2.0 - t * 1.6) * np.pi)
    dx = wave_x * envelope * 2.3 * strength
    dy = wave_y * envelope * 0.9 * strength
    return np.dstack((dx, dy)).astype(np.float32)


def combine_displacement_maps(
    base_map: Optional["npt.NDArray[np.float32]"],
    detail_map: Optional["npt.NDArray[np.float32]"],
) -> Optional["npt.NDArray[np.float32]"]:
    """Combine two flow fields without mutating either input."""

    if base_map is None:
        return detail_map
    if detail_map is None:
        return base_map
    return (base_map + detail_map).astype("float32")


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


def warp_garment_by_profile_bands(
    garment_rgba: Image.Image,
    mannequin: MannequinParams,
    strength: float = 1.0,
) -> Image.Image:
    """PIL fallback for environments without numpy.

    This avoids per-pixel Python loops by resizing horizontal bands.
    """

    garment = garment_rgba.convert("RGBA")
    output = Image.new("RGBA", garment.size, (0, 0, 0, 0))
    band_count = 40
    height = garment.height

    for band in range(band_count):
        y0 = int(height * band / band_count)
        y1 = int(height * (band + 1) / band_count)
        if y1 <= y0:
            continue

        t = (y0 + y1) / 2 / max(1, height)
        profile = _garment_width_profile(t, mannequin)
        scale = _lerp(1.0, profile, _clamp_float(strength, 0.0, 1.0))
        strip = garment.crop((0, y0, garment.width, y1))
        strip_width = max(1, int(garment.width * scale))
        strip = strip.resize((strip_width, y1 - y0), Image.Resampling.BICUBIC)
        x = (garment.width - strip_width) // 2
        output.alpha_composite(strip, dest=(x, y0))

    return output


def pil_to_cv2(image: Image.Image) -> "npt.NDArray[np.uint8]":
    """Convert PIL RGBA to an OpenCV-style BGRA ndarray for future cv2 hooks."""

    if np is None:
        raise RuntimeError("numpy is required for PIL/OpenCV array conversion")

    rgba = np.asarray(image.convert("RGBA"), dtype=np.uint8)
    return rgba[..., [2, 1, 0, 3]]


def cv2_to_pil(image: "npt.NDArray[np.uint8]") -> Image.Image:
    """Convert an OpenCV-style BGRA/RGB/BGR ndarray back to PIL RGBA."""

    if np is None:
        raise RuntimeError("numpy is required for OpenCV/PIL array conversion")

    if image.ndim != 3:
        raise ValueError("Expected a 3-channel or 4-channel image array")

    if image.shape[2] == 4:
        rgba = image[..., [2, 1, 0, 3]]
    elif image.shape[2] == 3:
        rgb = image[..., [2, 1, 0]]
        alpha = np.full((*rgb.shape[:2], 1), 255, dtype=np.uint8)
        rgba = np.concatenate([rgb, alpha], axis=2)
    else:
        raise ValueError("Expected 3 or 4 channels")

    return Image.fromarray(rgba.astype("uint8"), "RGBA")


def _map_to_l(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    if image.size != size:
        image = image.resize(size, Image.Resampling.BILINEAR)

    if image.mode == "RGBA":
        luminance = ImageOps.grayscale(image.convert("RGB"))
        return ImageChops.lighter(luminance, image.getchannel("A"))

    if image.mode == "LA":
        return ImageChops.lighter(image.getchannel("L"), image.getchannel("A"))

    return image.convert("L")


def _garment_width_profile(t: float, mannequin: MannequinParams) -> float:
    shoulder_scale = _bounded_scale(mannequin.shoulder_scale, 0.80, 1.25)
    chest_scale = _bounded_scale(mannequin.chest_scale, 0.80, 1.25)
    waist_scale = _bounded_scale(mannequin.waist_scale, 0.76, 1.30)
    hip_scale = _bounded_scale(mannequin.hip_scale, 0.82, 1.26)

    shoulder = 1.00 + (shoulder_scale - 1.00) * 0.16
    chest = 0.98 + (chest_scale - 1.00) * 0.16
    waist = 0.90 + (waist_scale - 1.00) * 0.24 + (waist_scale - chest_scale) * 0.04
    hem = 0.97 + (hip_scale - 1.00) * 0.14

    if t < 0.22:
        return _lerp(shoulder, chest, _smooth_step(t / 0.22))
    if t < 0.66:
        return _lerp(chest, waist, _smooth_step((t - 0.22) / 0.44))
    return _lerp(waist, hem, _smooth_step((t - 0.66) / 0.34))


def _bounded_scale(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, float(value or 1.0)))


def _clamp_float(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, float(value)))


def _smooth_step(value: float) -> float:
    value = _clamp_float(value, 0.0, 1.0)
    return value * value * (3 - 2 * value)


def _smooth_step_np(value):
    return np.clip(value, 0.0, 1.0) ** 2 * (3 - 2 * np.clip(value, 0.0, 1.0))


def _lerp(start: float, end: float, progress: float) -> float:
    return start + (end - start) * progress


def _lerp_np(start: float, end: float, progress):
    return start + (end - start) * progress
