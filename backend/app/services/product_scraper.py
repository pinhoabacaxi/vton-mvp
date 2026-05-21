import httpx
from bs4 import BeautifulSoup
from urllib.parse import unquote, urlparse
from app.models.product import ProductScrapeResult
from app.services.size_normalizer import normalize_size_text


async def scrape_product_page(url: str) -> ProductScrapeResult:
    """
    Scraper básico e conservador para MVP.

    Não faz bypass.
    Não faz login.
    Não ignora bloqueios.
    Não executa automação agressiva.
    Apenas tenta extrair metadados públicos simples.
    """
    parsed = urlparse(url)

    if not parsed.scheme.startswith("http"):
        raise ValueError("URL inválida.")

    headers = {
        "User-Agent": "Mozilla/5.0 VTON-MVP/0.1",
        "Accept": "text/html,application/xhtml+xml",
    }

    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    title = _extract_title(soup)
    if _is_generic_store_title(title):
        title = _title_from_product_slug(url)

    image_url = _extract_image(soup)
    price = _extract_price(soup)
    raw_size_text = _extract_possible_size_text(soup)
    normalized = normalize_size_text(raw_size_text or "")

    return ProductScrapeResult(
        source_url=url,
        title=title or "Produto sem título detectado",
        image_url=image_url,
        currency=None,
        price=price,
        raw_size_text=raw_size_text,
        normalized_sizes=normalized,
    )


def _extract_title(soup: BeautifulSoup) -> str | None:
    og_title = soup.find("meta", property="og:title")

    if og_title and og_title.get("content"):
        return og_title["content"].strip()

    if soup.title and soup.title.string:
        return soup.title.string.strip()

    h1 = soup.find("h1")

    if h1:
        return h1.get_text(" ", strip=True)

    return None


def _is_generic_store_title(title: str | None) -> bool:
    if not title:
        return True

    normalized = title.lower()

    generic_fragments = [
        "loja de moda online",
        "roupas femininas",
        "roupas masculinas",
        "online fashion",
        "shein",
    ]

    return any(fragment in normalized for fragment in generic_fragments)


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
    og_image = soup.find("meta", property="og:image")

    if og_image and og_image.get("content"):
        return og_image["content"].strip()

    image = soup.find("img")

    if image and image.get("src"):
        return image["src"].strip()

    return None


def _extract_price(soup: BeautifulSoup) -> str | None:
    candidates = []

    for attr in ["price", "product:price:amount"]:
        meta = soup.find("meta", property=attr) or soup.find("meta", attrs={"name": attr})
        if meta and meta.get("content"):
            candidates.append(meta["content"].strip())

    text = soup.get_text(" ", strip=True)

    import re

    price_match = re.search(r"(R\$|US\$|\$|€|£)\s?\d+[,.]?\d*", text)

    if price_match:
        candidates.append(price_match.group(0))

    return candidates[0] if candidates else None


def _extract_possible_size_text(soup: BeautifulSoup) -> str | None:
    keywords = [
        "tamanho",
        "medidas",
        "size",
        "size guide",
        "size chart",
        "busto",
        "cintura",
        "quadril",
        "chest",
        "waist",
        "hip",
    ]

    chunks = []

    for table in soup.find_all("table"):
        text = table.get_text("\n", strip=True)
        lower = text.lower()

        if any(keyword in lower for keyword in keywords):
            chunks.append(text)

    if chunks:
        return "\n".join(chunks)

    text = soup.get_text("\n", strip=True)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    possible_lines = [
        line for line in lines
        if any(keyword in line.lower() for keyword in keywords)
    ]

    return "\n".join(possible_lines[:30]) if possible_lines else None
