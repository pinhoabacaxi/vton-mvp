# -*- coding: utf-8 -*-
import os
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from app.models.mannequin import MannequinRenderInput, MannequinRenderResult
from app.services.image_processor import UPLOAD_DIR
from app.services.url_utils import absolute_url


CANVAS_SIZE = (900, 1200)
PREVIEW_SIZE = (360, 480)
SUPERSAMPLE_SCALE = 2
MANNEQUIN_DIR = UPLOAD_DIR / "mannequin"
MANNEQUIN_PREVIEW_DIR = MANNEQUIN_DIR / "previews"
BODY_MESH_ASSET_DIR = Path(__file__).resolve().parents[1] / "assets" / "body_mesh"
BODY_MESH_PREVIEW_DIR = BODY_MESH_ASSET_DIR / "previews"
BODY_MESH_MOCK_DIR = BODY_MESH_ASSET_DIR / "mock"
BODY_MESH_FAMILY_DIR = BODY_MESH_ASSET_DIR / "families"

MANNEQUIN_DIR.mkdir(parents=True, exist_ok=True)
MANNEQUIN_PREVIEW_DIR.mkdir(parents=True, exist_ok=True)


def render_front_mannequin(data: MannequinRenderInput) -> MannequinRenderResult:
    filename = f"mannequin_front_{uuid4().hex}.png"
    output_path = MANNEQUIN_DIR / filename

    image, _, _, _ = render_mannequin_scene(
        data.mannequin,
        size=CANVAS_SIZE,
        include_label=True,
    )
    image.save(output_path, "PNG", optimize=True)

    return MannequinRenderResult(
        image_url=absolute_url(f"/uploads/mannequin/{filename}"),
        image_path=str(output_path),
        message="Render frontal do manequim gerado com sucesso.",
    )


def render_tryon_person_scene(
    mannequin,
    size: tuple[int, int] = CANVAS_SIZE,
) -> Image.Image:
    """Render a bright, human-like try-on person for external VTON providers."""

    high_size = (size[0] * SUPERSAMPLE_SCALE, size[1] * SUPERSAMPLE_SCALE)
    scene = _create_studio_background(high_size)
    body_layer, body_alpha, body_shadow, body_light = build_parametric_body_layers(
        mannequin,
        high_size,
    )
    scene.alpha_composite(body_layer)
    _draw_tryon_base_clothing(scene, body_alpha, body_shadow, body_light, high_size)
    return _downsample_rgba(scene, size)


def render_body_model_preview(base_model_id: str) -> str:
    asset_preview = _mesh_preview_asset_path(base_model_id)
    output_path = MANNEQUIN_PREVIEW_DIR / f"{base_model_id}.png"

    if _use_mesh_asset_mannequin() and asset_preview.exists():
        with Image.open(asset_preview) as asset:
            asset.convert("RGBA").save(output_path, "PNG", optimize=True)
        return absolute_url(f"/uploads/mannequin/previews/{base_model_id}.png")

    from app.models.body import FineTuneInput
    from app.services.body_recommender import build_mannequin_params

    input_data = FineTuneInput(
        base_model_id=base_model_id,
        height_cm=170,
        weight_kg=64,
        age=23,
        chest_cm=95,
        waist_cm=78,
        hip_cm=98,
        shoulder_cm=42,
        sleeve_cm=60,
        biceps_cm=31,
        inseam_cm=78,
        thigh_cm=56,
        skin_tone="medium",
    )
    mannequin = build_mannequin_params(input_data)
    image, _, _, _ = render_mannequin_scene(
        mannequin,
        size=PREVIEW_SIZE,
        include_label=False,
    )

    image.save(output_path, "PNG", optimize=True)
    return absolute_url(f"/uploads/mannequin/previews/{base_model_id}.png")


def render_mannequin_scene(
    mannequin,
    size: tuple[int, int] = CANVAS_SIZE,
    include_label: bool = False,
) -> tuple[Image.Image, Image.Image, Image.Image, Image.Image]:
    asset_scene = _render_mesh_asset_scene(mannequin, size)
    if asset_scene is not None:
        scene, body_alpha, body_shadow, body_light = asset_scene
        if include_label:
            draw = ImageDraw.Draw(scene)
            label_xy = (int(size[0] * 0.045), int(size[1] * 0.035))
            draw.text(label_xy, "Mannequin frontal", fill="#e9d5ff")
        return scene, body_alpha, body_shadow, body_light

    high_size = (size[0] * SUPERSAMPLE_SCALE, size[1] * SUPERSAMPLE_SCALE)
    scene = _create_background(high_size)
    body_layer, body_alpha, body_shadow, body_light = build_parametric_body_layers(
        mannequin,
        high_size,
    )
    scene.alpha_composite(body_layer)

    if include_label:
        draw = ImageDraw.Draw(scene)
        label_xy = (int(high_size[0] * 0.045), int(high_size[1] * 0.035))
        draw.text(label_xy, "Mannequin frontal", fill="#e9d5ff")

    return (
        _downsample_rgba(scene, size),
        _downsample_l(body_alpha, size),
        _downsample_l(body_shadow, size),
        _downsample_l(body_light, size),
    )


def draw_parametric_body(
    mannequin,
    size: tuple[int, int] = CANVAS_SIZE,
) -> Image.Image:
    high_size = (size[0] * SUPERSAMPLE_SCALE, size[1] * SUPERSAMPLE_SCALE)
    body_layer, _, _, _ = build_parametric_body_layers(mannequin, high_size)
    return _downsample_rgba(body_layer, size)


def _render_mesh_asset_scene(
    mannequin,
    size: tuple[int, int],
) -> tuple[Image.Image, Image.Image, Image.Image, Image.Image] | None:
    if not _use_mesh_asset_mannequin():
        return None

    model_id = str(getattr(mannequin, "base_model_id", "balanced_soft") or "balanced_soft")
    asset_path = _mesh_mock_asset_path(model_id)
    if not asset_path.exists():
        asset_path = _mesh_mock_asset_path("balanced_soft")
    if not asset_path.exists():
        return None

    with Image.open(asset_path) as asset:
        body_layer = _fit_mesh_asset_to_canvas(asset.convert("RGBA"), size)

    body_layer = _morph_mesh_asset_to_measurements(body_layer, mannequin)
    body_alpha = body_layer.getchannel("A")
    ambient_occlusion = _build_ambient_occlusion_mask(body_alpha, size)
    body_shadow = _draw_soft_shadow(body_alpha, ambient_occlusion, size)
    body_light = _draw_torso_volume(body_alpha, size)

    scene = _create_background(size)
    scene.alpha_composite(body_layer)
    return scene, body_alpha, body_shadow, body_light


def _fit_mesh_asset_to_canvas(asset: Image.Image, size: tuple[int, int]) -> Image.Image:
    if asset.size == size:
        return asset.copy()

    fitted = Image.new("RGBA", size, (0, 0, 0, 0))
    scale = min(size[0] / max(1, asset.width), size[1] / max(1, asset.height))
    resized = asset.resize(
        (max(1, int(asset.width * scale)), max(1, int(asset.height * scale))),
        Image.Resampling.LANCZOS,
    )
    left = (size[0] - resized.width) // 2
    top = (size[1] - resized.height) // 2
    fitted.alpha_composite(resized, (left, top))
    return fitted


def _morph_mesh_asset_to_measurements(image: Image.Image, mannequin) -> Image.Image:
    width, height = image.size
    morphed = Image.new("RGBA", image.size, (0, 0, 0, 0))
    band_height = max(2, height // 260)

    for top in range(0, height, band_height):
        bottom = min(height, top + band_height)
        band = image.crop((0, top, width, bottom))
        scale = _mesh_asset_band_scale((top + bottom) * 0.5 / max(1, height), mannequin)
        resized_width = max(1, int(width * scale))
        resized_band = band.resize((resized_width, bottom - top), Image.Resampling.LANCZOS)

        if resized_width > width:
            crop_left = (resized_width - width) // 2
            resized_band = resized_band.crop((crop_left, 0, crop_left + width, bottom - top))
            morphed.alpha_composite(resized_band, (0, top))
        else:
            left = (width - resized_width) // 2
            morphed.alpha_composite(resized_band, (left, top))

    alpha = morphed.getchannel("A").filter(ImageFilter.GaussianBlur(radius=max(0.2, width * 0.0007)))
    morphed.putalpha(alpha)
    return morphed


def _mesh_asset_band_scale(y_ratio: float, mannequin) -> float:
    scale = 1.0
    scale += (_bounded_scale(mannequin, "shoulder_scale", 0.78, 1.30) - 1.0) * _band_weight(y_ratio, 0.305, 0.060) * 0.28
    scale += (_bounded_scale(mannequin, "chest_scale", 0.76, 1.34) - 1.0) * _band_weight(y_ratio, 0.395, 0.095) * 0.30
    scale += (_bounded_scale(mannequin, "waist_scale", 0.72, 1.38) - 1.0) * _band_weight(y_ratio, 0.510, 0.075) * 0.26
    scale += (_bounded_scale(mannequin, "hip_scale", 0.76, 1.38) - 1.0) * _band_weight(y_ratio, 0.615, 0.085) * 0.30
    scale += (_bounded_scale(mannequin, "thigh_scale", 0.72, 1.55) - 1.0) * _band_weight(y_ratio, 0.745, 0.115) * 0.22
    scale += (_bounded_scale(mannequin, "biceps_scale", 0.72, 1.55) - 1.0) * _band_weight(y_ratio, 0.430, 0.160) * 0.08
    return max(0.88, min(1.16, scale))


def _band_weight(position: float, center: float, radius: float) -> float:
    distance = abs(position - center) / max(radius, 0.001)
    if distance >= 1.0:
        return 0.0
    return (1.0 - distance * distance) ** 2


def _mesh_preview_asset_path(base_model_id: str) -> Path:
    family_path = BODY_MESH_FAMILY_DIR / _mesh_asset_family() / "previews" / f"{base_model_id}.png"
    if family_path.exists():
        return family_path
    neutral_path = BODY_MESH_FAMILY_DIR / "neutral" / "previews" / f"{base_model_id}.png"
    if neutral_path.exists():
        return neutral_path
    return BODY_MESH_PREVIEW_DIR / f"{base_model_id}.png"


def _mesh_mock_asset_path(base_model_id: str, family: str | None = None) -> Path:
    selected_family = family or _mesh_asset_family()
    family_path = BODY_MESH_FAMILY_DIR / selected_family / "mock" / f"{base_model_id}.png"
    if family_path.exists():
        return family_path
    neutral_path = BODY_MESH_FAMILY_DIR / "neutral" / "mock" / f"{base_model_id}.png"
    if neutral_path.exists():
        return neutral_path
    return BODY_MESH_MOCK_DIR / f"{base_model_id}.png"


def _mesh_asset_family() -> str:
    return os.getenv("VTON_BODY_MESH_FAMILY", "neutral").strip().lower() or "neutral"


def build_parametric_body_layers(
    mannequin,
    size: tuple[int, int] = CANVAS_SIZE,
) -> tuple[Image.Image, Image.Image, Image.Image, Image.Image]:
    body_alpha = _build_body_alpha_mask(mannequin, size)
    ambient_occlusion = _build_ambient_occlusion_mask(body_alpha, size)
    core_shadow = _draw_soft_shadow(body_alpha, ambient_occlusion, size)
    body_light = _draw_torso_volume(body_alpha, size)

    skin_rgb = _apply_skin_texture(
        Image.new("RGB", size, _body_material_rgb(getattr(mannequin, "skin_tone", "medium"))),
        body_alpha,
    )

    shade_factor = core_shadow.point(lambda value: max(0, 255 - int(value * 0.50)))
    shaded_rgb = ImageChops.multiply(
        skin_rgb,
        Image.merge("RGB", (shade_factor, shade_factor, shade_factor)),
    )

    body_layer = Image.merge("RGBA", (*shaded_rgb.split(), body_alpha))

    highlight = Image.new("RGBA", size, (*_body_highlight_rgb(), 0))
    highlight.putalpha(body_light.point(lambda value: int(value * 0.70)))
    body_layer = Image.alpha_composite(body_layer, highlight)

    body_layer = _apply_surface_anatomy(body_layer, body_alpha, size)

    rim_light = Image.new("RGBA", size, (*_body_rim_rgb(), 0))
    rim_light.putalpha(_build_rim_light_mask(body_alpha, size))
    body_layer = Image.alpha_composite(body_layer, rim_light)

    return body_layer, body_alpha, core_shadow, body_light


def _create_background(size: tuple[int, int]) -> Image.Image:
    width, height = size
    image = Image.new("RGBA", size, "#170b25")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, width, height), fill="#170b25")
    draw.ellipse(
        (
            int(width * -0.20),
            int(height * -0.10),
            int(width * 0.58),
            int(height * 0.44),
        ),
        fill="#311d5a",
    )
    draw.ellipse(
        (
            int(width * 0.42),
            int(height * 0.60),
            int(width * 1.20),
            int(height * 1.05),
        ),
        fill="#2d1461",
    )
    return image


def _create_studio_background(size: tuple[int, int]) -> Image.Image:
    width, height = size
    image = Image.new("RGBA", size, "#f6f0ea")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, width, height), fill="#f6f0ea")
    draw.ellipse(
        (
            int(width * 0.12),
            int(height * 0.04),
            int(width * 0.88),
            int(height * 0.98),
        ),
        fill="#fffaf5",
    )
    draw.ellipse(
        (
            int(width * 0.28),
            int(height * 0.86),
            int(width * 0.72),
            int(height * 0.94),
        ),
        fill="#d8cabf",
    )
    return image


def _build_body_alpha_mask(mannequin, size: tuple[int, int]) -> Image.Image:
    metrics = _body_metrics(mannequin, size)
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)

    _draw_head_and_neck(draw, metrics)
    _draw_torso_mask(draw, metrics)
    _draw_tapered_limb(
        draw,
        _quadratic_points(
            metrics["left_shoulder_joint"],
            metrics["left_elbow"],
            metrics["left_wrist"],
            28,
        ),
        metrics["upper_arm_width"],
        metrics["wrist_width"],
    )
    _draw_tapered_limb(
        draw,
        _quadratic_points(
            metrics["right_shoulder_joint"],
            metrics["right_elbow"],
            metrics["right_wrist"],
            28,
        ),
        metrics["upper_arm_width"],
        metrics["wrist_width"],
    )
    _draw_tapered_limb(
        draw,
        _quadratic_points(
            metrics["left_thigh"],
            metrics["left_knee"],
            metrics["left_ankle"],
            32,
        ),
        metrics["thigh_width"],
        metrics["ankle_width"],
    )
    _draw_tapered_limb(
        draw,
        _quadratic_points(
            metrics["right_thigh"],
            metrics["right_knee"],
            metrics["right_ankle"],
            32,
        ),
        metrics["thigh_width"],
        metrics["ankle_width"],
    )

    _carve_inner_leg_gap(draw, metrics)
    return mask.filter(ImageFilter.GaussianBlur(radius=max(0.7, size[0] * 0.0016)))


def _draw_head_and_neck(draw: ImageDraw.ImageDraw, metrics: dict[str, float]) -> None:
    cx = metrics["center_x"]
    head_cy = metrics["head_cy"]
    head_w = metrics["head_w"]
    head_h = metrics["head_h"]
    jaw_w = head_w * 0.42
    jaw_y = head_cy + head_h * 0.42

    head_points = _cubic_closed_shape(
        [
            (cx, head_cy - head_h * 0.54),
            (cx + head_w * 0.50, head_cy - head_h * 0.34),
            (cx + head_w * 0.44, head_cy + head_h * 0.24),
            (cx + jaw_w, jaw_y),
            (cx, head_cy + head_h * 0.50),
            (cx - jaw_w, jaw_y),
            (cx - head_w * 0.44, head_cy + head_h * 0.24),
            (cx - head_w * 0.50, head_cy - head_h * 0.34),
        ],
        8,
    )
    draw.polygon([(int(x), int(y)) for x, y in head_points], fill=255)

    neck_top = head_cy + head_h * 0.32
    neck_bottom = metrics["shoulder_y"] + metrics["height"] * 0.014
    neck_half = metrics["neck_half"]
    trap_half = metrics["shoulder_half"] * 0.30
    neck_polygon = [
        (cx - neck_half * 0.74, neck_top),
        (cx + neck_half * 0.74, neck_top),
        (cx + trap_half, neck_bottom),
        (cx + neck_half * 0.70, neck_bottom + metrics["height"] * 0.020),
        (cx - neck_half * 0.70, neck_bottom + metrics["height"] * 0.020),
        (cx - trap_half, neck_bottom),
    ]
    draw.polygon([(int(x), int(y)) for x, y in neck_polygon], fill=255)


def _draw_torso_mask(draw: ImageDraw.ImageDraw, metrics: dict[str, float]) -> None:
    cx = metrics["center_x"]
    shoulder_y = metrics["shoulder_y"]
    chest_y = metrics["chest_y"]
    waist_y = metrics["waist_y"]
    hip_y = metrics["hip_y"]
    pelvis_y = metrics["pelvis_y"]

    right = []
    right.extend(
        _cubic_points(
            (cx + metrics["neck_half"], shoulder_y - metrics["height"] * 0.020),
            (cx + metrics["shoulder_half"] * 0.38, shoulder_y - metrics["height"] * 0.050),
            (cx + metrics["shoulder_half"] * 0.90, shoulder_y - metrics["height"] * 0.030),
            (cx + metrics["shoulder_half"], shoulder_y + metrics["height"] * 0.038),
            20,
        )
    )
    right.extend(
        _cubic_points(
            right[-1],
            (cx + metrics["chest_half"] * 1.10, shoulder_y + metrics["height"] * 0.108),
            (cx + metrics["chest_half"] * 1.06, chest_y - metrics["height"] * 0.050),
            (cx + metrics["chest_half"], chest_y),
            20,
        )[1:]
    )
    right.extend(
        _cubic_points(
            right[-1],
            (cx + metrics["chest_half"] * 0.92, chest_y + metrics["height"] * 0.060),
            (cx + metrics["waist_half"] * 1.08, waist_y - metrics["height"] * 0.050),
            (cx + metrics["waist_half"], waist_y),
            24,
        )[1:]
    )
    right.extend(
        _cubic_points(
            right[-1],
            (cx + metrics["waist_half"] * 1.02, waist_y + metrics["height"] * 0.055),
            (cx + metrics["hip_half"] * 0.98, hip_y - metrics["height"] * 0.055),
            (cx + metrics["hip_half"], hip_y),
            24,
        )[1:]
    )
    right.extend(
        _cubic_points(
            right[-1],
            (cx + metrics["hip_half"] * 0.95, hip_y + metrics["height"] * 0.035),
            (cx + metrics["pelvis_half"] * 1.16, pelvis_y - metrics["height"] * 0.012),
            (cx + metrics["pelvis_half"], pelvis_y),
            16,
        )[1:]
    )

    left = [(cx - (x - cx), y) for x, y in reversed(right)]
    draw.polygon([(int(x), int(y)) for x, y in right + left], fill=255)


def _draw_tapered_limb(
    draw: ImageDraw.ImageDraw,
    points: list[tuple[float, float]],
    start_width: float,
    end_width: float,
) -> None:
    if len(points) < 2:
        return

    left_edge: list[tuple[float, float]] = []
    right_edge: list[tuple[float, float]] = []

    for index, point in enumerate(points):
        t = index / max(1, len(points) - 1)
        width = _lerp(start_width, end_width, _smooth_step(t))
        if index < len(points) - 1:
            next_point = points[index + 1]
        else:
            next_point = points[index - 1]
        dx = next_point[0] - point[0]
        dy = next_point[1] - point[1]
        length = max(0.001, (dx * dx + dy * dy) ** 0.5)
        nx = -dy / length
        ny = dx / length
        half = width * 0.5
        left_edge.append((point[0] + nx * half, point[1] + ny * half))
        right_edge.append((point[0] - nx * half, point[1] - ny * half))

    draw.polygon(
        [(int(x), int(y)) for x, y in left_edge + list(reversed(right_edge))],
        fill=255,
    )

    for index in range(len(points)):
        t = index / max(1, len(points) - 2)
        width = _lerp(start_width, end_width, _smooth_step(t))
        radius = max(4, int(width / 2))
        x, y = points[index]
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=255)

    radius = max(4, int(end_width / 2))
    x, y = points[-1]
    draw.ellipse((x - radius * 0.82, y - radius * 1.22, x + radius * 0.82, y + radius * 1.22), fill=255)


def _carve_inner_leg_gap(draw: ImageDraw.ImageDraw, metrics: dict[str, float]) -> None:
    cx = metrics["center_x"]
    gap_half = metrics["height"] * 0.018
    draw.rounded_rectangle(
        (
            cx - gap_half,
            metrics["pelvis_y"] - metrics["height"] * 0.006,
            cx + gap_half,
            metrics["pelvis_y"] + metrics["height"] * 0.085,
        ),
        radius=int(gap_half),
        fill=0,
    )


def _draw_soft_shadow(
    body_alpha: Image.Image,
    ambient_occlusion: Image.Image,
    size: tuple[int, int],
) -> Image.Image:
    width, height = size
    center_x = width / 2
    side_gradient = Image.new("L", size, 0)
    draw = ImageDraw.Draw(side_gradient)

    for x in range(width):
        distance = abs((x - center_x) / max(1, width * 0.40))
        value = int(min(165, 8 + 130 * (distance ** 2.12)))
        draw.line((x, 0, x, height), fill=value)

    eroded = body_alpha.filter(ImageFilter.MinFilter(19))
    edge = ImageChops.subtract(body_alpha, eroded)
    edge = edge.filter(ImageFilter.GaussianBlur(radius=max(5, int(width * 0.012))))
    edge = edge.point(lambda value: int(value * 0.78))

    shadow = ImageChops.lighter(side_gradient, edge)
    shadow = ImageChops.lighter(shadow, ambient_occlusion)
    return ImageChops.multiply(shadow, body_alpha)


def _draw_torso_volume(body_alpha: Image.Image, size: tuple[int, int]) -> Image.Image:
    width, height = size
    light = Image.new("L", size, 0)
    draw = ImageDraw.Draw(light)

    _draw_soft_highlight(draw, width * 0.50, height * 0.39, width * 0.18, height * 0.24, 62)
    _draw_soft_highlight(draw, width * 0.43, height * 0.75, width * 0.065, height * 0.18, 42)
    _draw_soft_highlight(draw, width * 0.57, height * 0.75, width * 0.065, height * 0.18, 42)
    _draw_soft_highlight(draw, width * 0.245, height * 0.48, width * 0.045, height * 0.18, 30)
    _draw_soft_highlight(draw, width * 0.755, height * 0.48, width * 0.045, height * 0.18, 30)
    _draw_soft_highlight(draw, width * 0.50, height * 0.15, width * 0.040, height * 0.050, 24)

    light = light.filter(ImageFilter.GaussianBlur(radius=max(10, int(width * 0.025))))
    return ImageChops.multiply(light, body_alpha)


def _draw_tryon_base_clothing(
    scene: Image.Image,
    body_alpha: Image.Image,
    body_shadow: Image.Image,
    body_light: Image.Image,
    size: tuple[int, int],
) -> None:
    width, height = size
    center_x = width // 2
    clothing_mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(clothing_mask)

    top_points = [
        (center_x - width * 0.108, height * 0.324),
        (center_x + width * 0.108, height * 0.324),
        (center_x + width * 0.153, height * 0.530),
        (center_x + width * 0.100, height * 0.626),
        (center_x - width * 0.100, height * 0.626),
        (center_x - width * 0.153, height * 0.530),
    ]
    draw.polygon([(int(x), int(y)) for x, y in top_points], fill=235)
    draw.ellipse(
        (
            center_x - width * 0.055,
            height * 0.286,
            center_x + width * 0.055,
            height * 0.390,
        ),
        fill=0,
    )

    shorts_box = (
        center_x - width * 0.130,
        height * 0.640,
        center_x + width * 0.130,
        height * 0.745,
    )
    draw.rounded_rectangle(shorts_box, radius=int(width * 0.034), fill=225)
    draw.rounded_rectangle(
        (
            center_x - width * 0.025,
            height * 0.670,
            center_x + width * 0.025,
            height * 0.770,
        ),
        radius=int(width * 0.020),
        fill=0,
    )

    clothing_mask = ImageChops.multiply(clothing_mask.filter(ImageFilter.GaussianBlur(radius=1.2)), body_alpha)
    fabric = Image.new("RGBA", size, (238, 232, 226, 0))
    fabric.putalpha(clothing_mask)

    shadow = Image.new("RGBA", size, (94, 78, 92, 0))
    shadow.putalpha(ImageChops.multiply(body_shadow, clothing_mask).point(lambda value: int(value * 0.34)))
    light = Image.new("RGBA", size, (255, 255, 255, 0))
    light.putalpha(ImageChops.multiply(body_light, clothing_mask).point(lambda value: int(value * 0.20)))

    scene.alpha_composite(fabric)
    scene.alpha_composite(shadow)
    scene.alpha_composite(light)


def _draw_soft_highlight(
    draw: ImageDraw.ImageDraw,
    cx: float,
    cy: float,
    rx: float,
    ry: float,
    fill: int,
) -> None:
    draw.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=fill)


def _apply_surface_anatomy(
    body_layer: Image.Image,
    body_alpha: Image.Image,
    size: tuple[int, int],
) -> Image.Image:
    """Add subtle mannequin anatomy without turning the render into a diagram."""

    width, height = size
    detail_alpha = Image.new("L", size, 0)
    draw = ImageDraw.Draw(detail_alpha)
    line_width = max(2, width // 220)
    cx = width // 2

    draw.arc(
        (width * 0.36, height * 0.285, width * 0.50, height * 0.385),
        205,
        350,
        fill=42,
        width=line_width,
    )
    draw.arc(
        (width * 0.50, height * 0.285, width * 0.64, height * 0.385),
        190,
        335,
        fill=42,
        width=line_width,
    )
    draw.line(
        (cx, height * 0.352, cx, height * 0.555),
        fill=28,
        width=max(1, line_width - 1),
    )
    draw.arc(
        (width * 0.365, height * 0.405, width * 0.635, height * 0.585),
        20,
        160,
        fill=24,
        width=max(1, line_width - 1),
    )
    draw.arc(
        (width * 0.355, height * 0.590, width * 0.645, height * 0.765),
        200,
        340,
        fill=36,
        width=line_width,
    )
    draw.arc(
        (width * 0.385, height * 0.732, width * 0.490, height * 0.835),
        250,
        345,
        fill=32,
        width=max(1, line_width - 1),
    )
    draw.arc(
        (width * 0.510, height * 0.732, width * 0.615, height * 0.835),
        195,
        290,
        fill=32,
        width=max(1, line_width - 1),
    )

    detail_alpha = detail_alpha.filter(ImageFilter.GaussianBlur(radius=max(2, width * 0.004)))
    detail_alpha = ImageChops.multiply(detail_alpha, body_alpha)
    detail = Image.new("RGBA", size, (*_body_detail_rgb(), 0))
    detail.putalpha(detail_alpha.point(lambda value: int(value * 0.74)))

    soft_highlight = Image.new("L", size, 0)
    highlight_draw = ImageDraw.Draw(soft_highlight)
    highlight_draw.ellipse((width * 0.42, height * 0.315, width * 0.58, height * 0.505), fill=38)
    highlight_draw.ellipse((width * 0.405, height * 0.670, width * 0.475, height * 0.900), fill=30)
    highlight_draw.ellipse((width * 0.525, height * 0.670, width * 0.595, height * 0.900), fill=30)
    soft_highlight = soft_highlight.filter(ImageFilter.GaussianBlur(radius=max(8, width * 0.017)))
    soft_highlight = ImageChops.multiply(soft_highlight, body_alpha)
    light = Image.new("RGBA", size, (*_body_highlight_rgb(), 0))
    light.putalpha(soft_highlight.point(lambda value: int(value * 0.58)))

    return Image.alpha_composite(Image.alpha_composite(body_layer, detail), light)


def _build_ambient_occlusion_mask(body_alpha: Image.Image, size: tuple[int, int]) -> Image.Image:
    width, height = size
    ao = Image.new("L", size, 0)
    draw = ImageDraw.Draw(ao)

    draw.ellipse((width * 0.42, height * 0.255, width * 0.58, height * 0.330), fill=90)
    draw.ellipse((width * 0.225, height * 0.270, width * 0.365, height * 0.375), fill=82)
    draw.ellipse((width * 0.635, height * 0.270, width * 0.775, height * 0.375), fill=82)
    draw.ellipse((width * 0.405, height * 0.685, width * 0.595, height * 0.765), fill=96)
    draw.ellipse((width * 0.355, height * 0.705, width * 0.480, height * 0.785), fill=62)
    draw.ellipse((width * 0.520, height * 0.705, width * 0.645, height * 0.785), fill=62)

    ao = ao.filter(ImageFilter.GaussianBlur(radius=max(10, int(width * 0.026))))
    return ImageChops.multiply(ao, body_alpha)


def _apply_skin_texture(base_rgb: Image.Image, body_alpha: Image.Image) -> Image.Image:
    noise = Image.effect_noise(base_rgb.size, 5.5).convert("L")
    factor = noise.point(lambda value: max(247, min(255, 251 + int((value - 128) * 0.018))))
    textured = ImageChops.multiply(base_rgb, Image.merge("RGB", (factor, factor, factor)))

    warmth = Image.new("RGB", base_rgb.size, (6, 2, 0))
    texture_alpha = body_alpha.point(lambda value: int(value * 0.012))
    textured.paste(ImageChops.add(textured, warmth), mask=texture_alpha)
    return textured


def _build_rim_light_mask(body_alpha: Image.Image, size: tuple[int, int]) -> Image.Image:
    blurred = body_alpha.filter(ImageFilter.GaussianBlur(radius=max(4, int(size[0] * 0.009))))
    rim = ImageChops.subtract(blurred, body_alpha.filter(ImageFilter.MinFilter(7)))
    return rim.point(lambda value: int(value * 0.32))


def _body_metrics(mannequin, size: tuple[int, int]) -> dict[str, float]:
    width, height = size
    center_x = width * 0.50
    shoulder_scale = _bounded_scale(mannequin, "shoulder_scale", 0.78, 1.30)
    chest_scale = _bounded_scale(mannequin, "chest_scale", 0.76, 1.34)
    waist_scale = _bounded_scale(mannequin, "waist_scale", 0.72, 1.38)
    hip_scale = _bounded_scale(mannequin, "hip_scale", 0.76, 1.38)
    arm_scale = _bounded_scale(mannequin, "arm_scale", 0.82, 1.22)
    leg_scale = _bounded_scale(mannequin, "leg_scale", 0.86, 1.18)
    biceps_scale = _bounded_scale(mannequin, "biceps_scale", 0.72, 1.55)
    thigh_scale = _bounded_scale(mannequin, "thigh_scale", 0.72, 1.55)

    shoulder_y = height * 0.288
    chest_y = height * 0.425
    waist_y = height * 0.548
    hip_y = height * 0.654
    pelvis_y = height * 0.712

    shoulder_half = width * 0.154 * shoulder_scale
    chest_half = width * 0.142 * chest_scale
    waist_half = width * 0.100 * waist_scale
    hip_half = width * 0.132 * hip_scale
    pelvis_half = width * 0.092

    return {
        "width": width,
        "height": height,
        "center_x": center_x,
        "head_cy": height * 0.147,
        "head_w": width * 0.096,
        "head_h": height * 0.108,
        "neck_half": width * 0.025,
        "shoulder_y": shoulder_y,
        "chest_y": chest_y,
        "waist_y": waist_y,
        "hip_y": hip_y,
        "pelvis_y": pelvis_y,
        "shoulder_half": shoulder_half,
        "chest_half": chest_half,
        "waist_half": waist_half,
        "hip_half": hip_half,
        "pelvis_half": pelvis_half,
        "left_shoulder_joint": (center_x - shoulder_half * 0.98, shoulder_y + height * 0.072),
        "right_shoulder_joint": (center_x + shoulder_half * 0.98, shoulder_y + height * 0.072),
        "left_elbow": (center_x - shoulder_half * 1.22, height * 0.510),
        "right_elbow": (center_x + shoulder_half * 1.22, height * 0.510),
        "left_wrist": (center_x - shoulder_half * 1.08, height * 0.694),
        "right_wrist": (center_x + shoulder_half * 1.08, height * 0.694),
        "upper_arm_width": width * 0.042 * arm_scale * biceps_scale,
        "wrist_width": width * 0.024 * arm_scale,
        "left_thigh": (center_x - width * 0.058, pelvis_y - height * 0.006),
        "right_thigh": (center_x + width * 0.058, pelvis_y - height * 0.006),
        "left_knee": (center_x - width * 0.070, height * 0.820),
        "right_knee": (center_x + width * 0.070, height * 0.820),
        "left_ankle": (center_x - width * 0.060, height * min(0.950, 0.920 + (leg_scale - 1) * 0.045)),
        "right_ankle": (center_x + width * 0.060, height * min(0.950, 0.920 + (leg_scale - 1) * 0.045)),
        "thigh_width": width * 0.062 * leg_scale * thigh_scale,
        "ankle_width": width * 0.031 * leg_scale,
    }


def _cubic_closed_shape(
    anchors: list[tuple[float, float]],
    steps_per_edge: int,
) -> list[tuple[float, float]]:
    points = []
    count = len(anchors)

    for index, current in enumerate(anchors):
        previous_point = anchors[(index - 1) % count]
        next_point = anchors[(index + 1) % count]
        next_next = anchors[(index + 2) % count]

        control_1 = (
            current[0] + (next_point[0] - previous_point[0]) / 6,
            current[1] + (next_point[1] - previous_point[1]) / 6,
        )
        control_2 = (
            next_point[0] - (next_next[0] - current[0]) / 6,
            next_point[1] - (next_next[1] - current[1]) / 6,
        )
        segment = _cubic_points(current, control_1, control_2, next_point, steps_per_edge)
        points.extend(segment[:-1])

    return points


def _cubic_points(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    steps: int,
) -> list[tuple[float, float]]:
    points = []
    for index in range(steps + 1):
        t = index / steps
        inv = 1 - t
        x = inv**3 * p0[0] + 3 * inv**2 * t * p1[0] + 3 * inv * t**2 * p2[0] + t**3 * p3[0]
        y = inv**3 * p0[1] + 3 * inv**2 * t * p1[1] + 3 * inv * t**2 * p2[1] + t**3 * p3[1]
        points.append((x, y))
    return points


def _quadratic_points(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    steps: int,
) -> list[tuple[float, float]]:
    points = []
    for index in range(steps + 1):
        t = index / steps
        inv = 1 - t
        x = inv**2 * p0[0] + 2 * inv * t * p1[0] + t**2 * p2[0]
        y = inv**2 * p0[1] + 2 * inv * t * p1[1] + t**2 * p2[1]
        points.append((x, y))
    return points


def _bounded_scale(mannequin, field: str, minimum: float, maximum: float) -> float:
    value = float(getattr(mannequin, field, 1.0) or 1.0)
    return max(minimum, min(maximum, value))


def _smooth_step(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3 - 2 * value)


def _lerp(start: float, end: float, progress: float) -> float:
    return start + (end - start) * progress


def _downsample_rgba(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    return image.resize(size, Image.Resampling.LANCZOS)


def _downsample_l(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    return image.resize(size, Image.Resampling.LANCZOS)


def _use_premium_gray_material() -> bool:
    return os.getenv("VTON_MOCK_BODY_STYLE", "premium_gray").strip().lower() in {
        "premium_gray",
        "matte_gray",
        "gray",
        "fiberglass",
    }


def _use_mesh_asset_mannequin() -> bool:
    return os.getenv("VTON_USE_MESH_ASSET_MANNEQUIN", "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "sim",
    }


def _body_material_rgb(tone: str) -> tuple[int, int, int]:
    if _use_premium_gray_material():
        return (196, 197, 193)
    return _skin_rgb(tone)


def _body_highlight_rgb() -> tuple[int, int, int]:
    if _use_premium_gray_material():
        return (244, 245, 241)
    return (255, 246, 235)


def _body_detail_rgb() -> tuple[int, int, int]:
    if _use_premium_gray_material():
        return (93, 94, 91)
    return (98, 63, 45)


def _body_rim_rgb() -> tuple[int, int, int]:
    if _use_premium_gray_material():
        return (218, 220, 216)
    return (120, 78, 205)


def _skin_rgb(tone: str) -> tuple[int, int, int]:
    if tone == "light":
        return (242, 199, 165)
    if tone == "medium":
        return (198, 134, 90)
    if tone == "dark":
        return (107, 63, 42)
    if tone == "deep":
        return (58, 36, 28)
    return (198, 134, 90)
