# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from typing import Dict, List, Optional

from app.models.product import (
    FitCheckInput,
    FitCheckResult,
    FitSizeOption,
    FitZone,
    SizeMeasurement,
)
from app.services.fabric_physics import (
    fabric_ease_modifier,
    fabric_warnings_for_zone,
    infer_stretch_level,
)
from app.utils.tiered_cache import get_cache, set_cache, stable_hash


MEASUREMENT_ALIASES: Dict[str, List[str]] = {
    "chest_cm": ["busto", "tórax", "torax", "peito", "chest", "bust", "bust size"],
    "waist_cm": ["cintura", "waist"],
    "hip_cm": ["quadril", "quadris", "anca", "glúteos", "gluteos", "hip", "hips"],
    "length_cm": ["comprimento total", "comprimento", "altura da peça", "length", "garment length", "clothing length"],
    "sleeve_cm": ["manga", "comprimento da manga", "sleeve", "sleeve length"],
    "biceps_cm": ["circunferência do braço", "circunferencia do braco", "largura do braço", "largura do braco", "upper arm", "biceps", "bíceps", "bicep", "braço", "braco", "arm circumference"],
    "top_length_cm": ["top length", "comprimento superior", "comprimento da parte superior", "comprimento do top"],
    "inseam_cm": ["entrepernas", "entre pernas", "inseam", "comprimento interno", "costura interna"],
    "thigh_cm": ["coxa", "circunferência da coxa", "circunferencia da coxa", "thigh"],
    "shoulder_cm": ["ombro", "ombros", "shoulder", "shoulders", "shoulder width"],
    "rise_cm": ["gancho", "cavalo", "cavalete", "rise", "front rise"],
    "wrist_cm": ["punho", "wrist", "cuff"],
}

MEASUREMENT_LABELS = {
    "chest": "Busto/Tórax",
    "waist": "Cintura",
    "hip": "Quadril",
    "length": "Comprimento total",
    "sleeve": "Manga",
    "biceps": "Bíceps",
    "top_length": "Comprimento superior",
    "inseam": "Entrepernas",
    "thigh": "Coxa",
    "shoulder": "Ombros",
    "rise": "Gancho",
    "wrist": "Punho",
}

ZONE_FIELDS = [
    ("chest", "chest_cm", "user_chest_cm"),
    ("waist", "waist_cm", "user_waist_cm"),
    ("hip", "hip_cm", "user_hip_cm"),
    ("length", "length_cm", "user_length_cm"),
    ("sleeve", "sleeve_cm", "user_sleeve_cm"),
    ("biceps", "biceps_cm", "user_biceps_cm"),
    ("top_length", "top_length_cm", "user_top_length_cm"),
    ("inseam", "inseam_cm", "user_inseam_cm"),
    ("thigh", "thigh_cm", "user_thigh_cm"),
    ("shoulder", "shoulder_cm", "user_shoulder_cm"),
    ("rise", "rise_cm", "user_rise_cm"),
    ("wrist", "wrist_cm", "user_wrist_cm"),
]

CATEGORY_EASE_CM: Dict[str, Dict[str, float]] = {
    "top": {"chest": 4.0, "waist": 3.0, "hip": 3.0, "shoulder": 1.0, "sleeve": 0.5, "biceps": 3.0, "top_length": 0.0, "length": 0.0},
    "pants": {"waist": 2.0, "hip": 4.0, "thigh": 4.0, "inseam": 0.0, "rise": 0.5, "length": 0.0},
    "dress": {"chest": 4.0, "waist": 3.0, "hip": 5.0, "length": 0.0, "sleeve": 0.5, "biceps": 2.5},
    "outerwear": {"chest": 7.0, "waist": 5.0, "hip": 5.0, "shoulder": 1.5, "sleeve": 1.0, "biceps": 4.0, "top_length": 0.0},
    "bodycon": {"chest": 0.0, "waist": 0.0, "hip": 1.0, "biceps": 0.5, "thigh": 1.0, "length": 0.0},
}

STRETCH_EASE_OFFSET = {
    "none": 0.0,
    "low": -0.5,
    "medium": -1.5,
    "high": -3.0,
    "stretch": -2.0,
    "elastic": -3.0,
}

SIZE_ORDER = ["PP", "P", "M", "G", "GG"]
SIZE_ALIASES = {"XS": "PP", "S": "P", "P": "P", "M": "M", "L": "G", "G": "G", "XL": "GG", "GG": "GG", "XXL": "XGG"}
GRADE_STEP_CM = {
    "chest_cm": 4.0,
    "waist_cm": 4.0,
    "hip_cm": 4.0,
    "biceps_cm": 2.0,
    "thigh_cm": 3.0,
    "shoulder_cm": 1.2,
    "sleeve_cm": 1.0,
    "length_cm": 1.0,
    "top_length_cm": 1.0,
    "inseam_cm": 1.0,
    "rise_cm": 0.5,
    "wrist_cm": 0.4,
}

SIZE_PATTERN = re.compile(
    r"\b(pp|xs|p|s|m|g|l|gg|xl|xxl|xxxl|eg|plus|one size|tamanho unico|tamanho único|\d{2,3})\b",
    re.IGNORECASE,
)


def normalize_size_text(raw_text: str) -> List[SizeMeasurement]:
    """Parse public size text into normalized garment measurements."""

    if not raw_text.strip():
        return []

    tabular_results = _parse_common_size_table_rows(raw_text)
    if tabular_results:
        return extrapolate_size_grading(tabular_results)

    results: List[SizeMeasurement] = []
    for block in _candidate_size_blocks(raw_text):
        lower = block.lower()
        size_match = SIZE_PATTERN.search(lower)
        if not size_match:
            continue

        values = {
            field: _find_measure(lower, aliases, field_name=field)
            for field, aliases in MEASUREMENT_ALIASES.items()
        }
        additional = _extract_dynamic_measurements(lower, values)

        if any(value is not None for value in values.values()) or additional:
            results.append(
                SizeMeasurement(
                    size_label=_normalize_size_label(size_match.group(1)),
                    **values,
                    garment_category=_infer_category(lower),
                    stretch_level=_infer_stretch_level(lower),
                    additional_measurements=additional,
                    is_estimated=False,
                    confidence=0.92,
                )
            )

    return extrapolate_size_grading(results)


def extrapolate_size_grading(sizes: List[SizeMeasurement]) -> List[SizeMeasurement]:
    """Expand sparse store size data into P/M/G/GG estimates."""

    if not sizes:
        return []

    by_label: Dict[str, SizeMeasurement] = {}
    for size in sizes:
        normalized = SIZE_ALIASES.get(size.size_label.strip().upper(), size.size_label.strip().upper())
        if normalized in SIZE_ORDER and normalized not in by_label:
            by_label[normalized] = size.model_copy(update={"size_label": normalized})

    if not by_label:
        by_label["M"] = sizes[0].model_copy(update={"size_label": "M"})

    anchor_label = "M" if "M" in by_label else sorted(by_label, key=SIZE_ORDER.index)[0]
    anchor = by_label[anchor_label]
    anchor_index = SIZE_ORDER.index(anchor_label)

    expanded: Dict[str, SizeMeasurement] = dict(by_label)
    for label in SIZE_ORDER:
        if label in expanded:
            continue
        offset = SIZE_ORDER.index(label) - anchor_index
        values = {}
        for field, step in GRADE_STEP_CM.items():
            base_value = getattr(anchor, field, None)
            values[field] = round(base_value + (step * offset), 1) if base_value is not None else None
        expanded[label] = anchor.model_copy(
            update={
                "size_label": label,
                **values,
                "is_estimated": True,
                "estimated_from_size": anchor_label,
                "confidence": max(0.52, 0.78 - abs(offset) * 0.08),
            }
        )

    extras = [
        size
        for size in sizes
        if SIZE_ALIASES.get(size.size_label.strip().upper(), size.size_label.strip().upper()) not in SIZE_ORDER
    ]
    return [expanded[label] for label in SIZE_ORDER if label in expanded] + extras


def evaluate_fit(data: FitCheckInput) -> FitCheckResult:
    """Evaluate garment fit using ease allowance by category and stretch."""

    cache_key = "fit:" + stable_hash(data)
    cached = get_cache(cache_key)
    if cached:
        return cached.model_copy(update={"cache_key": cache_key, "cache_hit": True})

    result = _evaluate_fit_uncached(data).model_copy(update={"cache_key": cache_key, "cache_hit": False})
    set_cache(cache_key, result)
    return result


def _evaluate_fit_uncached(data: FitCheckInput) -> FitCheckResult:
    candidates = extrapolate_size_grading(data.candidate_sizes or [data.garment_size])
    selected_label = data.garment_size.size_label.strip().upper()
    selected = next((size for size in candidates if size.size_label.strip().upper() == selected_label), data.garment_size)

    fabric_stretch = infer_stretch_level(data.fabric_analysis)
    fabric_modifier = fabric_ease_modifier(data.fabric_analysis)
    fabric_warnings = data.fabric_analysis.warnings if data.fabric_analysis else []

    size_options: List[FitSizeOption] = []
    for candidate in candidates:
        zones, summary = _evaluate_single_fit(data, candidate, fabric_stretch, fabric_modifier)
        size_options.append(
            FitSizeOption(
                size_label=candidate.size_label,
                score=_score_zones(zones),
                zones=zones,
                summary=summary,
                is_estimated=candidate.is_estimated,
            )
        )

    best = min(size_options, key=lambda item: item.score) if size_options else None
    if best:
        size_options = [option.model_copy(update={"is_best_match": option.size_label == best.size_label}) for option in size_options]

    selected_option = next((option for option in size_options if option.size_label == selected.size_label), size_options[0] if size_options else None)
    if selected_option:
        return FitCheckResult(
            zones=selected_option.zones,
            summary=selected_option.summary,
            best_size_label=best.size_label if best else None,
            selected_size_label=selected_option.size_label,
            size_options=size_options,
            fabric_warnings=fabric_warnings,
        )

    zones, summary = _evaluate_single_fit(data, selected, fabric_stretch, fabric_modifier)
    return FitCheckResult(zones=zones, summary=summary, selected_size_label=selected.size_label, fabric_warnings=fabric_warnings)


def _evaluate_single_fit(
    data: FitCheckInput,
    garment: SizeMeasurement,
    fabric_stretch: Optional[str],
    fabric_modifier: float,
) -> tuple[List[FitZone], str]:
    user = data.user_measurements
    category = _normalize_category(data.garment_category or garment.garment_category or _infer_category_from_measurement(garment))
    stretch = _normalize_stretch(data.stretch_level or garment.stretch_level or fabric_stretch)
    ease_modifier = data.user_ease_modifier + fabric_modifier

    zones = []
    for zone, garment_field, user_field in ZONE_FIELDS:
        body_value = getattr(data, user_field, None)
        if user and hasattr(user, garment_field):
            body_value = getattr(user, garment_field) or body_value
        garment_value = getattr(garment, garment_field, None)
        zones.append(
            _evaluate_zone(
                zone=zone,
                user_value=body_value,
                garment_value=garment_value,
                label=MEASUREMENT_LABELS.get(zone, zone),
                category=category,
                stretch_level=stretch,
                ease_modifier=ease_modifier,
                fabric_analysis=data.fabric_analysis,
            )
        )

    for key, garment_value in garment.additional_measurements.items():
        user_value = user.additional_measurements.get(key) if user else None
        zones.append(
            _evaluate_zone(
                zone=key,
                user_value=user_value,
                garment_value=garment_value,
                label=key.replace("_", " ").title(),
                category=category,
                stretch_level=stretch,
                ease_modifier=ease_modifier,
                fabric_analysis=data.fabric_analysis,
            )
        )

    return zones, _build_summary(zones)


def _evaluate_zone(
    zone: str,
    user_value: Optional[float],
    garment_value: Optional[float],
    label: str,
    category: str = "top",
    stretch_level: str = "none",
    ease_modifier: float = 0.0,
    fabric_analysis=None,
) -> FitZone:
    if garment_value is None or user_value is None:
        return FitZone(
            zone=zone,
            difference_cm=None,
            status="sem_informacao",
            color="gray",
            message=f"{label}: medida indisponível para cruzamento.",
            body_cm=user_value,
            garment_cm=garment_value,
            ease_allowance_cm=None,
            pressure_score=None,
        )

    ease = _ease_allowance(zone, category, stretch_level, ease_modifier=ease_modifier)
    delta = round(garment_value - user_value - ease, 2)
    pressure = round(max(-6.0, min(6.0, -delta)) / 6.0, 3)

    if delta < -2:
        status, color = "apertado", "red"
        message = f"{label}: APERTADO ({delta:+.1f} cm após margem de {ease:.1f} cm)."
    elif delta <= 1:
        status, color = "justo", "yellow"
        message = f"{label}: JUSTO ({delta:+.1f} cm após margem de {ease:.1f} cm)."
    elif delta <= 6:
        status, color = "folgado", "green"
        message = f"{label}: FOLGADO confortável ({delta:+.1f} cm após margem de {ease:.1f} cm)."
    else:
        status, color = "folgado", "blue"
        message = f"{label}: bem folgado/oversize ({delta:+.1f} cm após margem de {ease:.1f} cm)."

    return FitZone(
        zone=zone,
        difference_cm=delta,
        status=status,
        color=color,
        message=message,
        body_cm=round(user_value, 2),
        garment_cm=round(garment_value, 2),
        ease_allowance_cm=round(ease, 2),
        pressure_score=pressure,
        fabric_warning=fabric_warnings_for_zone(status, fabric_analysis),
    )



def _parse_common_size_table_rows(raw_text: str) -> List[SizeMeasurement]:
    """Parse compact rows commonly produced by OCR from marketplace size tables.

    Example supported row: `M 72-102 85` when the header contains waist and
    length. Range values are treated as elastic/adjustable measurements: the
    upper bound is used for fit, while the lower bound is preserved in
    additional_measurements.
    """

    lower = raw_text.lower()
    has_waist = any(token in lower for token in ("cintura", "waist", "tamanho da cintura"))
    has_length = any(token in lower for token in ("comprimento", "length"))
    if not (has_waist and has_length):
        return []

    normalized_text = re.sub(r"[|;]+", " ", raw_text)
    normalized_text = re.sub(r"(?i)\bbr\b", " ", normalized_text)
    rows: List[SizeMeasurement] = []
    row_pattern = re.compile(
        r"\b(pp|xs|p|s|m|g|l|gg|xl|xxl)\b\s+"
        r"(\d+(?:[,.]\d+)?(?:\s*[-–—]\s*\d+(?:[,.]\d+)?)?)\s+"
        r"(\d+(?:[,.]\d+)?)\b",
        flags=re.IGNORECASE,
    )

    for match in row_pattern.finditer(normalized_text):
        size_label = _normalize_size_label(match.group(1))
        waist_value, waist_min = _parse_measure_or_range(match.group(2))
        length_value, _ = _parse_measure_or_range(match.group(3))
        if waist_value is None and length_value is None:
            continue
        additional = {}
        if waist_min is not None and waist_value is not None and waist_min != waist_value:
            additional["waist_min_cm"] = waist_min
        rows.append(
            SizeMeasurement(
                size_label=size_label,
                waist_cm=waist_value,
                length_cm=length_value,
                garment_category="pants",
                stretch_level="high" if waist_min is not None and waist_value and waist_value - waist_min >= 12 else "medium",
                additional_measurements=additional,
                is_estimated=False,
                confidence=0.95,
            )
        )

    return rows


def _parse_measure_or_range(raw_value: str) -> tuple[Optional[float], Optional[float]]:
    parts = re.split(r"\s*[-–—]\s*", raw_value.strip())
    parsed = [_to_float(part) for part in parts if part.strip()]
    parsed = [value for value in parsed if value is not None]
    if not parsed:
        return None, None
    if len(parsed) == 1:
        return parsed[0], None
    return max(parsed), min(parsed)
def _candidate_size_blocks(raw_text: str) -> List[str]:
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    blocks: List[str] = []

    for index, line in enumerate(lines):
        blocks.append(line)
        merged = " ".join(lines[index : index + 4])
        if merged != line:
            blocks.append(merged)
    blocks.append(" ".join(lines))

    unique_blocks: List[str] = []
    seen = set()
    for block in blocks:
        if block and block not in seen:
            unique_blocks.append(block)
            seen.add(block)
    return unique_blocks


def _find_measure(text: str, aliases: List[str], field_name: Optional[str] = None) -> Optional[float]:
    for alias in sorted(aliases, key=len, reverse=True):
        escaped = re.escape(alias)
        patterns = [
            rf"{escaped}\s*(?:\([^)]*\))?\s*[:：=\-]?\s*(\d+(?:[,.]\d+)?)\s*(?:cm|centímetros|centimetros)?",
            rf"(\d+(?:[,.]\d+)?)\s*(?:cm|centímetros|centimetros)?\s*(?:de\s+)?{escaped}",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match and not _is_excluded_alias_match(field_name, alias, text, match.start(), match.end()):
                return _to_float(match.group(1))
    return None


def _is_excluded_alias_match(field_name: Optional[str], alias: str, text: str, start: int, end: int) -> bool:
    if field_name != "length_cm" or alias.lower() not in {"length", "comprimento"}:
        return False
    before = text[max(0, start - 28) : start].lower()
    return bool(
        re.search(r"(busto|tórax|torax|chest|bust|cintura|waist|quadril|hip|hips)\s*[:=\-]?\s*$", before)
        or re.search(r"(sleeve|manga|top|superior)\s*$", before)
    )


def _extract_dynamic_measurements(text: str, known_values: Dict[str, Optional[float]]) -> Dict[str, float]:
    matched_values = {value for value in known_values.values() if value is not None}
    dynamic: Dict[str, float] = {}
    pattern = re.compile(r"([a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s/]{2,28})\s*[:：=\-]\s*(\d+(?:[,.]\d+)?)\s*(?:cm)?", flags=re.IGNORECASE)
    known_aliases = {alias for aliases in MEASUREMENT_ALIASES.values() for alias in aliases}

    for label, raw_value in pattern.findall(text):
        value = _to_float(raw_value)
        clean_label = label.strip().lower()
        if value is None or value in matched_values or clean_label in known_aliases:
            continue
        dynamic[re.sub(r"\s+", "_", clean_label)] = value
    return dynamic


def _score_zones(zones: List[FitZone]) -> float:
    score = 0.0
    known_count = 0
    for zone in zones:
        if zone.status == "sem_informacao":
            score += 3.0
            continue
        known_count += 1
        if zone.status == "apertado":
            score += 100.0 + abs(zone.difference_cm or 0) * 4.0
        elif zone.status == "justo":
            score += 14.0 + abs(zone.difference_cm or 0)
        elif zone.color == "blue":
            score += 24.0 + abs(zone.difference_cm or 0)
        else:
            score += abs((zone.difference_cm or 0) - 3.0)
    if known_count == 0:
        score += 80.0
    return round(score, 3)


def _ease_allowance(zone: str, category: str, stretch_level: str, ease_modifier: float = 0.0) -> float:
    category_ease = CATEGORY_EASE_CM.get(category, CATEGORY_EASE_CM["top"])
    base = category_ease.get(zone, 2.0)
    if zone in {"length", "top_length", "inseam", "sleeve", "rise"}:
        base = category_ease.get(zone, 0.0)
    return round(max(-4.0, base + STRETCH_EASE_OFFSET.get(stretch_level, 0.0) + ease_modifier), 2)


def _build_summary(zones: List[FitZone]) -> str:
    known = [zone for zone in zones if zone.status != "sem_informacao"]
    if not known:
        return "A loja não informou medidas suficientes para diagnosticar o caimento."
    if any(zone.status == "apertado" for zone in known):
        return "Há regiões com risco de aperto ou tecido sob pressão."
    if any(zone.status == "justo" for zone in known):
        return "A peça tende a vestir justo em algumas regiões."
    if any(zone.color == "blue" for zone in known):
        return "A peça tende a ficar bem ampla/oversize."
    return "A peça tem folga confortável nas regiões avaliadas."


def _infer_category(text: str) -> Optional[str]:
    if re.search(r"\b(calca|calça|pants|jeans|short|shorts|legging|saia|skirt)\b", text):
        return "pants"
    if re.search(r"\b(vestido|dress)\b", text):
        return "dress"
    if re.search(r"\b(jaqueta|casaco|blazer|coat|jacket|outerwear)\b", text):
        return "outerwear"
    if re.search(r"\b(bodycon|justo|compressao|compressão|legging)\b", text):
        return "bodycon"
    return "top"


def _infer_category_from_measurement(garment: SizeMeasurement) -> str:
    if garment.inseam_cm or garment.thigh_cm or garment.rise_cm:
        return "pants"
    if garment.length_cm and garment.hip_cm and garment.chest_cm:
        return "dress"
    return "top"


def _normalize_category(value: Optional[str]) -> str:
    if not value:
        return "top"
    normalized = value.strip().lower()
    if normalized in {"calca", "calça", "pants", "jeans", "shorts", "skirt", "saia"}:
        return "pants"
    if normalized in {"dress", "vestido"}:
        return "dress"
    if normalized in {"jacket", "jaqueta", "coat", "casaco", "outerwear", "blazer"}:
        return "outerwear"
    if normalized in {"bodycon", "fitness", "legging", "compressao", "compressão"}:
        return "bodycon"
    return "top"


def _infer_stretch_level(text: str) -> Optional[str]:
    if re.search(r"\b(alta elasticidade|high stretch|super stretch)\b", text):
        return "high"
    if re.search(r"\b(elastano|spandex|elastane|stretch|elastic|malha|knit)\b", text):
        return "medium"
    return None


def _normalize_stretch(value: Optional[str]) -> str:
    if not value:
        return "none"
    normalized = value.strip().lower().replace("_", " ")
    if normalized in {"alto", "alta", "high", "alta elasticidade"}:
        return "high"
    if normalized in {"medio", "médio", "medium", "elastano", "stretch"}:
        return "medium"
    if normalized in {"baixo", "baixa", "low"}:
        return "low"
    if normalized in {"elastic", "elastico", "elástico"}:
        return "elastic"
    return "none"


def _normalize_size_label(value: str) -> str:
    return SIZE_ALIASES.get(value.strip().upper(), value.strip().upper())


def _to_float(value: str) -> Optional[float]:
    try:
        return float(value.replace(",", ".").strip())
    except ValueError:
        return None
