"""Render neutral GLB mannequins into transparent PNG sources.

Run with Blender:
blender --background --python scripts/blender_render_mannequin_sources.py -- \
  --female C:/path/female.glb --male C:/path/male.glb --output app/assets/body_mesh

The generated PNGs are then morphed by generate_body_mesh_assets.py. Blender is
an offline authoring dependency only; FastAPI and Render do not import it.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def import_glb(path: Path) -> list[bpy.types.Object]:
    bpy.ops.import_scene.gltf(filepath=str(path))
    objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if not objects:
        raise RuntimeError(f"No mesh objects found in {path}")
    return objects


def normalize_objects(objects: list[bpy.types.Object]) -> None:
    for obj in objects:
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        obj.select_set(False)

        material = bpy.data.materials.new(f"{obj.name}_matte_gray")
        material.use_nodes = True
        bsdf = material.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (0.78, 0.79, 0.76, 1.0)
            bsdf.inputs["Roughness"].default_value = 0.86
            bsdf.inputs["Metallic"].default_value = 0.0
        obj.data.materials.clear()
        obj.data.materials.append(material)


def scene_bounds(objects: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    corners = []
    for obj in objects:
        corners.extend(obj.matrix_world @ Vector(corner) for corner in obj.bound_box)
    min_corner = Vector((min(point.x for point in corners), min(point.y for point in corners), min(point.z for point in corners)))
    max_corner = Vector((max(point.x for point in corners), max(point.y for point in corners), max(point.z for point in corners)))
    return min_corner, max_corner


def setup_camera_and_lights(objects: list[bpy.types.Object], view_axis: str) -> None:
    min_corner, max_corner = scene_bounds(objects)
    center = (min_corner + max_corner) * 0.5
    extent = max_corner - min_corner
    height = max(extent.x, extent.y, extent.z)

    camera_distance = height * 2.6
    if view_axis == "positive_y":
        location = (center.x, center.y + camera_distance, center.z)
        rotation = (math.radians(90), 0, math.radians(180))
    else:
        location = (center.x, center.y - camera_distance, center.z)
        rotation = (math.radians(90), 0, 0)

    camera = bpy.data.objects.new("camera", bpy.data.cameras.new("camera"))
    bpy.context.collection.objects.link(camera)
    camera.location = location
    camera.rotation_euler = rotation
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = height * 1.05
    bpy.context.scene.camera = camera

    key = bpy.data.objects.new("key_light", bpy.data.lights.new("key_light", "AREA"))
    bpy.context.collection.objects.link(key)
    key.location = (center.x - height * 0.7, center.y - height * 1.1, center.z + height * 1.0)
    key.data.energy = 420
    key.data.size = height * 0.72

    fill = bpy.data.objects.new("fill_light", bpy.data.lights.new("fill_light", "AREA"))
    bpy.context.collection.objects.link(fill)
    fill.location = (center.x + height * 0.7, center.y + height * 0.7, center.z + height * 0.45)
    fill.data.energy = 95
    fill.data.size = height * 1.1


def render_png(output_path: Path) -> None:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    if hasattr(scene, "eevee"):
        scene.eevee.taa_render_samples = 48
    scene.render.resolution_x = 900
    scene.render.resolution_y = 1200
    scene.render.film_transparent = True
    scene.view_settings.view_transform = "Filmic"
    scene.view_settings.look = "Medium High Contrast"
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(output_path)
    bpy.ops.render.render(write_still=True)


def render_source(label: str, glb_path: Path, output_dir: Path, view_axis: str) -> None:
    clear_scene()
    objects = import_glb(glb_path)
    normalize_objects(objects)
    setup_camera_and_lights(objects, view_axis)
    output_dir.mkdir(parents=True, exist_ok=True)
    render_png(output_dir / f"{label}_base.png")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--female", type=Path, required=True)
    parser.add_argument("--male", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--view-axis", default="negative_y", choices=["negative_y", "positive_y"])
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    args = parser.parse_args(argv)

    render_source("female", args.female, args.output / "source_renders", args.view_axis)
    render_source("male", args.male, args.output / "source_renders", args.view_axis)


if __name__ == "__main__":
    main()
