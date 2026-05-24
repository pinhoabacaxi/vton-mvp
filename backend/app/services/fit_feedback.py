# -*- coding: utf-8 -*-
from __future__ import annotations

from app.models.product import FitFeedbackInput, FitFeedbackResult


_USER_EASE_MODIFIERS: dict[str, float] = {}

STATUS_RANK = {
    "apertado": 0,
    "too_small": 0,
    "tight": 0,
    "justo": 1,
    "balanced": 1,
    "folgado": 2,
    "loose": 2,
}


def get_user_ease_modifier(user_key: str = "local-device") -> float:
    return _USER_EASE_MODIFIERS.get(user_key, 0.0)


def record_fit_feedback(data: FitFeedbackInput) -> FitFeedbackResult:
    predicted = STATUS_RANK.get(data.predicted_status, 1)
    reported = STATUS_RANK.get(data.reported_status, 1)
    delta = reported - predicted

    current = get_user_ease_modifier(data.user_key)
    # If the user reports tighter than predicted, demand more ease next time.
    updated = _clamp(current + (delta * -0.45), -3.0, 3.0)
    _USER_EASE_MODIFIERS[data.user_key] = updated

    return FitFeedbackResult(
        user_key=data.user_key,
        user_ease_modifier=round(updated, 2),
        message="Preferencia de caimento atualizada para proximas predicoes.",
    )


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))
