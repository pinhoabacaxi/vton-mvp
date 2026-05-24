# -*- coding: utf-8 -*-
"""Human template selection for neural VTON providers.

The local fit diagram can use procedural mannequin assets, but neural VTON
providers need a realistic studio-like person image. This module maps the
inclusive body model ids used by the app to future human template assets without
requiring the user to declare gender.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Literal, Optional

from app.models.vton import VtonPayload


DEFAULT_TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "assets" / "human_templates"
SUPPORTED_TEMPLATE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")
BodyMeasurementBand = Literal["petite", "regular", "full"]

TEMPLATE_ALIASES: dict[str, tuple[str, ...]] = {
    "balanced_soft": ("balanced_soft", "balanced", "default"),
    "wide_shoulder": ("wide_shoulder", "broad_shoulder", "upper_balance"),
    "wide_hip": ("wide_hip", "curvy_hip", "pear"),
    "straight_frame": ("straight_frame", "straight", "linear"),
    "athletic_compact": ("athletic_compact", "athletic", "compact"),
    "full_soft": ("full_soft", "plus", "full", "soft_plus"),
}

MEASUREMENT_BANDS: dict[BodyMeasurementBand, tuple[str, ...]] = {
    "petite": ("petite", "compact"),
    "regular": ("regular", "standard"),
    "full": ("full", "plus", "curve"),
}


def get_human_template_dir() -> Path:
    """Return the configured template directory.

    The default path lives inside backend/app/assets/human_templates so future
    real studio templates can be added without changing provider code.
    """

    return Path(os.getenv("VTON_HUMAN_TEMPLATE_DIR", str(DEFAULT_TEMPLATE_DIR))).expanduser()


def select_human_template_path(payload: VtonPayload) -> Optional[Path]:
    """Select a realistic person template for a VTON payload.

    Search order:
    1. Explicit VTON_HUMAN_TEMPLATE_PATH override.
    2. Inclusive body-model aliases in neutral folders.
    3. Measurement-band folders such as full/regular/petite.
    4. Generic defaults.
    """

    override = os.getenv("VTON_HUMAN_TEMPLATE_PATH", "").strip()
    if override:
        path = Path(override).expanduser()
        if path.exists() and path.is_file():
            return path

    template_dir = get_human_template_dir()
    base_model_id = _safe_name(str(payload.mannequin.base_model_id or "balanced_soft"))
    aliases = TEMPLATE_ALIASES.get(base_model_id, (base_model_id,))
    measurement_band = _measurement_band(payload)

    candidates = list(_candidate_paths(template_dir, aliases, measurement_band))
    return next((path for path in candidates if path.exists() and path.is_file()), None)


def select_human_template_file(payload: VtonPayload) -> Optional[str]:
    """Return the selected template as a string path for API/provider layers."""

    path = select_human_template_path(payload)
    return str(path) if path else None


def _candidate_paths(
    template_dir: Path,
    aliases: Iterable[str],
    measurement_band: BodyMeasurementBand,
) -> Iterable[Path]:
    safe_aliases = [_safe_name(alias) for alias in aliases]
    band_aliases = MEASUREMENT_BANDS.get(measurement_band, (measurement_band,))

    folders = [
        template_dir,
        template_dir / "neutral",
        template_dir / measurement_band,
        template_dir / "neutral" / measurement_band,
    ]

    for folder in folders:
        for alias in safe_aliases:
            yield from _with_extensions(folder / alias)

    for band_alias in band_aliases:
        for folder in (template_dir, template_dir / "neutral"):
            yield from _with_extensions(folder / _safe_name(band_alias))

    for fallback in ("balanced_soft", "default", "neutral"):
        for folder in (template_dir, template_dir / "neutral"):
            yield from _with_extensions(folder / fallback)


def _with_extensions(path_without_extension: Path) -> Iterable[Path]:
    for extension in SUPPORTED_TEMPLATE_EXTENSIONS:
        yield path_without_extension.with_suffix(extension)


def _measurement_band(payload: VtonPayload) -> BodyMeasurementBand:
    mannequin = payload.mannequin
    chest = float(getattr(mannequin, "chest_cm", 0) or 0)
    waist = float(getattr(mannequin, "waist_cm", 0) or 0)
    hip = float(getattr(mannequin, "hip_cm", 0) or 0)
    height = float(getattr(mannequin, "height_cm", 0) or 0)

    circumference_score = max(chest, waist * 1.08, hip)
    if circumference_score >= 112 or (height and circumference_score / max(height, 1) >= 0.66):
        return "full"
    if height and height < 160 and circumference_score < 102:
        return "petite"
    return "regular"


def _safe_name(value: str) -> str:
    return "".join(ch for ch in value.strip().lower() if ch.isalnum() or ch in {"_", "-"})
