from __future__ import annotations

from typing import Dict, Tuple

from app.models.body import FineTuneInput


ADVANCED_FIELDS = [
    "shoulder_cm",
    "sleeve_cm",
    "biceps_cm",
    "top_length_cm",
    "inseam_cm",
    "thigh_cm",
    "rise_cm",
    "wrist_cm",
]


def estimate_missing_measurements(
    data: FineTuneInput,
) -> Tuple[Dict[str, float], Dict[str, bool]]:
    """Fill optional body measurements with non-persistent estimates.

    The returned `estimated` flags are as important as the numbers: downstream
    code can render a complete mannequin without treating inferred values as
    explicit user input.
    """

    estimates = {
        "shoulder_cm": _clamp(data.chest_cm * 0.43, 34.0, 58.0),
        "sleeve_cm": _clamp(data.height_cm * 0.35, 46.0, 76.0),
        "biceps_cm": _clamp(data.chest_cm * 0.31 + data.weight_kg * 0.025, 24.0, 52.0),
        "top_length_cm": _clamp(data.height_cm * 0.36, 48.0, 82.0),
        "inseam_cm": _clamp(data.height_cm * 0.46, 58.0, 96.0),
        "thigh_cm": _clamp(data.hip_cm * 0.58, 42.0, 88.0),
        "rise_cm": _clamp(data.height_cm * 0.16, 22.0, 38.0),
        "wrist_cm": _clamp((data.chest_cm * 0.31 + data.weight_kg * 0.025) * 0.52, 14.0, 25.0),
    }

    measurements: Dict[str, float] = {}
    estimated: Dict[str, bool] = {}

    for field in ADVANCED_FIELDS:
        explicit = getattr(data, field)
        if explicit is not None:
            measurements[field] = float(explicit)
            estimated[field] = False
        else:
            measurements[field] = round(estimates[field], 1)
            estimated[field] = True

    return measurements, estimated


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))
