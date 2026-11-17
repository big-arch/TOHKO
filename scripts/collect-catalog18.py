"""Collect Loretta's public tights/stockings listings without accounts or browser state.

Usage: python -X utf8 scripts/collect-catalog18.py [--refresh] [--no-images]
The default 24h HTTP cache makes interrupted imports resumable. --refresh refetches
HTML; cached images remain immutable by URL. An incomplete category crawl writes
only a QA candidate and report, preserving the published catalogue atomically.
Only Python's standard library is needed to parse; Pillow optimizes images.
"""
from __future__ import annotations

import argparse
import codecs
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
import shutil
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import unicodedata
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.error import HTTPError
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
# Explicit visual review, independent of product metadata/price collection.
# Keep these product records; never substitute a different model's photograph.
SOURCE_IMAGE_EXCLUSIONS = {
    BASE + "pics/cache/985_v_1267492.jpg": "Visual review: explicit full-body sheer photograph with a genital censor mark; unsuitable for this catalogue's product photography.",
}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def clean(value):
    return re.sub(r"\s+", " ", unescape(value)).strip()


def decode_html(body, content_type=""):
    """Decode declared HTML strictly; never publish replacement characters.

    Both UTF-8 and Windows-1251 are supported. Prefer an actual BOM,
    otherwise require consistent HTTP/meta declarations. Undeclared legacy
    pages are tried as UTF-8 then Windows-1251, without lossy replacements.
    """
    if body.startswith(codecs.BOM_UTF8):
        text = body.decode("utf-8-sig", errors="strict")
    else:
        header = re.search(r"charset\s*=\s*[\"']?([^\s;\"']+)", content_type, re.I)
        meta = re.search(rb"<meta\b[^>]*charset\s*=\s*[\"']?\s*([A-Za-z0-9._-]+)", body[:8192], re.I)
        declarations = []
        for encoding in (header.group(1) if header else None, meta.group(1).decode("ascii") if meta else None):
            if encoding:
                try:
                    declarations.append(codecs.lookup(encoding).name)
                except LookupError as exc:
                    raise UnicodeError(f"Unknown declared HTML charset: {encoding}") from exc
        if len(set(declarations)) > 1:
            raise UnicodeError(f"Conflicting HTTP/meta charsets: {declarations}")
        if declarations:
            text = body.decode(declarations[0], errors="strict")
        else:
            try:
                text = body.decode("utf-8", errors="strict")
            except UnicodeDecodeError:
                text = body.decode("windows-1251", errors="strict")
    if "\ufffd" in text:
        raise UnicodeError("Replacement characters in source HTML; refusing damaged text")
    return text


def normalized(value):
    return "".join(c for c in unicodedata.normalize("NFKD", value.casefold()) if not unicodedata.combining(c))


def slug(value):
    return re.sub(r"[^a-z0-9]+", "-", normalized(value)).strip("-")


def brand_slug(brand, source):
    if not brand:
        return "unknown"
    value = slug(brand)
    if value:
        return value
    # Cyrillic brands already have the shop's ASCII URL prefix (Интекс/inteks,
    # ХОХ/hoh). Do not merge distinct named brands under one 'unknown' slug.
    prefix = source.rsplit("/", 1)[-1].split("_", 1)[0]
    return prefix if re.fullmatch(r"[a-z0-9][a-z0-9-]*", prefix) else "brand-" + hashlib.sha256(brand.encode()).hexdigest()[:12]


def apply_image_review(item):
    reason = SOURCE_IMAGE_EXCLUSIONS.get(item.get("imageSource"))
    if reason:
        item.update({"imageNeedsReview": True, "imageReviewReason": reason, "image": None, "thumbnail": None, "width": 0, "height": 0, "photos": []})
    return item


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
    def __init__(self, cache, refresh=False, offline=False, delay=0.30, tls12=False, transport="urllib"):
        self.cache, self.refresh, self.offline, self.delay = cache, refresh, offline, delay
        self.cache.mkdir(parents=True, exist_ok=True)
        self.lock, self.last_request = threading.Lock(), 0.0
        self.network_count, self.cache_count = 0, 0
        self.failures = 0
        self.transport, self.tls12 = transport, tls12
        self.curl = shutil.which("curl.exe" if os.name == "nt" else "curl") if transport == "curl" else None
        if transport == "curl" and not self.curl:
            raise OSError("--transport curl requested but curl is not installed")
        self.context = ssl.create_default_context()
        if tls12:
            self.context.maximum_version = ssl.TLSVersion.TLSv1_2

    def curl_get(self, url, image=False):
        limit = 15_000_000 if image else 50_000_000
        descriptor, filename = tempfile.mkstemp(prefix="http-", suffix=".download", dir=self.cache)
        os.close(descriptor)
        path = Path(filename)
        try:
            # Disable implicit curlrc options so TLS checks/output limits cannot
            # silently be weakened by unrelated local command-line preferences.
            command = [self.curl, "--disable", "--silent", "--show-error", "--location", "--max-redirs", "5", "--proto", "=https", "--proto-redir", "=https", "--connect-timeout", "15", "--max-time", "45", "--max-filesize", str(limit), "--user-agent", "Mozilla/5.0 (compatible; TONKO-Public-Catalog/1.0; public catalog research)", "--header", "Accept: " + ("image/*" if image else "text/html,application/xhtml+xml"), "--output", str(path), "--write-out", "%{json}"]
            if self.tls12:
                command.extend(["--tls-max", "1.2"])
            command.append(url)
            completed = subprocess.run(command, capture_output=True, text=True, timeout=45, shell=False)
            if completed.returncode:
                raise OSError(f"curl exit {completed.returncode}: {completed.stderr.strip()[:600]}")
            metadata = json.loads(completed.stdout)
            if int(metadata.get("http_code", 0)) != 200:
                raise OSError(f"curl HTTP status {metadata.get('http_code')}")
            final = canonical_url(metadata.get("url_effective") or url)
            if path.stat().st_size > limit:
                raise ValueError("Response exceeded the import safety limit")
            body = path.read_bytes()
            return body, {"url": url, "finalUrl": final, "fetchedAt": utc_now(), "contentType": metadata.get("content_type") or "", "transport": "curl", "requestSeconds": metadata.get("time_total"), "bytes": len(body)}
        finally:
            path.unlink(missing_ok=True)

    def get(self, url, image=False, force_refresh=False):
        url = canonical_url(url)
        key = hashlib.sha256(url.encode()).hexdigest()
        path, meta_path = self.cache / (key + ".bin"), self.cache / (key + ".json")
        if path.exists() and meta_path.exists():
            meta = json.loads(meta_path.read_text("utf-8"))
            age = time.time() - path.stat().st_mtime
            if self.offline or (not force_refresh and (image or (not self.refresh and age < 86400))):
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
                if self.transport == "curl":
                    body, meta = self.curl_get(url, image=image)
                else:
                    request = Request(url, headers={
                        "User-Agent": "Mozilla/5.0 (compatible; TONKO-Public-Catalog/1.0; public catalog research)",
                        "Accept": "image/*" if image else "text/html,application/xhtml+xml",
                    })
                    request_started = time.monotonic()
                    with urlopen(request, timeout=45, context=self.context) as response:
                        final = canonical_url(response.url)
                        # Last cumulative pages can contain hundreds of cards.
                        body = response.read(15_000_001 if image else 50_000_001)
                        meta = {"url": url, "finalUrl": final, "fetchedAt": utc_now(), "contentType": response.headers.get("Content-Type", ""), "transport": "urllib", "requestSeconds": round(time.monotonic() - request_started, 4), "bytes": len(body)}
                if len(body) > (15_000_000 if image else 50_000_000):
                    raise ValueError("Response exceeded the import safety limit")
                if not image and b"card-item" not in body and b"/catalog/" not in body:
                    raise ValueError("Unexpected HTML: category/catalog markup is absent")
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
    # Parent URLs are real aggregate product listings, and can contain products
    # not assigned to any visible child category. Children's other goods remain
    # excluded: only the dedicated children's tights subcategory is in scope.
    categories = {
        canonical_url(f"catalog/{group}"): {"name": label + " · все модели", "url": canonical_url(f"catalog/{group}"), "scopeLevel": "parent"}
        for group, label in GROUPS.items() if group != "detskoe"
    }
    for anchor in tree.walk("a"):
        href = anchor.attrs.get("href", "")
        parts = urlsplit(href).path.strip("/").split("/")
        if len(parts) == 3 and parts[0] == "catalog" and parts[1] in GROUPS:
            if parts[1] == "detskoe" and parts[2] != "kolgotki":
                continue
            url = canonical_url(href)
            label = clean(anchor.text())
            if label:
                categories[url] = {"name": GROUPS[parts[1]] + " · " + label, "url": url, "scopeLevel": "subcategory"}
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
        if sku and not re.fullmatch(r"[0-9]+", sku):
            raise ValueError(f"Invalid source SKU on {url}")
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


def crawl_category_once(client, category, force_refresh=False):
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
            body, meta = client.get(url, force_refresh=True) if force_refresh else client.get(url)
            result = parse_listing(decode_html(body, meta.get("contentType", "")), url, meta["fetchedAt"])
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


def crawl_category(client, category):
    first = crawl_category_once(client, category)
    summary = first[0]
    changed_during_crawl = any(error["reason"] == "Advertised count changed during pagination" for error in summary["errors"])
    if changed_during_crawl and not getattr(client, "offline", False):
        # Inventory may change while the last cumulative page is being fetched.
        # Retry only this category once, bypassing its cached HTML throughout.
        # A second mismatch still fails; no count discrepancy is waived.
        second = crawl_category_once(client, category, force_refresh=True)
        second[0]["freshRetry"] = {"attempted": True, "reason": "Advertised count changed during pagination", "previousAdvertisedCount": summary["advertisedCount"], "previousCollectedCount": summary["collectedCount"], "previousErrors": summary["errors"], "previousPages": summary["pages"], "succeeded": second[0]["complete"]}
        return second
    return first


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
        record.update({"brand": brand or "Не указан", "brandSlug": brand_slug(brand, record["source"]), "model": model, "priceCurrency": "RUB", "sourceName": "Лоретта", "image": None, "thumbnail": None, "width": 0, "height": 0, "photos": [], "packageId": None})
        apply_image_review(record)
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


def existing_image_size(path, thumb, Image):
    try:
        with Image.open(path) as main_image, Image.open(thumb) as thumbnail:
            main_image.load()
            thumbnail.load()
            if main_image.format != "WEBP" or thumbnail.format != "WEBP" or max(main_image.size) > 1200 or max(thumbnail.size) > 320:
                return None
            return main_image.size
    except (OSError, ValueError):
        return None


def optimize_image(client, item, previous=None):
    apply_image_review(item)
    if not item["imageSource"] or item["imageNeedsReview"]:
        return item, None
    if not re.fullmatch(r"loretta-(?:[0-9]+|url-[a-f0-9]{12})", item["id"]):
        return item, {"id": item["id"], "url": item["imageSource"], "reason": "Invalid catalogue image ID"}
    # A photo changed at the source must not reuse an old same-product filename.
    # URL hashing keeps old deployed snapshots internally consistent too.
    image_key = hashlib.sha256(item["imageSource"].encode()).hexdigest()[:12]
    path = SITE / "assets/catalog" / (item["id"] + "-" + image_key + ".webp")
    thumb = path.with_name(path.stem + "-320.webp")
    Image, ImageOps = pillow_runtime()
    try:
        old = previous or {}
        size = None
        if old.get("imageSource") == item["imageSource"] and all(re.fullmatch(r"assets/catalog/[a-zA-Z0-9_-]+\.webp", old.get(key) or "") for key in ("image", "thumbnail")):
            old_path, old_thumb = SITE / old["image"], SITE / old["thumbnail"]
            size = existing_image_size(old_path, old_thumb, Image)
            if size:
                path, thumb = old_path, old_thumb
        if size is None:
            size = existing_image_size(path, thumb, Image)
        if size:
            width, height = size
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


class DeploymentCatalogNotFound(OSError):
    """Only the deployed catalogue JSON returned HTTP 404 (not an asset)."""


def valid_webp_file(path):
    try:
        with path.open("rb") as image_file:
            header = image_file.read(12)
        return len(header) == 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP" and int.from_bytes(header[4:8], "little") + 8 == path.stat().st_size
    except OSError:
        return False


def bind_initial_images(items, manifest_path):
    """One-time, explicit adoption of the first CI run's provenance-bound files.

    This is deliberately separate from ordinary refresh behavior. The approved
    manifest identifies immutable local bytes from the original import. A fresh
    listing must confirm the same SKU and the shop's product-linked image URL.
    The resolved evidence remains in QA; daily refresh never enables this flag.
    """
    manifest = json.loads(manifest_path.read_text("utf-8-sig"))
    provenance = manifest.get("provenance", {})
    if manifest.get("version") != 1 or manifest.get("purpose") != "one-time-initial-ci-image-adoption" or provenance.get("githubRunId") != "44085884185" or not re.fullmatch(r"6fffdb4[a-f0-9]{0,33}", provenance.get("gitCommit", "")):
        raise ValueError("The initial-image manifest is not the approved first-import provenance")
    by_id = {item["id"]: item for item in items}
    previous, accepted, rejected = {}, [], []
    seen = set()
    Image, _ = pillow_runtime()
    for entry in manifest.get("items", []):
        item_id = entry.get("id", "")
        try:
            if item_id in seen or not re.fullmatch(r"loretta-[0-9]+", item_id):
                raise ValueError("Invalid or duplicated manifest SKU")
            seen.add(item_id)
            item = by_id.get(item_id)
            if item is None:
                raise ValueError("SKU not present in the newly collected in-scope listings")
            if item["imageNeedsReview"]:
                raise ValueError("Product photograph currently requires visual review")
            image_source = item.get("imageSource")
            product_id = item.get("sourceProductId")
            if not image_source or not product_id or not str(product_id).isdigit():
                raise ValueError("New listing does not provide a verifiable source image/product ID")
            image_url = canonical_url(image_source)
            if urlsplit(image_url).path not in (f"/pics/cache/985_v_{product_id}.jpg", f"/pics/cache/378_v_{product_id}.jpg"):
                raise ValueError("Image URL does not match the new listing's product identifier")
            if entry.get("image") != f"assets/catalog/{item_id}.webp" or entry.get("thumbnail") != f"assets/catalog/{item_id}-320.webp":
                raise ValueError("Manifest does not refer to first-run legacy filenames")
            for key, hash_key in (("image", "sha256"), ("thumbnail", "thumbnailSha256")):
                path = SITE / entry[key]
                if not valid_webp_file(path) or hashlib.sha256(path.read_bytes()).hexdigest() != entry.get(hash_key):
                    raise ValueError(f"First-run {key} is missing, damaged or changed")
            size = existing_image_size(SITE / entry["image"], SITE / entry["thumbnail"], Image)
            if not size or list(size) != [entry.get("width"), entry.get("height")]:
                raise ValueError("First-run image dimensions do not match the manifest")
            adopted = {"imageSource": image_source, "image": entry["image"], "thumbnail": entry["thumbnail"], "width": size[0], "height": size[1], "photos": []}
            previous[item_id] = adopted
            accepted.append({**entry, "brand": item["brand"], "model": item["model"], "source": item["source"], "imageSource": image_source, "sourceProductId": product_id, "listingCheckedAt": item["checkedAt"], "evidence": "First CI asset hash and SKU match; current public listing confirms product ID and source image URL. The original CI did not retain its URL manifest; this is an explicit one-time provenance binding, not a byte comparison with a new image download."})
        except (ValueError, OSError, KeyError) as exc:
            rejected.append({"id": item_id, "reason": str(exc)})
    atomic_json(QA / "initial-images-resolved.json", {"version": 1, "resolvedAt": utc_now(), "provenance": provenance, "acceptedCount": len(accepted), "rejectedCount": len(rejected), "items": accepted, "rejected": rejected})
    return previous


def validate_complete_snapshot(data, require_local_assets=False):
    if data.get("version") != 1 or data.get("source", {}).get("id") != "loretta" or not isinstance(data.get("items"), list) or not data["items"] or not data.get("coverage", {}).get("complete"):
        raise ValueError("Not a complete Loretta v1 snapshot")
    stamp = datetime.fromisoformat(data["checkedAt"].replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("Snapshot timestamp needs a timezone")
    if data["coverage"].get("uniqueProducts") != len(data["items"]):
        raise ValueError("Snapshot item count does not match coverage")
    seen = set()
    for item in data["items"]:
        if not re.fullmatch(r"loretta-(?:[0-9]+|url-[a-f0-9]{12})", item.get("id", "")) or item["id"] in seen:
            raise ValueError("Invalid or duplicated snapshot item ID")
        seen.add(item["id"])
        if not item.get("title") or not item.get("brand"):
            raise ValueError("Snapshot item title/brand is missing")
        canonical_url(item["source"])
        if item.get("priceCurrency", "RUB") != "RUB":
            raise ValueError("Unexpected snapshot price currency")
        for key in ("priceRub", "oldPriceRub"):
            value = item.get(key)
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0):
                raise ValueError("Invalid snapshot price")
        for key in ("image", "thumbnail"):
            relative = item.get(key)
            if relative is None:
                continue
            if not re.fullmatch(r"assets/catalog/[a-zA-Z0-9_-]+\.webp", relative):
                raise ValueError(f"Unrecognized deployment asset path: {relative}")
            if require_local_assets and not (SITE / relative).is_file():
                raise ValueError(f"Repository seed image is missing: {relative}")
            if require_local_assets:
                if not valid_webp_file(SITE / relative):
                    raise ValueError(f"Repository seed image has an invalid WebP container: {relative}")


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

    try:
        remote = json.loads(read("data/catalog.json").decode("utf-8-sig"))
    except HTTPError as exc:
        if exc.code == 404:
            raise DeploymentCatalogNotFound("Deployed data/catalog.json returned HTTP 404") from exc
        raise
    validate_complete_snapshot(remote)
    if target.exists():
        local = json.loads(target.read_text("utf-8-sig"))
        if local.get("checkedAt", "") > remote.get("checkedAt", "") and local.get("coverage", {}).get("complete"):
            validate_complete_snapshot(local, require_local_assets=True)
            remote = local
    missing = set()
    for item in remote["items"]:
        for key in ("image", "thumbnail"):
            relative = item.get(key)
            if relative is None:
                continue
            if not re.fullmatch(r"assets/catalog/[a-zA-Z0-9_-]+\.webp", relative):
                raise ValueError(f"Unrecognized deployment asset path: {relative}")
            if not valid_webp_file(SITE / relative):
                missing.add(relative)
    for relative in sorted(missing):
        body = read(relative)
        if not body.startswith(b"RIFF") or body[8:12] != b"WEBP" or int.from_bytes(body[4:8], "little") + 8 != len(body):
            raise ValueError(f"Deployment asset is not WebP: {relative}")
        path = SITE / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_bytes(body)
        temp.replace(path)
    validate_complete_snapshot(remote, require_local_assets=True)
    atomic_json(target, remote)
    return remote, len(missing)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Fetch HTML again; preserve old published data if any category fails")
    parser.add_argument("--offline", action="store_true", help="Reparse only the saved HTTP cache")
    parser.add_argument("--resume", action="store_true", help="Reparse cached pages and finish images even when the current snapshot is younger than 24h")
    parser.add_argument("--no-images", action="store_true", help="Collect full listing data without fetching/optimizing images")
    parser.add_argument("--deployed", metavar="HTTPS_URL", help="Restore published data and missing assets from the HTTPS tights-guide/ base directory")
    parser.add_argument("--restore-only", action="store_true", help="Require --deployed; restore/validate the published catalogue and stop without collecting source pages")
    parser.add_argument("--initial-image-manifest", type=Path, help="Explicit one-time first-CI asset adoption; only for the approved review workflow, never regular updates")
    parser.add_argument("--tls12", action="store_true", help="Limit TLS to 1.2 for incompatible local transports; certificates are still verified")
    parser.add_argument("--transport", choices=("urllib", "curl"), default="urllib", help="Public-source HTTP transport for both HTML and images; curl keeps certificate verification enabled")
    parser.add_argument("--workers", type=int, default=4, choices=range(1, 5))
    parser.add_argument("--request-interval", type=float, default=0.30, help="Minimum seconds between public-source request starts (0.3 to 5)")
    parser.add_argument("--cache", type=Path, default=QA / "http-cache")
    args = parser.parse_args(argv)
    if not math.isfinite(args.request_interval) or not 0.3 <= args.request_interval <= 5:
        parser.error("--request-interval must be between 0.3 and 5 seconds")
    if args.restore_only and not args.deployed:
        parser.error("--restore-only requires --deployed")
    if args.restore_only and args.initial_image_manifest:
        parser.error("--initial-image-manifest is incompatible with --restore-only")
    QA.mkdir(parents=True, exist_ok=True)
    started = utc_now()
    old_catalog_path = SITE / "data/catalog.json"
    if args.deployed:
        try:
            _, restored_assets = restore_deployed(args.deployed, old_catalog_path)
            print(f"Restored deployed catalogue; fetched {restored_assets} missing assets", flush=True)
        except DeploymentCatalogNotFound as exc:
            try:
                seed = json.loads(old_catalog_path.read_text("utf-8-sig"))
                validate_complete_snapshot(seed, require_local_assets=True)
            except Exception as seed_error:
                atomic_json(QA / "restore-error.json", {"checkedAt": started, "url": args.deployed, "error": str(exc), "seedError": str(seed_error), "fatal": True})
                print(f"Deployment is absent and no complete repository seed is available: {seed_error}", flush=True)
                return 3
            print("Deployed catalogue returned HTTP 404; using the validated complete repository seed for the first publication", flush=True)
        except Exception as exc:
            atomic_json(QA / "restore-error.json", {"checkedAt": started, "url": args.deployed, "error": str(exc), "fatal": True})
            print(f"Deployment restore failed; published data left untouched: {exc}", flush=True)
            return 3
    if args.restore_only:
        try:
            restored = json.loads(old_catalog_path.read_text("utf-8-sig"))
            validate_complete_snapshot(restored, require_local_assets=True)
        except Exception as exc:
            atomic_json(QA / "restore-error.json", {"checkedAt": started, "url": args.deployed, "error": str(exc), "fatal": True})
            print(f"Restored catalogue failed local asset validation: {exc}", flush=True)
            return 3
        print(f"Restored and validated {len(restored['items'])} catalogue models for publication", flush=True)
        return 0
    if old_catalog_path.exists() and not (args.refresh or args.resume or args.offline):
        previous_data = json.loads(old_catalog_path.read_text("utf-8-sig"))
        if catalog_is_recent(previous_data):
            print(f"Complete catalogue already checked at {previous_data['checkedAt']}; daily refresh skipped", flush=True)
            return 0
    client = PublicClient(args.cache, refresh=args.refresh, offline=args.offline, tls12=args.tls12, transport=args.transport, delay=args.request_interval)
    report = {"startedAt": started, "source": BASE, "failedUrls": []}
    try:
        body, meta = client.get(BASE)
        tree = TreeParser(decode_html(body, meta.get("contentType", ""))).root
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
    if args.initial_image_manifest:
        try:
            initial_images = bind_initial_images(items, args.initial_image_manifest)
            for item_id, adoption in initial_images.items():
                old = previous.get(item_id, {})
                # Existing publication evidence always takes precedence. A known
                # old URL mismatch may never be bypassed by the bootstrap flag.
                if old.get("image") or (old.get("imageSource") and old["imageSource"] != adoption["imageSource"]):
                    continue
                previous[item_id] = {**old, **adoption}
            print(f"Verified {len(initial_images)} first-CI image pairs against hashes and fresh listing identifiers", flush=True)
        except Exception as exc:
            print(f"Initial-image provenance validation failed; published catalogue preserved: {exc}", flush=True)
            return 3
    for item in items:
        if item["id"] in previous:
            item["packageId"] = previous[item["id"]].get("packageId")
    summaries = sorted([row[0] for row in results], key=lambda row: row["url"])
    failed = [error for cat in summaries for error in cat["errors"]]
    if not items:
        failed.append({"url": BASE, "reason": "No in-scope products collected; refusing an empty replacement"})
    complete = not failed and not unknown_brands
    parent_only = [item for item in items if item["categories"] and all(len(urlsplit(category["url"]).path.strip("/").split("/")) == 2 for category in item["categories"])]
    coverage = {
        "complete": complete, "categories": len(categories), "categoriesComplete": sum(cat["complete"] for cat in summaries),
        "parentListings": sum(cat.get("scopeLevel") == "parent" for cat in summaries), "subcategories": sum(cat.get("scopeLevel") == "subcategory" for cat in summaries), "parentOnlyProducts": len(parent_only),
        "pages": sum(len(cat["pages"]) for cat in summaries), "listedOccurrences": sum(cat["cardCount"] for cat in summaries),
        "uniqueProducts": len(items), "excludedUnrelatedProducts": len(excluded),
        "imagesAwaitingReview": sum(item["imageNeedsReview"] for item in items),
        "byKind": dict(sorted(Counter(item["productKind"] for item in items).items())),
        "byBrand": dict(sorted(Counter(item["brand"] for item in items).items())),
        "byAvailability": dict(sorted(Counter(item["availability"] for item in items).items())),
        "pricesAvailable": sum(item["priceRub"] is not None for item in items),
        "scope": "Все публичные родительские и дочерние листинги колготок классика, колготок фантазия, чулок на силиконе и чулок под пояс, а также отдельная подкатегория детских колготок. Остальные группы не входят в охват.",
    }
    # Reprocessing cached images must not make old prices appear newly checked.
    checked_at = max((page["checkedAt"] for category in summaries for page in category["pages"]), default=started)
    output = {"version": 1, "source": {"id": "loretta", "name": "Лоретта", "url": BASE}, "checkedAt": checked_at, "coverage": coverage, "items": items}

    def checkpoint(phase, done=0, finished=False):
        coverage.update({"images": sum(bool(item["image"]) for item in items), "imageFailures": len(image_errors), "imagePhaseComplete": finished})
        atomic_json(QA / "catalog-candidate.json", output)
        report.update({**coverage, "phase": phase, "lastUpdatedAt": utc_now(), "imageJobsCompleted": done, "imageJobsTotal": 0 if args.no_images else len(items), "categoryDetails": summaries, "failedUrls": failed, "imageErrors": image_errors, "excludedProducts": excluded, "conflicts": conflicts, "unknownBrands": unknown_brands, "parentOnlyItems": [{"id": item["id"], "brand": item["brand"], "model": item["model"], "source": item["source"]} for item in parent_only], "networkRequests": client.network_count, "cacheHits": client.cache_count, "published": False})
        if finished:
            report["finishedAt"] = utc_now()
        atomic_json(QA / "coverage-report.json", report)

    # The review candidate is useful even when a long image phase is interrupted.
    # This is not the published JSON; its data dates are still actual HTTP dates.
    checkpoint("listing_complete")
    print(f"Listings complete: {len(items)} unique models, {len(failed)} source errors, {len(unknown_brands)} unresolved brands. Review candidate saved.", flush=True)
    done = 0
    if not args.no_images:
        pillow_runtime()
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = [executor.submit(optimize_image, client, item, previous.get(item["id"])) for item in items]
            for done, future in enumerate(as_completed(futures), 1):
                _, error = future.result()
                if error:
                    image_errors.append(error)
                if done % 100 == 0 or done == len(items):
                    checkpoint("images_in_progress", done)
                    print(f"Images {done}/{len(items)}, failures {len(image_errors)}", flush=True)
    else:
        # A data-only refresh retains already optimized, same-source photos.
        for item in items:
            old = previous.get(item["id"], {})
            if old.get("imageSource") == item["imageSource"] and not item["imageNeedsReview"]:
                for key in ("image", "thumbnail", "width", "height", "photos"):
                    if key in old:
                        item[key] = old[key]
    checkpoint("finished", done, finished=True)
    if complete:
        atomic_json(old_catalog_path, output)
        report["published"] = True
        atomic_json(QA / "coverage-report.json", report)
        print(f"Published {len(items)} unique products, {coverage['images']} images", flush=True)
    else:
        print(f"NOT PUBLISHED: {len(failed)} category errors, {len(unknown_brands)} unresolved brands. Previous published catalogue preserved.", flush=True)
    return 0 if complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
