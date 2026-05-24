# -*- coding: utf-8 -*-
from __future__ import annotations

import html
import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Iterable
from urllib.parse import unquote, urlparse

import httpx
from bs4 import BeautifulSoup

from app.models.product import ProductScrapeResult
from app.services.fabric_physics import analyze_fabric_text, infer_stretch_level
from app.services.size_normalizer import normalize_size_text


LOGGER = logging.getLogger(__name__)


class AntiBotChallengeError(RuntimeError):
    """Raised when a store returns a challenge page instead of product HTML."""


@dataclass(frozen=True)
class ExtractionCandidate:
    raw_size_text: str | None
    confidence_score: float
    extraction_method: str


MEASUREMENT_KEYWORDS = [
    "busto",
    "tórax",
    "torax",
    "peito",
    "cintura",
    "quadril",
    "quadris",
    "comprimento",
    "manga",
    "bíceps",
    "biceps",
    "braço",
    "braco",
    "coxa",
    "entrepernas",
    "entre pernas",
    "ombro",
    "ombros",
    "punho",
    "gancho",
    "chest",
    "bust",
    "waist",
    "hip",
    "hips",
    "length",
    "sleeve",
    "inseam",
    "thigh",
    "shoulder",
    "wrist",
    "rise",
    "arm",
    "measurements",
    "sizechart",
    "size chart",
    "size guide",
    "dimensions",
]

FABRIC_KEYWORDS = [
    "composição",
    "composicao",
    "tecido",
    "material",
    "fabric",
    "composition",
    "algodão",
    "algodao",
    "cotton",
    "viscose",
    "elastano",
    "elastane",
    "spandex",
    "lycra",
    "polyester",
    "poliéster",
    "poliester",
    "nylon",
]

FIBER_KEYWORDS = [
    "algodão",
    "algodao",
    "cotton",
    "viscose",
    "elastano",
    "elastane",
    "spandex",
    "lycra",
    "polyester",
    "poliéster",
    "poliester",
    "nylon",
]

SEMANTIC_CONTAINER_SELECTORS = [
    ".size-guide",
    ".size-chart",
    ".sizechart",
    ".measurement",
    ".measurements",
    ".product-measurements",
    ".product-size",
    "#size-guide",
    "#sizeChart",
    "#product-details",
    "[data-testid*='size']",
    "[class*='size-guide']",
    "[class*='size-chart']",
    "[class*='measurement']",
]

ANTI_BOT_PATH_FRAGMENTS = [
    "/risk/",
    "/challenge",
    "/captcha",
    "/verify",
]

ANTI_BOT_TEXT_PATTERNS = [
    "just a moment",
    "checking your browser",
    "cloudflare",
    "datadome",
    "captcha",
    "risk/challenge",
    "cf-challenge",
    "are you human",
]

SIZE_LABEL_PATTERN = re.compile(
    r"\b(pp|xs|p|s|m|g|l|gg|xl|xxl|xxxl|eg|plus|one size|tamanho unico|tamanho único|\d{2,3})\b",
    re.IGNORECASE,
)
CM_VALUE_PATTERN = re.compile(r"\d+(?:[,.]\d+)?\s*cm", re.IGNORECASE)


async def scrape_product_page(url: str) -> ProductScrapeResult:
    """Scrape public product data using semantic extraction islands.

    The scraper is intentionally conservative. It does not login, bypass
    captchas, automate a browser, or read arbitrary page text as truth.
    """

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("URL inválida.")

    response_text, final_url = await _fetch_public_html(url)
    _raise_if_antibot_challenge(final_url, response_text)

    soup = BeautifulSoup(response_text, "html.parser", from_encoding="utf-8")
    candidate = _extract_size_candidate(soup)
    raw_size_text = candidate.raw_size_text
    normalized = normalize_size_text(raw_size_text or "")

    fabric_text = _extract_fabric_composition(soup)
    fabric_analysis = analyze_fabric_text(fabric_text)
    inferred_stretch = infer_stretch_level(fabric_analysis)
    if inferred_stretch:
        normalized = [
            size.model_copy(update={"stretch_level": size.stretch_level or inferred_stretch})
            for size in normalized
        ]

    title = _extract_title(soup) or _title_from_product_slug(url) or "Produto sem título detectado"
    if _is_generic_store_title(title):
        title = _title_from_product_slug(url) or title

    _log_scraper_event(
        "scraper_extraction",
        url=final_url,
        method=candidate.extraction_method,
        confidence=candidate.confidence_score,
        sizes_found=len(normalized),
    )

    return ProductScrapeResult(
        source_url=url,
        title=title,
        image_url=_extract_image(soup),
        currency=None,
        price=_extract_price(soup),
        raw_size_text=raw_size_text,
        normalized_sizes=normalized,
        fabric_composition_text=fabric_text,
        fabric_analysis=fabric_analysis,
        confidence_score=candidate.confidence_score,
        extraction_method=candidate.extraction_method,
        fallback_reason=None if raw_size_text else "no_public_size_data",
        blocked_by_antibot=False,
    )


async def _fetch_public_html(url: str) -> tuple[str, str]:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 VTON-MVP/0.1"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    async with httpx.AsyncClient(timeout=25, follow_redirects=True) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
    return response.text, str(response.url)


def _raise_if_antibot_challenge(final_url: str, html_text: str) -> None:
    parsed = urlparse(final_url)
    normalized_path = parsed.path.lower()
    normalized_text = html_text[:120_000].lower()

    blocked_by_path = any(fragment in normalized_path for fragment in ANTI_BOT_PATH_FRAGMENTS)
    blocked_by_text = any(pattern in normalized_text for pattern in ANTI_BOT_TEXT_PATTERNS)

    if blocked_by_path or blocked_by_text:
        _log_scraper_event(
            "scraper_fallback",
            reason="antibot_challenge",
            domain=parsed.netloc,
            path=parsed.path,
        )
        raise AntiBotChallengeError("A loja bloqueou a leitura automática.")


def _extract_size_candidate(soup: BeautifulSoup) -> ExtractionCandidate:
    strategies = [
        ("state_hydration", 1.0, _extract_from_state_hydration),
        ("semantic_table", 0.8, _extract_from_semantic_containers),
        ("regex_fallback", 0.3, _extract_from_regex_fallback),
    ]

    for method, confidence, extractor in strategies:
        lines = _dedupe_lines(extractor(soup), limit=120)
        text = "\n".join(lines) if lines else None
        if text and normalize_size_text(text):
            return ExtractionCandidate(text, confidence, method)

    return ExtractionCandidate(None, 0.0, "not_found")


def _extract_from_state_hydration(soup: BeautifulSoup) -> list[str]:
    chunks: list[str] = []
    for payload in _iter_embedded_json_payloads(soup):
        chunks.extend(_walk_json_for_measurements(payload))
    return chunks


def _extract_from_semantic_containers(soup: BeautifulSoup) -> list[str]:
    chunks: list[str] = []
    for selector in SEMANTIC_CONTAINER_SELECTORS:
        for container in soup.select(selector):
            chunks.extend(_extract_structured_container_lines(container))
    return chunks


def _extract_from_regex_fallback(soup: BeautifulSoup) -> list[str]:
    chunks: list[str] = []
    visible_soup = BeautifulSoup(str(soup), "html.parser", from_encoding="utf-8")
    for tag in visible_soup(["script", "style", "noscript", "svg", "nav", "header", "footer"]):
        tag.decompose()

    lines = [_clean_text(line) for line in visible_soup.get_text("\n", strip=True).splitlines()]
    lines = [line for line in lines if line]

    for index, line in enumerate(lines):
        context = " ".join(lines[max(0, index - 1) : min(len(lines), index + 2)])
        if _is_measurement_context(context) and _near_size_context(lines, index):
            chunks.append(context)

    return chunks


def _extract_structured_container_lines(container: Any) -> list[str]:
    chunks: list[str] = []
    for table in container.find_all("table"):
        chunks.extend(_table_to_measurement_lines(table))

    for list_tag in container.find_all(["ul", "ol", "dl"]):
        text = list_tag.get_text("\n", strip=True)
        for line in text.splitlines():
            clean = _clean_text(line)
            if _is_measurement_context(clean):
                chunks.append(clean)

    if not chunks:
        text = container.get_text("\n", strip=True)
        lines = [_clean_text(line) for line in text.splitlines()]
        chunks.extend(line for line in lines if _is_measurement_context(line))

    return chunks


def _table_to_measurement_lines(table: Any) -> list[str]:
    rows = []
    for tr in table.find_all("tr"):
        cells = [_clean_text(cell.get_text(" ", strip=True)) for cell in tr.find_all(["th", "td"])]
        cells = [cell for cell in cells if cell]
        if cells:
            rows.append(cells)

    if len(rows) < 2:
        return []

    table_text = " ".join(" ".join(row) for row in rows).lower()
    if not _is_measurement_context(table_text):
        return []

    lines: list[str] = []
    header = rows[0]

    if any(_looks_like_size_label(row[0]) for row in rows[1:] if row):
        for row in rows[1:]:
            size_label = row[0]
            pairs = [
                f"{header[index]} {row[index]}"
                for index in range(1, min(len(header), len(row)))
                if _is_measurement_context(header[index]) or CM_VALUE_PATTERN.search(row[index])
            ]
            if pairs and _looks_like_size_label(size_label):
                lines.append(f"{size_label} {' '.join(pairs)}")

    size_headers = [cell for cell in header if _looks_like_size_label(cell)]
    if size_headers:
        size_values: dict[str, list[str]] = {size: [] for size in size_headers}
        for row in rows[1:]:
            if not row:
                continue
            measure_name = row[0]
            if not _is_measurement_context(measure_name):
                continue
            for index, size in enumerate(header[1:], start=1):
                if size in size_values and index < len(row):
                    size_values[size].append(f"{measure_name} {row[index]}")
        lines.extend(f"{size} {' '.join(values)}" for size, values in size_values.items() if values)

    return lines


def _iter_embedded_json_payloads(soup: BeautifulSoup) -> Iterable[Any]:
    for script in soup.find_all("script"):
        script_type = (script.get("type") or "").lower()
        script_id = (script.get("id") or "").lower()
        raw = script.string or script.get_text(" ", strip=True)
        if not raw:
            continue

        if script_type in {"application/ld+json", "application/json"} or script_id in {"__next_data__", "nuxt-data"}:
            yield from _parse_possible_json_objects(raw)
            continue

        if "__INITIAL_STATE__" in raw or "sizeChart" in raw or "measurements" in raw:
            yield from _parse_possible_json_objects(raw)


def _walk_json_for_measurements(value: Any, parent_key: str = "") -> list[str]:
    chunks: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            combined_key = f"{parent_key} {key_text}".strip()
            if _is_measurement_key(combined_key):
                chunks.extend(_json_measurement_lines(combined_key, child))
            chunks.extend(_walk_json_for_measurements(child, combined_key))
    elif isinstance(value, list):
        for item in value:
            chunks.extend(_walk_json_for_measurements(item, parent_key))
    elif isinstance(value, str) and _is_measurement_context(value):
        chunks.append(value)
    return chunks


def _json_measurement_lines(key: str, value: Any) -> list[str]:
    if isinstance(value, str):
        return [f"{key}: {value}"] if _is_measurement_context(value) else []
    if isinstance(value, (int, float)):
        return [f"{key}: {value}"]
    if isinstance(value, dict):
        parts = []
        for child_key, child in value.items():
            if isinstance(child, (str, int, float)):
                parts.append(f"{child_key} {child}")
        joined = " ".join(parts)
        return [joined] if _is_measurement_context(joined) else []
    if isinstance(value, list):
        lines = []
        for item in value:
            lines.extend(_json_measurement_lines(key, item))
        return lines
    return []


def _extract_title(soup: BeautifulSoup) -> str | None:
    product_json = _extract_product_json(soup)
    if product_json and isinstance(product_json.get("name"), str):
        return _clean_text(product_json["name"])

    for selector in [
        ("meta", {"property": "og:title"}),
        ("meta", {"name": "twitter:title"}),
        ("meta", {"itemprop": "name"}),
    ]:
        tag = soup.find(*selector)
        if tag and tag.get("content"):
            return _clean_text(tag["content"])

    h1 = soup.find("h1")
    if h1:
        return _clean_text(h1.get_text(" ", strip=True))

    if soup.title and soup.title.string:
        return _clean_text(soup.title.string)

    return None


def _is_generic_store_title(title: str | None) -> bool:
    if not title:
        return True
    normalized = title.lower()
    return any(
        fragment in normalized
        for fragment in [
            "loja de moda online",
            "roupas femininas",
            "roupas masculinas",
            "online fashion",
            "shein",
        ]
    )


def _title_from_product_slug(url: str) -> str | None:
    path = unquote(urlparse(url).path)
    filename = path.rsplit("/", 1)[-1]
    if not filename:
        return None

    slug = filename.split(".html", 1)[0]
    if "-p-" in slug:
        slug = slug.split("-p-", 1)[0]

    words = [word for word in slug.replace("_", "-").split("-") if word]
    if len(words) < 2:
        return None
    return " ".join(words)


def _extract_image(soup: BeautifulSoup) -> str | None:
    product_json = _extract_product_json(soup)
    if product_json:
        image = product_json.get("image")
        if isinstance(image, str):
            return _absolute_protocol_url(image)
        if isinstance(image, list) and image:
            return _absolute_protocol_url(str(image[0]))

    for selector in [
        ("meta", {"property": "og:image"}),
        ("meta", {"name": "twitter:image"}),
        ("meta", {"itemprop": "image"}),
    ]:
        tag = soup.find(*selector)
        if tag and tag.get("content"):
            return _absolute_protocol_url(tag["content"].strip())

    product_area = soup.select_one("#product-details, .product, [class*='product']")
    candidates = product_area.find_all("img") if product_area else soup.find_all("img")
    for image in candidates:
        src = image.get("src") or image.get("data-src") or image.get("data-original")
        if src and not src.startswith("data:"):
            return _absolute_protocol_url(src.strip())

    return None


def _extract_price(soup: BeautifulSoup) -> str | None:
    product_json = _extract_product_json(soup)
    if product_json:
        offers = product_json.get("offers")
        if isinstance(offers, dict) and offers.get("price"):
            return str(offers["price"])

    candidates = []
    for attr in ["price", "product:price:amount"]:
        meta = soup.find("meta", property=attr) or soup.find("meta", attrs={"name": attr})
        if meta and meta.get("content"):
            candidates.append(meta["content"].strip())

    text = soup.get_text(" ", strip=True)
    price_match = re.search(r"(R\$|US\$|\$|BRL|USD)\s?\d+[,.]?\d*", text)
    if price_match:
        candidates.append(price_match.group(0))

    return candidates[0] if candidates else None


def _extract_fabric_composition(soup: BeautifulSoup) -> str | None:
    chunks: list[str] = []
    for payload in _iter_embedded_json_payloads(soup):
        chunks.extend(_walk_json_for_fabric(payload))

    product_details = soup.select("#product-details, .product-details, .product-info, [class*='fabric'], [class*='composition']")
    for container in product_details:
        text = container.get_text("\n", strip=True)
        chunks.extend(_keyword_contexts(text, FABRIC_KEYWORDS))

    cleaned = [line for line in _dedupe_lines(chunks, limit=40) if _is_fabric_context(line)]
    return "\n".join(cleaned) if cleaned else None


def _walk_json_for_fabric(value: Any, parent_key: str = "") -> list[str]:
    chunks: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            combined_key = f"{parent_key} {key}".strip()
            if _has_any_keyword(combined_key, FABRIC_KEYWORDS):
                chunks.extend(_json_fabric_lines(combined_key, child))
            chunks.extend(_walk_json_for_fabric(child, combined_key))
    elif isinstance(value, list):
        for item in value:
            chunks.extend(_walk_json_for_fabric(item, parent_key))
    elif isinstance(value, str) and _is_fabric_context(value):
        chunks.append(value)
    return chunks


def _json_fabric_lines(key: str, value: Any) -> list[str]:
    if isinstance(value, (str, int, float)):
        return [f"{key}: {value}"]
    if isinstance(value, dict):
        text = " ".join(f"{child_key}: {child}" for child_key, child in value.items() if isinstance(child, (str, int, float)))
        return [text] if _is_fabric_context(text) else []
    if isinstance(value, list):
        return [str(item) for item in value if _is_fabric_context(str(item))]
    return []


def _extract_product_json(soup: BeautifulSoup) -> dict[str, Any]:
    for payload in _iter_embedded_json_payloads(soup):
        product = _find_product_json(payload)
        if product:
            return product
    return {}


def _find_product_json(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        type_value = value.get("@type")
        if type_value == "Product" or (isinstance(type_value, list) and "Product" in type_value):
            return value
        for child in value.values():
            found = _find_product_json(child)
            if found:
                return found
    elif isinstance(value, list):
        for item in value:
            found = _find_product_json(item)
            if found:
                return found
    return {}


def _parse_possible_json_objects(raw: str) -> Iterable[Any]:
    cleaned = html.unescape(raw).strip()
    candidates = [cleaned]

    for pattern in [
        r"window\.__INITIAL_STATE__\s*=\s*({.*?})\s*;",
        r"window\.__NUXT__\s*=\s*({.*?})\s*;",
        r"__NEXT_DATA__[^>]*>\s*({.*?})\s*</script>",
    ]:
        candidates.extend(match.group(1) for match in re.finditer(pattern, cleaned, flags=re.DOTALL))

    for candidate in candidates:
        try:
            yield json.loads(candidate)
        except json.JSONDecodeError:
            continue


def _keyword_contexts(text: str, keywords: list[str]) -> list[str]:
    cleaned = _clean_text(text)
    lower = cleaned.lower()
    contexts: list[str] = []
    for keyword in keywords:
        for match in re.finditer(re.escape(keyword.lower()), lower):
            start = max(0, match.start() - 220)
            end = min(len(cleaned), match.end() + 360)
            contexts.append(cleaned[start:end])
    return contexts


def _near_size_context(lines: list[str], index: int) -> bool:
    window = " ".join(lines[max(0, index - 3) : min(len(lines), index + 4)])
    return bool(SIZE_LABEL_PATTERN.search(window) and _is_measurement_context(window))


def _is_measurement_key(text: str) -> bool:
    normalized = text.lower().replace("_", " ")
    return any(keyword in normalized for keyword in MEASUREMENT_KEYWORDS)


def _is_measurement_context(text: str) -> bool:
    normalized = text.lower()
    return bool(CM_VALUE_PATTERN.search(normalized) or any(keyword in normalized for keyword in MEASUREMENT_KEYWORDS))


def _is_fabric_context(text: str) -> bool:
    normalized = text.lower()
    if _has_any_keyword(normalized, FIBER_KEYWORDS):
        return True
    return bool(
        ("composição" in normalized or "composicao" in normalized or "fabric" in normalized)
        and not re.search(r"material\s+de\s+(escritório|escritorio|school|office)", normalized)
    )


def _has_any_keyword(text: str, keywords: list[str]) -> bool:
    normalized = text.lower()
    return any(keyword.lower() in normalized for keyword in keywords)


def _looks_like_size_label(text: str) -> bool:
    return bool(SIZE_LABEL_PATTERN.fullmatch(_clean_text(text).lower()))


def _dedupe_lines(lines: list[str], limit: int) -> list[str]:
    cleaned: list[str] = []
    seen = set()
    for line in lines:
        normalized = _clean_text(line)
        if len(normalized) < 2:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(normalized)
        if len(cleaned) >= limit:
            break
    return cleaned


def _clean_text(value: Any) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"\\u([0-9a-fA-F]{4})", lambda match: chr(int(match.group(1), 16)), text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _absolute_protocol_url(url: str) -> str:
    if url.startswith("//"):
        return f"https:{url}"
    return url


def _log_scraper_event(event: str, **payload: Any) -> None:
    LOGGER.info(json.dumps({"event": event, **payload}, ensure_ascii=False))
