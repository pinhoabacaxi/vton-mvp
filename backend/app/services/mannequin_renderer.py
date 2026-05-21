from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageDraw

from app.models.mannequin import MannequinRenderInput, MannequinRenderResult
from app.services.image_processor import UPLOAD_DIR
from app.services.url_utils import absolute_url

MANNEQUIN_DIR = UPLOAD_DIR / "mannequin"
MANNEQUIN_DIR.mkdir(parents=True, exist_ok=True)


def render_front_mannequin(data: MannequinRenderInput) -> MannequinRenderResult:
    mannequin = data.mannequin
    filename = f"mannequin_front_{uuid4().hex}.png"
    output_path = MANNEQUIN_DIR / filename

    image = Image.new("RGBA", (900, 1200), "#170b25")
    draw = ImageDraw.Draw(image)

    _draw_background(draw)
    _draw_mannequin(draw, mannequin)

    draw.text((40, 40), "Mannequin frontal", fill="#e9d5ff")

    image.save(output_path, "PNG")

    return MannequinRenderResult(
        image_url=absolute_url(f"/uploads/mannequin/{filename}"),
        image_path=str(output_path),
        message="Render frontal do manequim gerado com sucesso.",
    )


def _draw_background(draw: ImageDraw.ImageDraw) -> None:
    draw.rectangle((0, 0, 900, 1200), fill="#170b25")
    draw.ellipse((-180, -120, 520, 520), fill="#311d5a")
    draw.ellipse((380, 720, 1080, 1260), fill="#2d1461")


def _draw_mannequin(draw: ImageDraw.ImageDraw, mannequin) -> None:
    skin = _skin_color(mannequin.skin_tone)
    center_x = 450
    head_y = 180

    shoulder_width = int(190 * getattr(mannequin, "shoulder_scale", 1))
    chest_width = int(170 * getattr(mannequin, "chest_scale", 1))
    waist_width = int(120 * getattr(mannequin, "waist_scale", 1))
    hip_width = int(190 * getattr(mannequin, "hip_scale", 1))
    arm_width = int(48 * getattr(mannequin, "arm_scale", 1))
    leg_width = int(72 * getattr(mannequin, "leg_scale", 1))

    draw.ellipse(
        (center_x - 70, head_y - 70, center_x + 70, head_y + 70),
        fill=skin,
    )

    draw.rectangle((center_x - 24, head_y + 70, center_x + 24, head_y + 110), fill=skin)

    draw.polygon(
        [
            (center_x - shoulder_width, 310),
            (center_x + shoulder_width, 310),
            (center_x + chest_width, 520),
            (center_x + waist_width, 680),
            (center_x - waist_width, 680),
            (center_x - chest_width, 520),
        ],
        fill=skin,
    )

    draw.polygon(
        [
            (center_x - waist_width, 680),
            (center_x + waist_width, 680),
            (center_x + hip_width, 860),
            (center_x + leg_width, 1120),
            (center_x + 18, 1120),
            (center_x + 18, 860),
            (center_x - 18, 860),
            (center_x - 18, 1120),
            (center_x - leg_width, 1120),
        ],
        fill=skin,
    )

    draw.rounded_rectangle(
        (center_x - shoulder_width - 20, 320, center_x - shoulder_width + 20, 760),
        radius=24,
        fill=skin,
    )
    draw.rounded_rectangle(
        (center_x + shoulder_width - 20, 320, center_x + shoulder_width + 20, 760),
        radius=24,
        fill=skin,
    )

    draw.rounded_rectangle(
        (center_x - 58, 860, center_x - 18, 1120),
        radius=24,
        fill=skin,
    )
    draw.rounded_rectangle(
        (center_x + 18, 860, center_x + 58, 1120),
        radius=24,
        fill=skin,
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
