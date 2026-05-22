from __future__ import annotations

import re
from typing import Iterable, Optional

from app.models.product import FabricAnalysis


STRETCH_FIBERS = {"elastano", "elastane", "spandex", "lycra"}
SHRINK_FIBERS = {"algodao", "algodão", "cotton", "viscose", "rayon", "linho", "linen", "wool", "la"}
DRAPE_FIBERS = {"viscose", "rayon", "modal", "tencel", "poliester", "polyester"}


def analyze_fabric_text(raw_text: Optional[str]) -> FabricAnalysis:
    """Extract light textile behavior signals from public composition text."""

    if not raw_text:
        return FabricAnalysis()

    text = _normalize(raw_text)
    percentages = _extract_percentages(text)
    detected = _detect_fibers(text)

    stretch_percent = sum(percentages.get(fiber, 0.0) for fiber in STRETCH_FIBERS)
    shrink_percent = sum(percentages.get(fiber, 0.0) for fiber in SHRINK_FIBERS)
    drape_percent = sum(percentages.get(fiber, 0.0) for fiber in DRAPE_FIBERS)

    if shrink_percent == 0 and any(fiber in detected for fiber in SHRINK_FIBERS):
        shrink_percent = 45.0

    if drape_percent == 0 and any(fiber in detected for fiber in DRAPE_FIBERS):
        drape_percent = 35.0

    stretch_factor = min(0.12, stretch_percent / 100.0)
    shrink_risk = min(1.0, shrink_percent / 100.0)
    drape_factor = min(1.0, 0.35 + drape_percent / 140.0)

    warnings = []
    if stretch_factor >= 0.03:
        warnings.append("Tecido com elasticidade detectada; ajuste apertado fica menos critico.")
    if shrink_risk >= 0.55:
        warnings.append("Fibra natural/viscose com risco de encolhimento apos lavagem.")

    return FabricAnalysis(
        raw_text=raw_text.strip(),
        stretch_factor=round(stretch_factor, 3),
        shrink_risk=round(shrink_risk, 3),
        drape_factor=round(drape_factor, 3),
        detected_fibers=sorted(detected),
        warnings=warnings,
    )


def infer_stretch_level(analysis: Optional[FabricAnalysis]) -> Optional[str]:
    if not analysis:
        return None
    if analysis.stretch_factor >= 0.05:
        return "high"
    if analysis.stretch_factor >= 0.015:
        return "medium"
    return None


def fabric_ease_modifier(analysis: Optional[FabricAnalysis]) -> float:
    """Return cm modifier added to the ease allowance.

    Positive values demand more ease for shrink-prone fabrics. Negative values
    loosen the model for elastic fabrics.
    """

    if not analysis:
        return 0.0

    shrink_modifier = analysis.shrink_risk * 1.8
    stretch_modifier = analysis.stretch_factor * -28.0
    return round(max(-3.0, min(3.0, shrink_modifier + stretch_modifier)), 2)


def fabric_warnings_for_zone(
    zone_status: str,
    analysis: Optional[FabricAnalysis],
) -> Optional[str]:
    if not analysis:
        return None
    if analysis.shrink_risk >= 0.55 and zone_status in {"apertado", "justo"}:
        return "Risco de ficar apertado apos lavagem."
    if analysis.stretch_factor >= 0.03 and zone_status == "apertado":
        return "Elasticidade do tecido pode compensar parte da pressao."
    return None


def _extract_percentages(text: str) -> dict[str, float]:
    values: dict[str, float] = {}
    pattern = re.compile(r"(\d+(?:[,.]\d+)?)\s*%\s*([a-zA-ZÀ-ÿ]+)|([a-zA-ZÀ-ÿ]+)\s*(\d+(?:[,.]\d+)?)\s*%")

    for left_value, left_fiber, right_fiber, right_value in pattern.findall(text):
        fiber = _normalize(left_fiber or right_fiber)
        raw_value = left_value or right_value
        try:
            values[fiber] = values.get(fiber, 0.0) + float(raw_value.replace(",", "."))
        except ValueError:
            continue

    return values


def _detect_fibers(text: str) -> set[str]:
    candidates = STRETCH_FIBERS | SHRINK_FIBERS | DRAPE_FIBERS
    return {fiber for fiber in candidates if re.search(rf"\b{re.escape(fiber)}\b", text)}


def _normalize(value: str) -> str:
    return value.strip().lower().replace("ã£", "a").replace("ã§", "c")
