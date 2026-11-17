"""Collect Loretta's public tights/stockings listings without accounts or browser state.

Usage: python -X utf8 scripts/collect-catalog18.py [--refresh] [--no-images]
The default 24h HTTP cache makes interrupted imports resumable. --refresh refetches
HTML; cached images remain immutable by URL. An incomplete category crawl writes
only a QA candidate and report, preserving the published catalogue atomically.
Only Python's standard library is needed to parse; Pillow optimizes images.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from functools import lru_cache
from html import unescape
from html.parser import HTMLParser
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import ssl
import sys
import threading
import time
import unicodedata
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "tights-guide"
QA = ROOT / "qa/catalog18-import"
BASE = "https://xn--80ajrmkna.xn--p1ai/"
HOST = urlsplit(BASE).hostname
GROUPS = {
    "kolgotki-klassika": "Колготки классика",
    "kolgotki-fantaziya": "Колготки фантазия",
    "chulki-na-silikone": "Чулки на силиконе",
    "chulki-pod-poyas": "Чулки под пояс",
    "detskoe": "Детское",
}
CANONICAL_BRANDS = {"omsa": "OMSA", "oroblu": "Oroblù", "falke": "FALKE", "dim": "DIM"}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def clean(value):
    return re.sub(r"\s+", " ", unescape(value)).strip()


def normalized(value):
    return "".join(c for c in unicodedata.normalize("NFKD", value.casefold()) if not unicodedata.combining(c))


def slug(value):
    return re.sub(r"[^a-z0-9]+", "-", normalized(value)).strip("-")


def canonical_url(value, base=BASE):
    parts = urlsplit(urljoin(base, unescape(value)))
    # Only the public source host is allowed, including discovered next links.
    host = (parts.hostname or "").encode("idna").decode("ascii")
    if host != HOST or parts.scheme not in ("https", "http"):
        raise ValueError(f"Unexpected source URL: {value}")
    return urlunsplit(("https", HOST, parts.path.rstrip("/") or "/", parts.query, ""))


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


class Node:
    def __init__(self, tag="root", attrs=(), parent=None):
        self.tag, self.attrs, self.parent = tag, dict(attrs), parent
        self.children = []

    def has_class(self, value):
        return value in self.attrs.get("class", "").split()

    def walk(self, tag=None, cls=None, **attrs):
        for child in self.children:
            if isinstance(child, Node):
                if (tag is None or child.tag == tag) and (cls is None or child.has_class(cls)) and all(child.attrs.get(k) == v for k, v in attrs.items()):
                    yield child
                yield from child.walk(tag, cls, **attrs)

    def first(self, tag=None, cls=None, **attrs):
        return next(self.walk(tag, cls, **attrs), None)

    def text(self):
        return clean(" ".join(c.text() if isinstance(c, Node) else c for c in self.children if not isinstance(c, Node) or c.tag not in {"script", "style"}))


class TreeParser(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root = Node()
        self.stack = [self.root]
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.stack[-1])
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        self.stack[-1].children.append(data)


class PublicClient:
    def __init__(self, cache, refresh=False, offline=False, delay=0.30, tls12=False):
        self.cache, self.refresh, self.offline, self.delay = cache, refresh, offline, delay
        self.cache.mkdir(parents=True, exist_ok=True)
        self.lock, self.last_request = threading.Lock(), 0.0
        self.network_count, self.cache_count = 0, 0
        self.failures = 0
        self.context = ssl.create_default_context()
        if tls12:
            self.context.maximum_version = ssl.TLSVersion.TLSv1_2

    def get(self, url, image=False):
        url = canonical_url(url)
        key = hashlib.sha256(url.encode()).hexdigest()
        path, meta_path = self.cache / (key + ".bin"), self.cache / (key + ".json")
        if path.exists() and meta_path.exists():
            meta = json.loads(meta_path.read_text("utf-8"))
            age = time.time() - path.stat().st_mtime
            if image or self.offline or (not self.refresh and age < 86400):
                with self.lock:
                    self.cache_count += 1
                return path.read_bytes(), meta
        if self.offline:
            raise OSError(f"Not in HTTP cache: {url}")
        if self.failures >= 8:
            raise OSError("Source circuit breaker: eight consecutive requests failed; retry later")
        error = None
        for attempt in range(3):
            try:
                with self.lock:
                    wait = self.delay - (time.monotonic() - self.last_request)
                    if wait > 0:
                        time.sleep(wait)
                    self.last_request = time.monotonic()
                    self.network_count += 1
                request = Request(url, headers={
                    "User-Agent": "Mozilla/5.0 (compatible; TONKO-Public-Catalog/1.0; public catalog research)",
                    "Accept": "image/*" if image else "text/html,application/xhtml+xml",
                })
                with urlopen(request, timeout=45, context=self.context) as response:
                    final = canonical_url(response.url)
                    # Loretta's paginated HTML is cumulative: the last page can
                    # contain hundreds of cards. The bounded larger HTML limit
                    # allows one final page instead of repeatedly fetching prefixes.
                    body = response.read(15_000_001 if image else 50_000_001)
                    if len(body) > (15_000_000 if image else 50_000_000):
                        raise ValueError("Response exceeded the import safety limit")
                    if not image and b"card-item" not in body and b"/catalog/" not in body:
                        raise ValueError("Unexpected HTML: category/catalog markup is absent")
                    meta = {"url": url, "finalUrl": final, "fetchedAt": utc_now(), "contentType": response.headers.get("Content-Type", "")}
                temp = path.with_suffix(".tmp")
                temp.write_bytes(body)
                temp.replace(path)
                atomic_json(meta_path, meta)
                with self.lock:
                    self.failures = 0
                return body, meta
            except Exception as exc:
                error = exc
                if attempt < 2:
                    time.sleep(0.8 * (attempt + 1))
        with self.lock:
            self.failures += 1
        raise OSError(f"{url}: {type(error).__name__}: {error}")


def discover_categories(tree):
    categories = {}
    for anchor in tree.walk("a"):
        href = anchor.attrs.get("href", "")
        parts = urlsplit(href).path.strip("/").split("/")
        if len(parts) == 3 and parts[0] == "catalog" and parts[1] in GROUPS:
            if parts[1] == "detskoe" and parts[2] != "kolgotki":
                continue
            url = canonical_url(href)
            label = clean(anchor.text())
            if label:
                categories[url] = {"name": GROUPS[parts[1]] + " · " + label, "url": url}
    return sorted(categories.values(), key=lambda row: row["url"])


def collect_brands(tree):
    brands = set()
    for select in tree.walk("select"):
        if select.attrs.get("name") == "vendor" or select.has_class("select-brands"):
            for option in select.walk("option"):
                if option.attrs.get("value"):
                    brands.add(clean(option.text()))
    for anchor in tree.walk("a"):
        if anchor.attrs.get("href", "").startswith("/brand/") and anchor.text():
            brands.add(clean(anchor.text()))
    return brands


def price_number(node):
    if node is None:
        return None
    text = node.text()
    matches = re.findall(r"\d[\d\s\u00a0]*(?:[.,]\d{1,2})?", text)
    if len(matches) != 1:
        return None
    number = float(re.sub(r"\s", "", matches[0]).replace(",", "."))
    if number <= 0:
        return None
    return int(number) if number.is_integer() else number


def parse_listing(html, url, checked_at):
    tree = TreeParser(html).root
    count_node = tree.first(cls="head__count")
    count_match = re.search(r"Товаров\s*:\s*([\d\s]+)", count_node.text() if count_node else "")
    advertised = int(re.sub(r"\s", "", count_match.group(1))) if count_match else None
    next_node = tree.first("link", rel="next")
    next_url = canonical_url(next_node.attrs["href"], url) if next_node else None
    product_list = tree.first(cls="product-list")
    cards = list(product_list.walk(cls="card-item")) if product_list else []
    items = []
    for card in cards:
        title_node = card.first(cls="card-item__title")
        anchor = title_node.first("a") if title_node else None
        if anchor is None:
            raise ValueError(f"Unrecognized product card on {url}")
        title = anchor.text()
        source = canonical_url(anchor.attrs["href"], url)
        sku_node = card.first("input", name="tocart")
        sold_node = card.first(cls="predZak")
        sku = (sku_node.attrs.get("value") if sku_node else None) or (sold_node.attrs.get("data-hid") if sold_node else None)
        goods_node = card.first("input", name="goodsId") or card.first(cls="inWishListSet")
        goods_id = (goods_node.attrs.get("value") or goods_node.attrs.get("data-id")) if goods_node else None
        if not sku:
            sku = "url-" + hashlib.sha256(source.rsplit("/", 1)[-1].encode()).hexdigest()[:12]
        description_node = card.first(cls="card-item__text")
        description = description_node.text() if description_node else ""
        details = card.first(cls="card-details")
        detail_text = details.text() if details else ""
        density_match = re.search(r"Плотность:\s*([\d\s.,/–-]+)\s*(?:den|ден)", detail_text, re.I)
        density_text = clean(density_match.group(1)) if density_match else None
        den = int(density_text) if density_text and density_text.isdigit() and 0 < int(density_text) <= 1000 else None
        current_node = card.first(cls="card__price")
        current_price = price_number(current_node)
        old_price = price_number(card.first(cls="sale-card__price-discount"))
        if old_price is not None and current_price is not None and old_price <= current_price:
            old_price = None
        availability = "unknown"
        if "нет в наличии" in card.text().casefold():
            availability = "out_of_stock"
        elif sku_node is not None and "В КОРЗИНУ" in card.text():
            availability = "in_stock"
        image_node = card.first(cls="card-item__img")
        image_tag = image_node.first("img") if image_node else None
        image_url = canonical_url(image_tag.attrs["src"]) if image_tag and image_tag.attrs.get("src") else None
        for button in card.walk("button"):
            match = re.search(r"https?://[^\s'\"\\]+/pics/cache/985_[^\s'\"\\]+", button.attrs.get("onclick", ""))
            if match:
                image_url = canonical_url(match.group())
                break
        items.append({
            "id": "loretta-" + sku, "sku": sku, "sourceProductId": goods_id,
            "title": title, "source": source, "den": den, "densityText": density_text,
            "priceRub": current_price, "oldPriceRub": old_price,
            "priceFrom": bool(current_node and re.search(r"\bот\b", current_node.text(), re.I)),
            "availability": availability, "imageSource": image_url, "checkedAt": checked_at,
            "_description": description, "_details": detail_text,
        })
    if advertised is None or (advertised > 0 and not cards):
        raise ValueError(f"Listing markup/count missing on {url}")
    return {"items": items, "advertisedCount": advertised, "next": next_url, "brands": collect_brands(tree)}


def crawl_category(client, category):
    url, visited, records, brands, pages, errors = category["url"], set(), [], set(), [], []
    expected = None
    first_page_size, cumulative, skipped_pages = None, False, 0
    seen_ids = set()
    while url:
        if url in visited or len(visited) >= 1000:
            errors.append({"url": url, "reason": "Pagination cycle or excessive page count"})
            break
        visited.add(url)
        try:
            body, meta = client.get(url)
            result = parse_listing(body.decode("utf-8", errors="replace"), url, meta["fetchedAt"])
            if expected is None:
                expected = result["advertisedCount"]
            elif expected != result["advertisedCount"]:
                errors.append({"url": url, "reason": "Advertised count changed during pagination"})
            current_ids = {item["id"] for item in result["items"]}
            if first_page_size is None:
                first_page_size = len(current_ids)
            elif seen_ids and seen_ids.issubset(current_ids) and len(current_ids) > len(seen_ids):
                cumulative = True
            records.extend(result["items"])
            brands.update(result["brands"])
            pages.append({"url": url, "count": len(result["items"]), "checkedAt": meta["fetchedAt"]})
            seen_ids.update(current_ids)
            url = result["next"]
            # Only jump after the source has demonstrated cumulative pagination.
            # Completeness remains checked against the independently advertised
            # category count. Standard/disjoint pagination follows every next link.
            match = re.search(r"/filter/page=(\d+)$", url or "")
            if cumulative and match and first_page_size and expected:
                last_page = math.ceil(expected / first_page_size) - 1
                next_page = int(match.group(1))
                if last_page > next_page:
                    skipped_pages += last_page - next_page
                    url = re.sub(r"page=\d+$", f"page={last_page}", url)
        except Exception as exc:
            errors.append({"url": url, "reason": str(exc)})
            break
    unique = {item["id"] for item in records}
    if expected is not None and len(unique) != expected:
        errors.append({"url": category["url"], "reason": f"Coverage mismatch: expected {expected}, collected {len(unique)} unique products"})
    summary = {**category, "advertisedCount": expected, "collectedCount": len(unique), "cardCount": len(records), "pages": pages, "paginationMode": "cumulative" if cumulative else "standard", "redundantIntermediatePagesSkipped": skipped_pages, "complete": not errors, "errors": errors}
    return summary, records, brands


def split_brand(title, source, brands):
    for brand in sorted(brands, key=lambda name: len(name), reverse=True):
        if normalized(title).startswith(normalized(brand) + " "):
            canonical = CANONICAL_BRANDS.get(slug(brand), brand)
            return canonical, title[len(brand):].strip()
    # URL prefixes are supplied by the shop (brand_model); only accept an exact
    # normalized prefix of the visible title, never a fabricated brand label.
    prefix = source.rsplit("/", 1)[-1].split("_", 1)[0]
    words = title.split()
    for i in range(1, len(words)):
        name = " ".join(words[:i])
        if slug(name) == prefix:
            return CANONICAL_BRANDS.get(slug(name), name), " ".join(words[i:])
    return "", title


def classify(record):
    text = record["_description"].casefold()
    title = record["title"].casefold()
    categories = " ".join(cat["url"] for cat in record["categories"])
    # Mixed listings include accessories, leggings and other hosiery. The source
    # description takes priority over the menu name.
    if re.search(r"\bаксессуар", text):
        kind = "аксессуар"
    elif re.search(r"\bкомбинезон", text) or "/kombinezony" in categories:
        kind = "комбинезон"
    elif re.search(r"\b(?:колготк|колготы)", text):
        kind = "колготки"
    elif re.search(r"\bчул[окк]", text):
        kind = "чулки"
    elif re.search(r"\b(?:леггинс|легинс|лосин|гольф|нос[окк]|брюк|капри)", text) or re.search(r"\b(?:leggings|gambaletto|calzino)\b", title):
        return None, "unrelated product type"
    elif "/chulki-" in categories:
        kind = "чулки"
    elif "/kolgotki-" in categories or "/detskoe/kolgotki" in categories:
        kind = "колготки"
    else:
        return None, "unrecognized product type"
    if "/detskoe/" in categories or re.search(r"\bдетск", text):
        gender = "kids"
    elif re.search(r"\bунисекс\b", text):
        gender = "unisex"
    elif "/muzhskie-kolgotki" in categories or re.search(r"\bмужск", text):
        gender = "men"
    elif re.search(r"\bженск", text):
        gender = "women"
    else:
        gender = "unknown"
    # Conservative image policy for potentially explicit photos. No guesses
    # about image content are made, and textual product records remain included.
    image_review = kind in {"аксессуар", "комбинезон"} or bool(re.search(r"\bэротич|открыт\w* (?:шаг|промеж|пах|ластов)|без ластовицы|вырез\w* (?:на|в) (?:пах|промеж)|доступом", text))
    return {"productKind": kind, "gender": gender, "imageNeedsReview": image_review}, None


def merge_records(results, brands):
    merged, by_product, by_slug, conflicts = {}, {}, {}, []
    for category, records, _ in sorted(results, key=lambda result: result[0]["url"]):
        for raw in records:
            product_key = raw.get("sourceProductId")
            url_key = raw["source"].rsplit("/", 1)[-1]
            key = by_product.get(product_key) if product_key else None
            key = key or by_slug.get(url_key) or raw["id"]
            category_ref = {"name": category["name"], "url": category["url"]}
            if key in merged:
                old = merged[key]
                if category_ref not in old["categories"]:
                    old["categories"].append(category_ref)
                for field in ("priceRub", "oldPriceRub", "availability"):
                    if old[field] != raw[field]:
                        conflicts.append({"id": key, "field": field, "values": [old[field], raw[field]], "sources": [old["source"], raw["source"]]})
                if raw["checkedAt"] > old["checkedAt"]:
                    preserved_categories = old["categories"]
                    old.update(raw)
                    old["id"] = key
                    old["categories"] = preserved_categories
            else:
                merged[key] = {**raw, "id": key, "categories": [category_ref]}
            if product_key:
                by_product[product_key] = key
            by_slug[url_key] = key
    items, excluded, unknown_brands = [], [], []
    for record in merged.values():
        classification, reason = classify(record)
        if classification is None:
            excluded.append({"id": record["id"], "title": record["title"], "source": record["source"], "reason": reason})
            continue
        brand, model = split_brand(record["title"], record["source"], brands)
        if not brand:
            unknown_brands.append({"id": record["id"], "title": record["title"], "source": record["source"]})
        record.update(classification)
        record.update({"brand": brand or "Не указан", "brandSlug": slug(brand) or "unknown", "model": model, "priceCurrency": "RUB", "sourceName": "Лоретта", "image": None, "thumbnail": None, "width": 0, "height": 0, "photos": [], "packageId": None})
        facts = [record["productKind"].capitalize()]
        if record["den"]:
            facts.append(f"{record['den']} DEN")
        if record["gender"] in {"men", "kids", "unisex", "women"}:
            facts.append({"men": "мужская модель", "kids": "детская модель", "unisex": "унисекс", "women": "женская модель"}[record["gender"]])
        record["description"] = "; ".join(facts) + "."
        del record["_description"], record["_details"]
        items.append(record)
    return sorted(items, key=lambda row: (row["brand"].casefold(), row["model"].casefold(), row["id"])), excluded, conflicts, unknown_brands


@lru_cache(maxsize=1)
def pillow_runtime():
    for runtime in (os.environ.get("TONKO_PILLOW_RUNTIME", ""), str(ROOT / ".cache/pillow-runtime"), str(Path.home() / "Documents/CODEX_сайт_ТОНКО/.cache/pillow-runtime")):
        if runtime and Path(runtime).is_dir():
            sys.path.insert(0, runtime)
    from PIL import Image, ImageOps
    Image.MAX_IMAGE_PIXELS = 25_000_000
    return Image, ImageOps


def optimize_image(client, item):
    if not item["imageSource"] or item["imageNeedsReview"]:
        return item, None
    path = SITE / "assets/catalog" / (item["id"] + ".webp")
    thumb = path.with_name(item["id"] + "-320.webp")
    Image, ImageOps = pillow_runtime()
    try:
        if path.exists() and thumb.exists():
            with Image.open(path) as existing:
                width, height = existing.size
        else:
            body, meta = client.get(item["imageSource"], image=True)
            with Image.open(io.BytesIO(body)) as opened:
                opened.load()
                image = ImageOps.exif_transpose(opened).convert("RGB")
                image.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
                width, height = image.size
                path.parent.mkdir(parents=True, exist_ok=True)
                image.save(path, "WEBP", quality=83, method=4)
                image.thumbnail((320, 320), Image.Resampling.LANCZOS)
                image.save(thumb, "WEBP", quality=80, method=4)
        item.update({"image": path.relative_to(SITE).as_posix(), "thumbnail": thumb.relative_to(SITE).as_posix(), "width": width, "height": height})
        return item, None
    except Exception as exc:
        return item, {"id": item["id"], "url": item["imageSource"], "reason": str(exc)}


def catalog_is_recent(data, max_age_hours=24):
    if not data.get("coverage", {}).get("complete") or not data.get("items"):
        return False
    try:
        checked = datetime.fromisoformat(data["checkedAt"].replace("Z", "+00:00"))
        age = (datetime.now(timezone.utc) - checked).total_seconds()
        return 0 <= age < max_age_hours * 3600
    except (KeyError, ValueError, TypeError):
        return False


def restore_deployed(base_url, target):
    """Restore last published data and missing assets before source refresh.

    base_url is the HTTPS tights-guide/ directory, supplied by the caller. Only
    catalogue asset paths are accepted. A partial restore cannot replace JSON.
    """
    parts = urlsplit(base_url)
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment:
        raise ValueError("--deployed requires an HTTPS base URL without credentials/query")
    base_url = base_url.rstrip("/") + "/"

    def read(relative):
        request = Request(urljoin(base_url, relative), headers={"User-Agent": "TONKO-Catalog-Refresh/1.0", "Cache-Control": "no-cache"})
        with urlopen(request, timeout=40) as response:
            if urlsplit(response.url).hostname != parts.hostname:
                raise ValueError("Deployment restore redirected to another host")
            payload = response.read(15_000_001)
            if len(payload) > 15_000_000:
                raise ValueError("Deployment asset exceeds 15 MB")
            return payload

    remote = json.loads(read("data/catalog.json").decode("utf-8-sig"))
    if remote.get("version") != 1 or remote.get("source", {}).get("id") != "loretta" or not isinstance(remote.get("items"), list) or not remote.get("coverage", {}).get("complete"):
        raise ValueError("Deployment catalogue is not a complete Loretta v1 snapshot")
    if target.exists():
        local = json.loads(target.read_text("utf-8-sig"))
        if local.get("checkedAt", "") > remote.get("checkedAt", "") and local.get("coverage", {}).get("complete"):
            remote = local
    missing = set()
    for item in remote["items"]:
        for key in ("image", "thumbnail"):
            relative = item.get(key)
            if relative is None:
                continue
            if not re.fullmatch(r"assets/catalog/[a-zA-Z0-9_-]+\.webp", relative):
                raise ValueError(f"Unrecognized deployment asset path: {relative}")
            if not (SITE / relative).is_file():
                missing.add(relative)
    for relative in sorted(missing):
        body = read(relative)
        if not body.startswith(b"RIFF") or body[8:12] != b"WEBP":
            raise ValueError(f"Deployment asset is not WebP: {relative}")
        path = SITE / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
    atomic_json(target, remote)
    return remote, len(missing)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Fetch HTML again; preserve old published data if any category fails")
    parser.add_argument("--offline", action="store_true", help="Reparse only the saved HTTP cache")
    parser.add_argument("--resume", action="store_true", help="Reparse cached pages and finish images even when the current snapshot is younger than 24h")
    parser.add_argument("--no-images", action="store_true", help="Collect full listing data without fetching/optimizing images")
    parser.add_argument("--deployed", metavar="HTTPS_URL", help="Restore published data and missing assets from the HTTPS tights-guide/ base directory")
    parser.add_argument("--tls12", action="store_true", help="Limit TLS to 1.2 for incompatible local transports; certificates are still verified")
    parser.add_argument("--workers", type=int, default=4, choices=range(1, 5))
    parser.add_argument("--cache", type=Path, default=QA / "http-cache")
    args = parser.parse_args(argv)
    QA.mkdir(parents=True, exist_ok=True)
    started = utc_now()
    old_catalog_path = SITE / "data/catalog.json"
    if args.deployed:
        try:
            _, restored_assets = restore_deployed(args.deployed, old_catalog_path)
            print(f"Restored deployed catalogue; fetched {restored_assets} missing assets", flush=True)
        except Exception as exc:
            atomic_json(QA / "restore-error.json", {"checkedAt": started, "url": args.deployed, "error": str(exc)})
            print(f"Deployment restore failed; published data left untouched: {exc}", flush=True)
            return 2
    if old_catalog_path.exists() and not (args.refresh or args.resume or args.offline):
        previous_data = json.loads(old_catalog_path.read_text("utf-8-sig"))
        if catalog_is_recent(previous_data):
            print(f"Complete catalogue already checked at {previous_data['checkedAt']}; daily refresh skipped", flush=True)
            return 0
    client = PublicClient(args.cache, refresh=args.refresh, offline=args.offline, tls12=args.tls12)
    report = {"startedAt": started, "source": BASE, "failedUrls": []}
    try:
        body, meta = client.get(BASE)
        tree = TreeParser(body.decode("utf-8", errors="replace")).root
        categories, brands = discover_categories(tree), collect_brands(tree)
        if len(categories) < 40:
            raise ValueError(f"Menu discovery found only {len(categories)} categories; refusing a partial import")
    except Exception as exc:
        report.update({"complete": False, "failedUrls": [{"url": BASE, "reason": str(exc)}]})
        atomic_json(QA / "coverage-report.json", report)
        print(str(exc), flush=True)
        return 2
    print(f"Discovered {len(categories)} categories", flush=True)
    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(crawl_category, client, cat): cat for cat in categories}
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            summary, _, found_brands = result
            brands.update(found_brands)
            print(f"[{len(results)}/{len(categories)}] {summary['name']}: {summary['collectedCount']}/{summary['advertisedCount']}, {len(summary['pages'])} pages, {'OK' if summary['complete'] else 'INCOMPLETE'}", flush=True)
            atomic_json(QA / "crawl-progress.json", {"startedAt": started, "completedCategories": [row[0] for row in results]})
    packaging_file = SITE / "data/packaging.json"
    if packaging_file.exists():
        brands.update(item["brand"] for item in json.loads(packaging_file.read_text("utf-8-sig")))
    items, excluded, conflicts, unknown_brands = merge_records(results, brands)
    image_errors = []
    previous = {}
    if old_catalog_path.exists():
        previous = {row["id"]: row for row in json.loads(old_catalog_path.read_text("utf-8-sig")).get("items", [])}
    for item in items:
        if item["id"] in previous:
            item["packageId"] = previous[item["id"]].get("packageId")
    if not args.no_images:
        pillow_runtime()
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = [executor.submit(optimize_image, client, item) for item in items]
            for done, future in enumerate(as_completed(futures), 1):
                _, error = future.result()
                if error:
                    image_errors.append(error)
                if done % 100 == 0 or done == len(items):
                    print(f"Images {done}/{len(items)}, failures {len(image_errors)}", flush=True)
    else:
        # A data-only refresh retains already optimized, same-source photos.
        for item in items:
            old = previous.get(item["id"], {})
            if old.get("imageSource") == item["imageSource"] and not item["imageNeedsReview"]:
                for key in ("image", "thumbnail", "width", "height", "photos"):
                    if key in old:
                        item[key] = old[key]
    summaries = sorted([row[0] for row in results], key=lambda row: row["url"])
    failed = [error for cat in summaries for error in cat["errors"]]
    complete = not failed and not unknown_brands
    coverage = {
        "complete": complete, "categories": len(categories), "categoriesComplete": sum(cat["complete"] for cat in summaries),
        "pages": sum(len(cat["pages"]) for cat in summaries), "listedOccurrences": sum(cat["cardCount"] for cat in summaries),
        "uniqueProducts": len(items), "excludedUnrelatedProducts": len(excluded),
        "images": sum(bool(item["image"]) for item in items), "imageFailures": len(image_errors),
        "imagesAwaitingReview": sum(item["imageNeedsReview"] for item in items),
        "byKind": dict(sorted(Counter(item["productKind"] for item in items).items())),
        "byBrand": dict(sorted(Counter(item["brand"] for item in items).items())),
        "byAvailability": dict(sorted(Counter(item["availability"] for item in items).items())),
        "pricesAvailable": sum(item["priceRub"] is not None for item in items),
        "scope": "Все публичные подкатегории колготок классика, колготок фантазия, детских колготок, чулок на силиконе и чулок под пояс из меню Лоретты. Остальные группы не входят в охват.",
    }
    # Reprocessing cached images must not make old prices appear newly checked.
    checked_at = max((page["checkedAt"] for category in summaries for page in category["pages"]), default=started)
    output = {"version": 1, "source": {"id": "loretta", "name": "Лоретта", "url": BASE}, "checkedAt": checked_at, "coverage": coverage, "items": items}
    atomic_json(QA / "catalog-candidate.json", output)
    report.update({"finishedAt": utc_now(), **coverage, "categoryDetails": summaries, "failedUrls": failed, "imageErrors": image_errors, "excludedProducts": excluded, "conflicts": conflicts, "unknownBrands": unknown_brands, "networkRequests": client.network_count, "cacheHits": client.cache_count, "published": complete})
    atomic_json(QA / "coverage-report.json", report)
    if complete:
        atomic_json(old_catalog_path, output)
        print(f"Published {len(items)} unique products, {coverage['images']} images", flush=True)
    else:
        print(f"NOT PUBLISHED: {len(failed)} category errors, {len(unknown_brands)} unresolved brands. Previous published catalogue preserved.", flush=True)
    return 0 if complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
