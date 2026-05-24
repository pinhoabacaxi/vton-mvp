# -*- coding: utf-8 -*-
"""Generate lightweight mannequin PNG assets from a human mesh or render.

The backend should not depend on Blender or FBX importers at runtime. This
script is an offline bridge: it reads a body OBJ/STL or a Blender-rendered PNG,
applies simple anthropometric width morphs for the existing body model IDs, and
writes transparent PNGs that the FastAPI renderer can serve quickly.
"""

from __future__ import annotations

import argparse
import json
import math
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageChops, ImageDraw, ImageFilter


BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = Path.home() / "Downloads" / "Female_Body_Base_Model.obj"
DEFAULT_OUTPUT = BACKEND_ROOT / "app" / "assets" / "body_mesh"
PREVIEW_SIZE = (360, 480)
MOCK_SIZE = (900, 1200)
SOURCE_RENDER_SIZE = (540, 720)


@dataclass(frozen=True)
class Mesh:
    vertices: list[tuple[float, float, float]]
    faces: list[tuple[int, int, int]]


@dataclass(frozen=True)
class BodyVariant:
    model_id: str
    shoulder_scale: float
    chest_scale: float
    waist_scale: float
    hip_scale: float
    thigh_scale: float
    arm_scale: float


BODY_VARIANTS = [
    BodyVariant("balanced_soft", 1.04, 1.06, 1.00, 1.08, 1.06, 1.03),
    BodyVariant("wide_shoulder", 1.28, 1.12, 0.92, 1.02, 1.04, 1.12),
    BodyVariant("wide_hip", 0.98, 1.05, 0.96, 1.38, 1.30, 1.02),
    BodyVariant("straight_frame", 1.10, 1.08, 1.24, 1.14, 1.10, 1.06),
    BodyVariant("athletic_compact", 1.20, 1.12, 0.90, 1.04, 1.14, 1.16),
    BodyVariant("full_soft", 1.20, 1.34, 1.38, 1.40, 1.32, 1.22),
]


def parse_obj(path: Path) -> Mesh:
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int]] = []

    with path.open("r", encoding="utf-8", errors="ignore") as file:
        for raw_line in file:
            line = raw_line.strip()
            if line.startswith("v "):
                _, x, y, z, *_ = line.split()
                vertices.append((float(x), float(y), float(z)))
            elif line.startswith("f "):
                indices = [_parse_face_index(token) for token in line.split()[1:]]
                if len(indices) < 3:
                    continue
                first = indices[0]
                for index in range(1, len(indices) - 1):
                    faces.append((first, indices[index], indices[index + 1]))

    if not vertices or not faces:
        raise ValueError(f"OBJ mesh is empty or unsupported: {path}")

    return Mesh(vertices=vertices, faces=faces)


def parse_stl(path: Path) -> Mesh:
    data = path.read_bytes()
    if len(data) < 84:
        raise ValueError(f"STL file is too small: {path}")

    triangle_count = struct.unpack("<I", data[80:84])[0]
    expected_size = 84 + triangle_count * 50
    if expected_size > len(data):
        raise ValueError(f"Only binary STL is supported for this asset pipeline: {path}")

    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int]] = []
    offset = 84

    for _ in range(triangle_count):
        values = struct.unpack("<12fH", data[offset : offset + 50])
        first_index = len(vertices)
        vertices.extend(
            [
                (values[3], values[4], values[5]),
                (values[6], values[7], values[8]),
                (values[9], values[10], values[11]),
            ]
        )
        faces.append((first_index, first_index + 1, first_index + 2))
        offset += 50

    return Mesh(vertices=vertices, faces=faces)


def parse_mesh(path: Path) -> Mesh:
    suffix = path.suffix.lower()
    if suffix == ".obj":
        return parse_obj(path)
    if suffix == ".stl":
        return parse_stl(path)
    raise ValueError(f"Unsupported mesh format for preview generation: {path.suffix}")


def _parse_face_index(token: str) -> int:
    return int(token.split("/", 1)[0]) - 1


def render_variant(mesh: Mesh, variant: BodyVariant, size: tuple[int, int]) -> Image.Image:
    layout = _axis_layout(mesh.vertices)
    source_bounds = _axis_bounds(mesh.vertices, layout)
    morphed = [_morph_vertex(vertex, source_bounds, layout, variant) for vertex in mesh.vertices]
    bounds = _axis_bounds(morphed, layout)
    projected = _project_vertices(morphed, bounds, layout, size)
    sorted_faces = sorted(
        mesh.faces,
        key=lambda face: _face_depth(morphed, face, layout[2]),
        reverse=True,
    )

    scale = 2 if size[0] <= 400 else 1
    high_size = (size[0] * scale, size[1] * scale)
    image = Image.new("RGBA", high_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image, "RGBA")

    for face in sorted_faces:
        if not _face_inside_robust_bounds(morphed, face, bounds, layout):
            continue
        points = [(projected[index][0] * scale, projected[index][1] * scale) for index in face]
        area = _triangle_area(points)
        if area < 0.5 or area > high_size[0] * high_size[1] * 0.045:
            continue
        if _looks_like_export_outlier_plane(points, high_size):
            continue
        normal = _face_normal(morphed, face)
        shade = _shade_from_normal(normal, layout)
        color = (
            int(184 + shade * 54),
            int(186 + shade * 54),
            int(183 + shade * 52),
            255,
        )
        draw.polygon(points, fill=color)

    alpha = image.getchannel("A").filter(ImageFilter.GaussianBlur(radius=0.5 * scale))
    image.putalpha(alpha)
    image = _add_mesh_material_pass(image)
    return image.resize(size, Image.Resampling.LANCZOS)


def _morph_vertex(
    vertex: tuple[float, float, float],
    source_bounds: tuple[float, float, float, float],
    layout: tuple[int, int, int],
    variant: BodyVariant,
) -> tuple[float, float, float]:
    horizontal_axis, vertical_axis, _ = layout
    min_h, max_h, min_v, max_v = source_bounds
    center_h = (min_h + max_h) / 2
    height = max(0.001, max_v - min_v)
    t = (vertex[vertical_axis] - min_v) / height

    width_scale = 1.0
    width_scale += (variant.shoulder_scale - 1.0) * _region_weight(t, 0.73, 0.090)
    width_scale += (variant.chest_scale - 1.0) * _region_weight(t, 0.60, 0.120)
    width_scale += (variant.waist_scale - 1.0) * _region_weight(t, 0.485, 0.090)
    width_scale += (variant.hip_scale - 1.0) * _region_weight(t, 0.385, 0.100)
    width_scale += (variant.thigh_scale - 1.0) * _region_weight(t, 0.245, 0.115)
    width_scale += (variant.arm_scale - 1.0) * _region_weight(t, 0.525, 0.270) * 0.38
    width_scale = max(0.78, min(1.24, width_scale))

    coords = list(vertex)
    coords[horizontal_axis] = center_h + (vertex[horizontal_axis] - center_h) * width_scale
    return (coords[0], coords[1], coords[2])


def _region_weight(position: float, center: float, radius: float) -> float:
    distance = abs(position - center) / max(radius, 0.001)
    if distance >= 1.0:
        return 0.0
    return (1.0 - distance * distance) ** 2


def _axis_layout(vertices: Iterable[tuple[float, float, float]]) -> tuple[int, int, int]:
    materialized = list(vertices)
    ranges = []
    for axis in range(3):
        low, high = _trimmed_range([point[axis] for point in materialized])
        ranges.append((high - low, axis))
    ordered = [axis for _, axis in sorted(ranges, reverse=True)]
    vertical_axis = ordered[0]
    horizontal_axis = ordered[1]
    depth_axis = ordered[2]
    return horizontal_axis, vertical_axis, depth_axis


def _axis_bounds(
    vertices: Iterable[tuple[float, float, float]],
    layout: tuple[int, int, int],
) -> tuple[float, float, float, float]:
    materialized = list(vertices)
    horizontal_axis, vertical_axis, _ = layout
    min_h, max_h = _trimmed_range([point[horizontal_axis] for point in materialized])
    min_v, max_v = _trimmed_range([point[vertical_axis] for point in materialized])
    return min_h, max_h, min_v, max_v


def _trimmed_range(values: list[float], trim_ratio: float = 0.01) -> tuple[float, float]:
    ordered = sorted(values)
    if not ordered:
        return 0.0, 1.0
    low_index = int((len(ordered) - 1) * trim_ratio)
    high_index = int((len(ordered) - 1) * (1.0 - trim_ratio))
    return ordered[low_index], ordered[high_index]


def _face_inside_robust_bounds(
    vertices: list[tuple[float, float, float]],
    face: tuple[int, int, int],
    bounds: tuple[float, float, float, float],
    layout: tuple[int, int, int],
) -> bool:
    horizontal_axis, vertical_axis, _ = layout
    min_h, max_h, min_v, max_v = bounds
    margin_h = (max_h - min_h) * 0.18
    margin_v = (max_v - min_v) * 0.08
    for index in face:
        vertex = vertices[index]
        if vertex[horizontal_axis] < min_h - margin_h or vertex[horizontal_axis] > max_h + margin_h:
            return False
        if vertex[vertical_axis] < min_v - margin_v or vertex[vertical_axis] > max_v + margin_v:
            return False
    return True


def _project_vertices(
    vertices: list[tuple[float, float, float]],
    bounds: tuple[float, float, float, float],
    layout: tuple[int, int, int],
    size: tuple[int, int],
) -> list[tuple[float, float]]:
    width, height = size
    horizontal_axis, vertical_axis, _ = layout
    min_h, max_h, min_v, max_v = bounds
    mesh_w = max(0.001, max_h - min_h)
    mesh_h = max(0.001, max_v - min_v)
    scale = min(width * 0.74 / mesh_w, height * 0.90 / mesh_h)
    offset_x = width * 0.5 - ((min_h + max_h) * 0.5 * scale)
    offset_y = height * 0.948 + min_v * scale

    return [
        (
            vertex[horizontal_axis] * scale + offset_x,
            offset_y - vertex[vertical_axis] * scale,
        )
        for vertex in vertices
    ]


def _face_depth(
    vertices: list[tuple[float, float, float]],
    face: tuple[int, int, int],
    depth_axis: int,
) -> float:
    return sum(vertices[index][depth_axis] for index in face) / 3


def _face_normal(
    vertices: list[tuple[float, float, float]],
    face: tuple[int, int, int],
) -> tuple[float, float, float]:
    a, b, c = (vertices[index] for index in face)
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    nx = uy * vz - uz * vy
    ny = uz * vx - ux * vz
    nz = ux * vy - uy * vx
    length = max(0.001, math.sqrt(nx * nx + ny * ny + nz * nz))
    return (nx / length, ny / length, nz / length)


def _shade_from_normal(
    normal: tuple[float, float, float],
    layout: tuple[int, int, int],
) -> float:
    horizontal_axis, vertical_axis, depth_axis = layout
    camera_normal = (
        normal[horizontal_axis],
        normal[vertical_axis],
        abs(normal[depth_axis]),
    )
    light = (-0.32, 0.42, 0.84)
    light_len = math.sqrt(sum(value * value for value in light))
    lx, ly, lz = (value / light_len for value in light)
    dot = max(0.0, camera_normal[0] * lx + camera_normal[1] * ly + camera_normal[2] * lz)
    rim = min(1.0, abs(camera_normal[0]) * 0.30 + max(0.0, camera_normal[1]) * 0.20)
    return max(0.0, min(1.0, dot * 0.86 + rim * 0.18))


def _triangle_area(points: list[tuple[float, float]]) -> float:
    (ax, ay), (bx, by), (cx, cy) = points
    return abs((ax * (by - cy) + bx * (cy - ay) + cx * (ay - by)) * 0.5)


def _looks_like_export_outlier_plane(
    points: list[tuple[float, float]],
    size: tuple[int, int],
) -> bool:
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    bbox_width = max(xs) - min(xs)
    bbox_height = max(ys) - min(ys)
    return bbox_width > size[0] * 0.68 and bbox_height < size[1] * 0.24


def _add_mesh_material_pass(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    width, height = rgba.size
    alpha = rgba.getchannel("A")
    bbox = alpha.getbbox()
    if not bbox:
        return rgba

    material = Image.new("RGBA", rgba.size, (0, 0, 0, 0))
    material.alpha_composite(rgba)

    eroded = alpha.filter(ImageFilter.MinFilter(25)).filter(ImageFilter.GaussianBlur(9))
    edge = ImageChops.subtract(alpha, eroded).filter(ImageFilter.GaussianBlur(7))
    edge_shadow = Image.new("RGBA", rgba.size, (38, 34, 42, 0))
    edge_shadow.putalpha(edge.point(lambda value: int(value * 0.38)))
    material = Image.alpha_composite(material, edge_shadow)

    highlight = Image.new("RGBA", rgba.size, (0, 0, 0, 0))
    hd = ImageDraw.Draw(highlight, "RGBA")
    left, top, right, bottom = bbox
    body_w = right - left
    body_h = bottom - top
    cx = (left + right) // 2

    hd.ellipse((cx - body_w * 0.20, top + body_h * 0.17, cx + body_w * 0.20, top + body_h * 0.50), fill=(255, 255, 255, 34))
    hd.ellipse((cx - body_w * 0.13, top + body_h * 0.48, cx + body_w * 0.13, top + body_h * 0.72), fill=(255, 255, 255, 22))
    hd.ellipse((cx - body_w * 0.25, top + body_h * 0.63, cx - body_w * 0.06, top + body_h * 0.96), fill=(255, 255, 255, 24))
    hd.ellipse((cx + body_w * 0.06, top + body_h * 0.63, cx + body_w * 0.25, top + body_h * 0.96), fill=(255, 255, 255, 24))
    hd.ellipse((left + body_w * 0.05, top + body_h * 0.26, left + body_w * 0.22, top + body_h * 0.70), fill=(255, 255, 255, 16))
    hd.ellipse((right - body_w * 0.22, top + body_h * 0.26, right - body_w * 0.05, top + body_h * 0.70), fill=(255, 255, 255, 16))
    highlight.putalpha(ImageChops.multiply(highlight.getchannel("A"), alpha).filter(ImageFilter.GaussianBlur(8)))
    material = Image.alpha_composite(material, highlight)

    ao = Image.new("RGBA", rgba.size, (0, 0, 0, 0))
    ad = ImageDraw.Draw(ao, "RGBA")
    ad.ellipse((cx - body_w * 0.25, top + body_h * 0.235, cx + body_w * 0.25, top + body_h * 0.330), fill=(25, 22, 30, 42))
    ad.ellipse((cx - body_w * 0.33, top + body_h * 0.345, cx - body_w * 0.13, top + body_h * 0.460), fill=(18, 14, 22, 36))
    ad.ellipse((cx + body_w * 0.13, top + body_h * 0.345, cx + body_w * 0.33, top + body_h * 0.460), fill=(18, 14, 22, 36))
    ad.ellipse((cx - body_w * 0.20, top + body_h * 0.610, cx + body_w * 0.20, top + body_h * 0.730), fill=(18, 14, 22, 42))
    ao = ao.filter(ImageFilter.GaussianBlur(16))
    ao.putalpha(ImageChops.multiply(ao.getchannel("A"), alpha))
    material = Image.alpha_composite(material, ao)

    noise = Image.effect_noise(rgba.size, 7).convert("L").point(lambda value: int(max(0, min(20, (value - 128) * 0.10 + 8))))
    grain = Image.new("RGBA", rgba.size, (255, 255, 255, 0))
    grain.putalpha(ImageChops.multiply(noise, alpha).point(lambda value: int(value * 0.42)))
    material = Image.alpha_composite(material, grain)

    material.putalpha(alpha.filter(ImageFilter.GaussianBlur(0.35)))
    return material


def render_image_variant(source_image: Image.Image, variant: BodyVariant, size: tuple[int, int]) -> Image.Image:
    image = _fit_image_source(source_image, SOURCE_RENDER_SIZE)
    morphed = Image.new("RGBA", SOURCE_RENDER_SIZE, (0, 0, 0, 0))
    width, height = SOURCE_RENDER_SIZE
    band_height = 3

    for top in range(0, height, band_height):
        bottom = min(height, top + band_height)
        band = image.crop((0, top, width, bottom))
        y_ratio = (top + bottom) * 0.5 / max(1, height)
        scale = _image_band_scale(y_ratio, variant)
        resized_width = max(1, int(width * scale))
        resized = band.resize((resized_width, bottom - top), Image.Resampling.LANCZOS)

        if resized_width > width:
            crop_left = (resized_width - width) // 2
            resized = resized.crop((crop_left, 0, crop_left + width, bottom - top))
            morphed.alpha_composite(resized, (0, top))
        else:
            morphed.alpha_composite(resized, ((width - resized_width) // 2, top))

    alpha = morphed.getchannel("A").filter(ImageFilter.GaussianBlur(radius=0.25))
    morphed.putalpha(alpha)
    return morphed.resize(size, Image.Resampling.LANCZOS)


def _fit_image_source(source: Image.Image, size: tuple[int, int]) -> Image.Image:
    rgba = source.convert("RGBA")
    bbox = rgba.getchannel("A").getbbox()
    if bbox:
        rgba = rgba.crop(bbox)
    rgba = _normalize_rendered_material(rgba)

    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    scale = min(size[0] * 0.70 / max(1, rgba.width), size[1] * 0.92 / max(1, rgba.height))
    resized = rgba.resize((max(1, int(rgba.width * scale)), max(1, int(rgba.height * scale))), Image.Resampling.LANCZOS)
    left = (size[0] - resized.width) // 2
    top = int(size[1] * 0.955) - resized.height
    canvas.alpha_composite(resized, (left, max(0, top)))
    return canvas


def _normalize_rendered_material(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    bbox = alpha.getbbox()
    if not bbox:
        return rgba

    luma = rgba.convert("L")
    body_luma = luma.crop(bbox)
    lo, hi = body_luma.getextrema()
    if hi - lo < 12:
        lo, hi = 35, 220

    def normalize(value: int) -> int:
        scaled = int(150 + ((value - lo) / max(1, hi - lo)) * 82)
        return max(118, min(238, scaled))

    tone = luma.point(normalize)
    red = tone.point(lambda value: min(244, value + 8))
    green = tone.point(lambda value: min(238, value + 6))
    blue = tone.point(lambda value: max(130, value - 2))
    material = Image.merge("RGBA", (red, green, blue, alpha))
    return _add_mesh_material_pass(material)


def _image_band_scale(y_ratio: float, variant: BodyVariant) -> float:
    scale = 1.0
    scale += (variant.shoulder_scale - 1.0) * _band_weight(y_ratio, 0.300, 0.060) * 0.95
    scale += (variant.chest_scale - 1.0) * _band_weight(y_ratio, 0.395, 0.090) * 1.02
    scale += (variant.waist_scale - 1.0) * _band_weight(y_ratio, 0.505, 0.075) * 1.05
    scale += (variant.hip_scale - 1.0) * _band_weight(y_ratio, 0.600, 0.095) * 1.06
    scale += (variant.thigh_scale - 1.0) * _band_weight(y_ratio, 0.735, 0.135) * 0.88
    scale += (variant.arm_scale - 1.0) * _band_weight(y_ratio, 0.450, 0.220) * 0.22
    return max(0.68, min(1.55, scale))


def _band_weight(position: float, center: float, radius: float) -> float:
    distance = abs(position - center) / max(radius, 0.001)
    if distance >= 1.0:
        return 0.0
    return (1.0 - distance * distance) ** 2


def write_assets(source: Path, output_dir: Path, family: str = "female") -> None:
    mesh = parse_mesh(source)
    family_dir = output_dir / "families" / family
    preview_dir = family_dir / "previews"
    mock_dir = family_dir / "mock"
    preview_dir.mkdir(parents=True, exist_ok=True)
    mock_dir.mkdir(parents=True, exist_ok=True)

    for variant in BODY_VARIANTS:
        rendered_source = render_variant(mesh, variant, SOURCE_RENDER_SIZE)
        preview = rendered_source.resize(PREVIEW_SIZE, Image.Resampling.LANCZOS)
        mock = rendered_source.resize(MOCK_SIZE, Image.Resampling.LANCZOS)
        preview.save(preview_dir / f"{variant.model_id}.png", "PNG", optimize=True)
        mock.save(mock_dir / f"{variant.model_id}.png", "PNG", optimize=True)

    contact_sheet = Image.new("RGBA", (PREVIEW_SIZE[0] * 3, PREVIEW_SIZE[1] * 2), (23, 11, 37, 255))
    for index, variant in enumerate(BODY_VARIANTS):
        preview = Image.open(preview_dir / f"{variant.model_id}.png").convert("RGBA")
        x = (index % 3) * PREVIEW_SIZE[0]
        y = (index // 3) * PREVIEW_SIZE[1]
        contact_sheet.alpha_composite(preview, (x, y))
    contact_sheet.save(preview_dir / "contact_sheet.png", "PNG", optimize=True)

    if family in {"neutral", "female"}:
        _mirror_default_family(output_dir, preview_dir, mock_dir)

    manifest = {
        "source": source.name,
        "family": family,
        "format": f"transparent_png_from_{source.suffix.lower().lstrip('.')}",
        "preview_size": PREVIEW_SIZE,
        "mock_size": MOCK_SIZE,
        "variants": [variant.model_id for variant in BODY_VARIANTS],
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def write_image_assets(source: Path, output_dir: Path, family: str) -> None:
    source_image = Image.open(source).convert("RGBA")
    family_dir = output_dir / "families" / family
    preview_dir = family_dir / "previews"
    mock_dir = family_dir / "mock"
    preview_dir.mkdir(parents=True, exist_ok=True)
    mock_dir.mkdir(parents=True, exist_ok=True)

    for variant in BODY_VARIANTS:
        rendered = render_image_variant(source_image, variant, SOURCE_RENDER_SIZE)
        preview = rendered.resize(PREVIEW_SIZE, Image.Resampling.LANCZOS)
        mock = rendered.resize(MOCK_SIZE, Image.Resampling.LANCZOS)
        preview.save(preview_dir / f"{variant.model_id}.png", "PNG", optimize=True)
        mock.save(mock_dir / f"{variant.model_id}.png", "PNG", optimize=True)

    contact_sheet = Image.new("RGBA", (PREVIEW_SIZE[0] * 3, PREVIEW_SIZE[1] * 2), (23, 11, 37, 255))
    for index, variant in enumerate(BODY_VARIANTS):
        preview = Image.open(preview_dir / f"{variant.model_id}.png").convert("RGBA")
        x = (index % 3) * PREVIEW_SIZE[0]
        y = (index // 3) * PREVIEW_SIZE[1]
        contact_sheet.alpha_composite(preview, (x, y))
    contact_sheet.save(preview_dir / "contact_sheet.png", "PNG", optimize=True)

    if family in {"neutral", "female"}:
        _mirror_default_family(output_dir, preview_dir, mock_dir)

    manifest = {
        "source": source.name,
        "family": family,
        "format": "transparent_png_from_blender_render",
        "preview_size": PREVIEW_SIZE,
        "mock_size": MOCK_SIZE,
        "variants": [variant.model_id for variant in BODY_VARIANTS],
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def _mirror_default_family(output_dir: Path, preview_dir: Path, mock_dir: Path) -> None:
    default_preview_dir = output_dir / "previews"
    default_mock_dir = output_dir / "mock"
    default_preview_dir.mkdir(parents=True, exist_ok=True)
    default_mock_dir.mkdir(parents=True, exist_ok=True)

    for path in preview_dir.glob("*.png"):
        Image.open(path).save(default_preview_dir / path.name, "PNG", optimize=True)
    for path in mock_dir.glob("*.png"):
        Image.open(path).save(default_mock_dir / path.name, "PNG", optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--family", default="neutral")
    args = parser.parse_args()

    if args.source.suffix.lower() in {".png", ".webp", ".jpg", ".jpeg"}:
        write_image_assets(args.source, args.output, args.family)
    else:
        write_assets(args.source, args.output, args.family)
    print(args.output)


if __name__ == "__main__":
    main()
