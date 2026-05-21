import re
from typing import List, Optional

from app.models.product import (
    SizeMeasurement,
    FitZone,
    FitCheckResult,
    FitCheckInput,
)


def _to_float(value: str) -> Optional[float]:
    cleaned = value.replace(",", ".").strip()

    try:
        return float(cleaned)
    except ValueError:
        return None


def normalize_size_text(raw_text: str) -> List[SizeMeasurement]:
    """
    Normalizador simples para MVP.
    Lê linhas como:
    P busto 88 cintura 70 quadril 94
    M chest 94 waist 76 hip 100
    G bust 100 waist 82 hips 106
    """
    if not raw_text.strip():
        return []

    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    results: List[SizeMeasurement] = []

    for line in lines:
        lower = line.lower()

        size_match = re.search(
            r"\b(pp|xs|p|s|m|g|l|gg|xl|xxl|eg|plus|one size|\d{2,3})\b",
            lower,
        )

        if not size_match:
            continue

        size_label = size_match.group(1).upper()

        chest = _find_measure(lower, ["busto", "torax", "tórax", "chest", "bust"])
        waist = _find_measure(lower, ["cintura", "waist"])
        hip = _find_measure(lower, ["quadril", "hip", "hips"])
        length = _find_measure(lower, ["comprimento", "length"])
        shoulder = _find_measure(lower, ["ombro", "shoulder"])
        sleeve = _find_measure(lower, ["manga", "sleeve"])

        if any(value is not None for value in [chest, waist, hip, length, shoulder, sleeve]):
            results.append(
                SizeMeasurement(
                    size_label=size_label,
                    chest_cm=chest,
                    waist_cm=waist,
                    hip_cm=hip,
                    length_cm=length,
                    shoulder_cm=shoulder,
                    sleeve_cm=sleeve,
                )
            )

    return results


def _find_measure(text: str, keywords: List[str]) -> Optional[float]:
    for keyword in keywords:
        pattern = rf"{keyword}\s*[:\-]?\s*(\d+(?:[,.]\d+)?)"
        match = re.search(pattern, text)

        if match:
            return _to_float(match.group(1))

    return None


def evaluate_fit(data: FitCheckInput) -> FitCheckResult:
    zones = [
        _evaluate_zone(
            zone="chest",
            user_value=data.user_chest_cm,
            garment_value=data.garment_size.chest_cm,
            label="Busto/Tórax",
        ),
        _evaluate_zone(
            zone="waist",
            user_value=data.user_waist_cm,
            garment_value=data.garment_size.waist_cm,
            label="Cintura",
        ),
        _evaluate_zone(
            zone="hip",
            user_value=data.user_hip_cm,
            garment_value=data.garment_size.hip_cm,
            label="Quadril",
        ),
    ]

    return FitCheckResult(
        zones=zones,
        summary=_build_summary(zones),
    )


def _evaluate_zone(
    zone: str,
    user_value: float,
    garment_value: Optional[float],
    label: str,
) -> FitZone:
    if garment_value is None:
        return FitZone(
            zone=zone,
            difference_cm=None,
            status="unknown",
            color="gray",
            message=f"{label}: a peça não informou essa medida.",
        )

    difference = round(garment_value - user_value, 2)

    if difference < 0:
        return FitZone(
            zone=zone,
            difference_cm=difference,
            status="too_small",
            color="red",
            message=f"{label}: peça menor que o corpo em {abs(difference)} cm. Alto risco de não servir.",
        )

    if difference < 2:
        return FitZone(
            zone=zone,
            difference_cm=difference,
            status="tight",
            color="red",
            message=f"{label}: diferença de {difference} cm. Provavelmente apertado.",
        )

    if 2 <= difference <= 5:
        return FitZone(
            zone=zone,
            difference_cm=difference,
            status="balanced",
            color="yellow",
            message=f"{label}: diferença de {difference} cm. Caimento próximo ao corpo.",
        )

    return FitZone(
        zone=zone,
        difference_cm=difference,
        status="loose",
        color="green",
        message=f"{label}: diferença de {difference} cm. Folga confortável.",
    )


def _build_summary(zones: List[FitZone]) -> str:
    statuses = [zone.status for zone in zones]

    if "too_small" in statuses:
        return "A peça parece pequena em pelo menos uma região importante."

    if "tight" in statuses:
        return "A peça pode ficar apertada em algumas regiões."

    known_statuses = [status for status in statuses if status != "unknown"]

    if known_statuses and all(status == "loose" for status in known_statuses):
        return "A peça parece ter folga confortável."

    if "balanced" in statuses:
        return "A peça parece ter caimento próximo ao corpo."

    return "Não há medidas suficientes para uma avaliação completa."