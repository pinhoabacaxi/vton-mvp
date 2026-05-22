import os
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

from app.services.mannequin_renderer import CANVAS_SIZE, render_tryon_person_scene
from app.utils.image_normalizer import fit_on_studio_canvas


def render_humanized_tryon_person(
    mannequin,
    size: tuple[int, int] = CANVAS_SIZE,
) -> Image.Image:
    """Create a provider-facing person image with human visual cues.

    If VTON_HUMAN_TEMPLATE_PATH points to a real studio photo, that image is used as
    a lightweight template. Otherwise the existing parametric person is enriched
    with skin, face, hands, hair and studio-photo texture cues so pose detectors see
    a less abstract input than the decorative mock mannequin.
    """

    template = _load_template_from_env(size)
    if template is not None:
        return template.convert("RGBA")

    image = render_tryon_person_scene(mannequin, size=size).convert("RGBA")
    _draw_human_identity_cues(image, mannequin)
    image = _add_photo_like_texture(image)
    return image


def _load_template_from_env(size: tuple[int, int]) -> Image.Image | None:
    template_path = os.getenv("VTON_HUMAN_TEMPLATE_PATH", "").strip()
    if not template_path:
        return None

    path = Path(template_path)
    if not path.exists() or not path.is_file():
        return None

    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image)
        return fit_on_studio_canvas(
            image,
            target_size=size,
            kind="person",
            background_rgb=(248, 248, 246),
        )


def _draw_human_identity_cues(image: Image.Image, mannequin) -> None:
    width, height = image.size
    draw = ImageDraw.Draw(image, "RGBA")
    skin = _skin_rgb(getattr(mannequin, "skin_tone", "medium"))
    shadow = tuple(max(0, channel - 42) for channel in skin)
    blush = tuple(min(255, channel + 38) for channel in skin)

    cx = width // 2
    head_w = int(width * 0.145)
    head_h = int(height * 0.142)
    head_top = int(height * 0.083)
    head_box = (
        cx - head_w // 2,
        head_top,
        cx + head_w // 2,
        head_top + head_h,
    )

    hair_color = _hair_rgb(getattr(mannequin, "skin_tone", "medium"))
    draw.ellipse(
        (
            head_box[0] - int(width * 0.010),
            head_box[1] - int(height * 0.010),
            head_box[2] + int(width * 0.010),
            head_box[1] + int(head_h * 0.62),
        ),
        fill=(*hair_color, 230),
    )
    draw.ellipse(head_box, fill=(*skin, 255))
    draw.ellipse(
        (
            head_box[0] + int(head_w * 0.12),
            head_box[1] + int(head_h * 0.42),
            head_box[2] - int(head_w * 0.12),
            head_box[3] + int(head_h * 0.08),
        ),
        fill=(*skin, 245),
    )

    face_shadow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    face_mask = Image.new("L", image.size, 0)
    mask_draw = ImageDraw.Draw(face_mask)
    mask_draw.ellipse(head_box, fill=95)
    face_shadow.putalpha(face_mask.filter(ImageFilter.GaussianBlur(radius=max(5, width // 90))))
    face_shadow = Image.new("RGBA", image.size, (*shadow, 0))
    face_shadow.putalpha(face_mask.filter(ImageFilter.GaussianBlur(radius=max(6, width // 80))))
    image.alpha_composite(face_shadow)

    draw = ImageDraw.Draw(image, "RGBA")
    eye_y = head_top + int(head_h * 0.47)
    eye_dx = int(head_w * 0.20)
    eye_r = max(2, int(width * 0.006))
    for sign in (-1, 1):
        ex = cx + sign * eye_dx
        draw.ellipse((ex - eye_r, eye_y - eye_r, ex + eye_r, eye_y + eye_r), fill=(45, 32, 24, 210))

    nose_y = head_top + int(head_h * 0.58)
    draw.line((cx, eye_y + eye_r, cx - eye_r, nose_y), fill=(*shadow, 110), width=max(1, width // 280))
    mouth_y = head_top + int(head_h * 0.72)
    draw.arc(
        (
            cx - int(head_w * 0.15),
            mouth_y - int(head_h * 0.04),
            cx + int(head_w * 0.15),
            mouth_y + int(head_h * 0.07),
        ),
        start=10,
        end=170,
        fill=(120, 65, 58, 150),
        width=max(1, width // 260),
    )

    _draw_hands(draw, width, height, skin, shadow, blush)
    _draw_subtle_anatomy(draw, width, height, skin, shadow)


def _draw_hands(
    draw: ImageDraw.ImageDraw,
    width: int,
    height: int,
    skin: tuple[int, int, int],
    shadow: tuple[int, int, int],
    blush: tuple[int, int, int],
) -> None:
    hand_y = int(height * 0.660)
    hand_w = int(width * 0.042)
    hand_h = int(height * 0.046)
    for sign in (-1, 1):
        cx = width // 2 + sign * int(width * 0.165)
        box = (cx - hand_w // 2, hand_y, cx + hand_w // 2, hand_y + hand_h)
        draw.ellipse(box, fill=(*skin, 255), outline=(*shadow, 80), width=max(1, width // 360))
        for idx in range(4):
            fx = cx - sign * int(hand_w * 0.32) + sign * int(idx * hand_w * 0.18)
            draw.line(
                (fx, hand_y + int(hand_h * 0.45), fx + sign * int(hand_w * 0.10), hand_y + int(hand_h * 0.92)),
                fill=(*blush, 92),
                width=max(1, width // 340),
            )


def _draw_subtle_anatomy(
    draw: ImageDraw.ImageDraw,
    width: int,
    height: int,
    skin: tuple[int, int, int],
    shadow: tuple[int, int, int],
) -> None:
    cx = width // 2
    draw.arc(
        (
            cx - int(width * 0.20),
            int(height * 0.260),
            cx + int(width * 0.20),
            int(height * 0.405),
        ),
        start=200,
        end=340,
        fill=(*shadow, 42),
        width=max(2, width // 180),
    )
    draw.line(
        (
            cx,
            int(height * 0.382),
            cx,
            int(height * 0.595),
        ),
        fill=(*shadow, 30),
        width=max(1, width // 240),
    )
    draw.ellipse(
        (
            cx - int(width * 0.065),
            int(height * 0.515),
            cx + int(width * 0.065),
            int(height * 0.555),
        ),
        outline=(*skin, 54),
        width=max(1, width // 260),
    )


def _add_photo_like_texture(image: Image.Image) -> Image.Image:
    rgb = image.convert("RGB")
    noise = Image.effect_noise(image.size, 9.5).convert("L")
    factor = noise.point(lambda value: max(244, min(255, 250 + int((value - 128) * 0.035))))
    textured = ImageChops.multiply(rgb, Image.merge("RGB", (factor, factor, factor)))

    warm = Image.new("RGB", image.size, (8, 4, 2))
    warm_alpha = Image.new("L", image.size, 8)
    textured = Image.composite(ImageChops.add(textured, warm, scale=1.0, offset=0), textured, warm_alpha)
    return Image.merge("RGBA", (*textured.split(), image.getchannel("A")))


def _skin_rgb(tone: str) -> tuple[int, int, int]:
    if tone == "light":
        return (242, 199, 165)
    if tone == "dark":
        return (117, 70, 48)
    if tone == "deep":
        return (79, 49, 38)
    return (202, 143, 98)


def _hair_rgb(tone: str) -> tuple[int, int, int]:
    if tone in {"dark", "deep"}:
        return (34, 24, 22)
    if tone == "light":
        return (82, 58, 42)
    return (48, 34, 28)
