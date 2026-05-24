# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import logging
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from PIL import Image

from app.models.product import ProductScrapeResult
from app.services.fabric_physics import analyze_fabric_text, infer_stretch_level
from app.services.image_processor import UPLOAD_DIR
from app.services.size_normalizer import normalize_size_text


LOGGER = logging.getLogger(__name__)
OCR_UPLOAD_DIR = UPLOAD_DIR / "ocr"
OCR_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class OcrUnavailableError(RuntimeError):
    """Raised when no OCR engine is available in the current environment."""


async def extract_size_chart_from_image(file: UploadFile) -> ProductScrapeResult:
    """Extract size measurements from a user-provided size chart screenshot.

    The implementation prefers `pytesseract` when available, but degrades
    gracefully when OCR dependencies are absent on Render Free.
    """

    saved_path = await _save_ocr_upload(file)
    raw_text = _read_image_with_optional_tesseract(saved_path)
    normalized = normalize_size_text(raw_text or "")
    fabric_analysis = analyze_fabric_text(raw_text)
    inferred_stretch = infer_stretch_level(fabric_analysis)
    if inferred_stretch:
        normalized = [
            size.model_copy(update={"stretch_level": size.stretch_level or inferred_stretch})
            for size in normalized
        ]

    confidence = 0.65 if normalized else 0.15 if raw_text else 0.0
    _log_ocr_event(
        "ocr_size_chart",
        filename=file.filename,
        text_found=bool(raw_text),
        sizes_found=len(normalized),
        confidence=confidence,
    )

    return ProductScrapeResult(
        source_url=f"ocr://{saved_path.name}",
        title="Tabela de medidas enviada por imagem",
        image_url=f"/uploads/ocr/{saved_path.name}",
        raw_size_text=raw_text,
        normalized_sizes=normalized,
        fabric_composition_text=raw_text,
        fabric_analysis=fabric_analysis,
        confidence_score=confidence,
        extraction_method="ocr_size_chart",
        fallback_reason=None if normalized else "ocr_without_structured_sizes",
        blocked_by_antibot=False,
    )


async def _save_ocr_upload(file: UploadFile) -> Path:
    suffix = Path(file.filename or "size_chart.png").suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
        suffix = ".png"

    path = OCR_UPLOAD_DIR / f"size_chart_{uuid4().hex}{suffix}"
    content = await file.read()
    path.write_bytes(content)

    with Image.open(path) as image:
        image.verify()

    return path


def _read_image_with_optional_tesseract(path: Path) -> str | None:
    try:
        import pytesseract  # type: ignore
    except Exception:
        _log_ocr_event("ocr_fallback", reason="pytesseract_unavailable")
        return None

    try:
        with Image.open(path) as image:
            prepared = image.convert("RGB")
            prepared.thumbnail((1800, 1800), Image.Resampling.LANCZOS)
            text = pytesseract.image_to_string(prepared, lang="por+eng")
            return text.strip() or None
    except Exception as error:
        _log_ocr_event("ocr_fallback", reason="ocr_failed", error=str(error))
        return None


def _log_ocr_event(event: str, **payload) -> None:
    LOGGER.info(json.dumps({"event": event, **payload}, ensure_ascii=False))
