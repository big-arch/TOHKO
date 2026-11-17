"""Build the dated product catalogue from local JSON, without network access.

Only catalog.html, data/catalog.js and data/exchange-rate.js are written.
The site navigation/footer are inherited from index.html; other pages are untouched.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import html
import json
import math
from pathlib import Path
import re
import unicodedata
from urllib.parse import urlencode, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "tights-guide"
PAGE_SIZE = 48
STALE = timedelta(hours=48)
MOSCOW = timezone(timedelta(hours=3))
GENDERS = {"women": "Женские", "men": "Мужские", "unisex": "Унисекс", "kids": "Детские", "unknown": "Не уточнено"}
PRICE_BANDS = [("under500", "Меньше 500 ₽"), ("500-999", "500–999 ₽"), ("1000-1999", "1 000–1 999 ₽"), ("2000-4999", "2 000–4 999 ₽"), ("5000plus", "От 5 000 ₽"), ("unknown", "Цена не указана")]


def esc(value: object) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def order(value: str) -> str:
    return unicodedata.normalize("NFKD", value).casefold()


def https_url(value: object) -> str:
    if not isinstance(value, str):
        return ""
    try:
        url = urlsplit(value)
        return value if url.scheme == "https" and url.netloc else ""
    except ValueError:
        return ""


def image_path(value: object) -> str:
    return value if isinstance(value, str) and re.fullmatch(r"assets/catalog/[a-zA-Z0-9_./%\-]+", value) and ".." not in value else ""


def timestamp(value: object) -> datetime | None:
    match = isinstance(value, str) and re.fullmatch(r"(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(?:Z|[+-](\d{2}):(\d{2}))", value)
    if not match or any(int(match[index] or 0) > maximum for index, maximum in ((2, 23), (3, 59), (4, 59), (5, 23), (6, 59))):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
    except ValueError:
        return None


def price_known(value: object) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value) and value > 0


def rate_valid(rate: object, now: datetime) -> bool:
    if not isinstance(rate, dict) or rate.get("base") != "USD" or rate.get("quote") != "RUB" or not price_known(rate.get("rubPerUsd")):
        return False
    try:
        day = datetime.strptime(rate.get("date", ""), "%Y-%m-%d").date()
        if day.isoformat() != rate["date"] or day > now.astimezone(MOSCOW).date():
            return False
    except (ValueError, TypeError):
        return False
    checked = timestamp(rate.get("checkedAt"))
    return checked is not None and checked <= now + timedelta(minutes=5)


def stale(value: object, now: datetime) -> bool:
    checked = timestamp(value)
    return checked is not None and now - checked > STALE


def date_text(value: object) -> str:
    checked = timestamp(value)
    return checked.astimezone(MOSCOW).strftime("%d.%m.%Y") if checked else "дата не указана"


def rub_text(value: float, decimals: int = 2) -> str:
    result = f"{value:,.{decimals}f}".rstrip("0").rstrip(".")
    return result.replace(",", "\u00a0").replace(".", ",")


def checked_text(item: dict, now: datetime) -> str:
    checked = timestamp(item.get("checkedAt"))
    if checked is None or checked > now + timedelta(minutes=5):
        return "Дата проверки не указана"
    prefix = "Цена проверена " if price_known(item.get("priceRub")) else "Проверено "
    return prefix + date_text(item.get("checkedAt")) + (" · требует обновления" if stale(item.get("checkedAt"), now) else "")


def card(item: dict, rate: dict | None, now: datetime) -> str:
    picture = image_path(item.get("thumbnail")) or image_path(item.get("image"))
    width = int(item.get("width") or 480)
    height = int(item.get("height") or 640)
    title = esc(item["title"])
    image = f'<img src="{esc(picture)}" alt="{title} — каталожное изображение" width="{width}" height="{height}" loading="lazy" decoding="async">' if picture else '<span class="catalog-no-image">Фото пока недоступно</span>'
    price = item.get("priceRub")
    known = price_known(price)
    prefix = "от " if item.get("priceFrom") else ""
    rub = prefix + rub_text(price) + " ₽" if known else "Цена не указана"
    usd = f'<span>≈ {prefix}${price / rate["rubPerUsd"]:,.2f}</span>' if known and rate_valid(rate, now) else ""
    facts = [item.get("productKind"), str(item["den"]) + " DEN" if item.get("den") is not None else ""]
    source = https_url(item.get("source"))
    query = "?" + urlencode({"product": item["id"]})
    return f'''<article class="catalog-card" data-id="{esc(item['id'])}"><a class="catalog-open" data-product="{esc(item['id'])}" href="{esc(query)}" aria-label="Подробнее: {title}"><span class="catalog-image">{image}<span class="catalog-image-open" aria-hidden="true">↗</span></span><span class="catalog-brand">{esc(item['brand'])}</span><h3>{esc(item.get('model') or item['title'])}</h3></a><p class="catalog-card-facts">{esc(' · '.join(f for f in facts if f))}</p><p class="catalog-price{'' if known else ' is-unknown'}"><strong>{esc(rub)}</strong>{usd}</p><p class="catalog-checked{' is-stale' if stale(item.get('checkedAt'), now) else ''}">{esc(checked_text(item, now))}</p>{'<p class="catalog-availability">Нет в наличии</p>' if item.get('availability') == 'out_of_stock' else ''}{f'<a class="catalog-seller" href="{esc(source)}" target="_blank" rel="noopener noreferrer">У продавца <span aria-hidden="true">↗</span><span class="catalog-sr-only"> — {title}</span></a>' if source else ''}</article>'''


def rate_markup(rate: dict | None, now: datetime) -> str:
    if not rate_valid(rate, now):
        return "Курс USD пока недоступен. Цены показаны в рублях."
    name = esc(rate.get("sourceName") or "Банк России")
    source = https_url(rate.get("source"))
    link = f'<a href="{esc(source)}" target="_blank" rel="noopener noreferrer">{name} ↗</a>' if source else name
    day = datetime.strptime(rate["date"], "%Y-%m-%d").strftime("%d.%m.%Y")
    return f'{link}: 1 USD = {rub_text(rate["rubPerUsd"], 4)} ₽. Действует с {day}; проверен {date_text(rate.get("checkedAt"))}{" · требует обновления" if stale(rate.get("checkedAt"), now) else ""}.'


def options(values: list[tuple[str, str]]) -> str:
    return "".join(f'<option value="{esc(key)}">{esc(label)}</option>' for key, label in values)


def body_markup(data: dict, rate: dict | None, now: datetime) -> str:
    rows = sorted(data["items"], key=lambda row: (order(row["brand"]), order(row.get("model") or row["title"]), order(row["id"])))
    counts = Counter(item["brand"] for item in rows)
    brands = sorted(counts, key=order)
    kinds = sorted({row.get("productKind", "колготки") for row in rows}, key=order)
    genders = {row.get("gender") or "unknown" for row in rows}
    source = data.get("source") or {}
    source_name = source.get("name") or "Лоретта"
    source_url = https_url(source.get("url"))
    source_link = f'<a href="{esc(source_url)}" target="_blank" rel="noopener noreferrer">{esc(source_name)} ↗</a>' if source_url else esc(source_name)
    links = '<a href="catalog.html" data-catalog-brand="all" aria-current="true"><span>Все бренды</span><span>' + str(len(rows)) + '</span></a>'
    links += "".join(f'<a href="?{esc(urlencode({"brand": brand}))}" data-catalog-brand="{esc(brand)}"><span>{esc(brand)}</span><span>{counts[brand]}</span></a>' for brand in brands)
    priced = sum(price_known(item.get("priceRub")) for item in rows)
    checked = date_text(data.get("checkedAt"))
    cards = "".join(card(item, rate, now) for item in rows[:PAGE_SIZE])
    return f'''
<section class="portal-container catalog-intro"><p class="portal-eyebrow">Модели и цены</p><h1>Колготки и чулки.</h1><div class="catalog-intro-bottom"><p>Выберите бренд, найдите свою модель и сравните цены. Рядом с рублями — ориентир в долларах по курсу Банка России.</p><div class="catalog-summary"><p><strong>{len(rows)}</strong> моделей · <strong>{len(brands)}</strong> брендов</p><small>{priced} моделей с ценой · источник: {source_link}<br>Каталог проверен: {esc(checked)}.</small></div></div></section>
<div class="portal-container catalog-browser"><details class="catalog-directory" id="catalog-directory" open><summary><span>Бренды</span><span aria-hidden="true">+</span></summary><p>По алфавиту. Число рядом — модели из каталога «Лоретты».</p><nav id="catalog-brand-links" aria-label="Выбрать бренд каталога">{links}</nav></details>
<section class="catalog-collection" id="catalog-collection" aria-labelledby="catalog-collection-title"><form class="catalog-tools" id="catalog-tools" role="search" aria-label="Фильтры каталога" hidden>
<label class="catalog-search">Найти модель<input type="search" id="catalog-query" placeholder="Название, бренд или DEN" autocomplete="off" maxlength="200"></label>
<label>Бренд<select id="catalog-brand">{options([('all', 'Все бренды')] + [(brand, f'{brand} · {counts[brand]}') for brand in brands])}</select></label>
<label>Изделие<select id="catalog-kind">{options([('all', 'Все изделия')] + [(kind, kind.capitalize()) for kind in kinds])}</select></label>
<label>Категория<select id="catalog-gender">{options([('all', 'Все категории')] + [(key, label) for key, label in GENDERS.items() if key in genders])}</select></label>
<label>Цена в рублях<select id="catalog-price">{options([('all', 'Любая цена')] + PRICE_BANDS)}</select></label>
<label class="catalog-sort-field">Порядок<select id="catalog-sort"><option value="brand">По бренду и названию</option><option value="price-asc">Сначала дешевле</option><option value="price-desc">Сначала дороже</option></select></label>
</form><div class="catalog-actions" id="catalog-actions" hidden><button type="button" id="catalog-reset">Сбросить фильтры</button><button type="button" id="catalog-copy">Скопировать ссылку на подборку</button><p class="catalog-share-status" id="catalog-share-status" role="status"></p></div>
<div class="catalog-results"><h2 id="catalog-collection-title">Каталог</h2><p class="catalog-count" id="catalog-count" role="status" aria-live="polite">{len(rows)} моделей · показано {min(PAGE_SIZE, len(rows))}</p></div>
<p class="catalog-runtime-note" id="catalog-runtime-note" hidden></p><div class="catalog-grid" id="catalog-grid">{cards}</div>
<div class="catalog-empty" id="catalog-empty" hidden><h3>В этой подборке пока пусто</h3><p>Попробуйте другой диапазон цены или уберите один из фильтров.</p><button type="button" id="catalog-empty-reset">Сбросить фильтры</button></div>
<button type="button" class="catalog-more" id="catalog-more" hidden>Показать ещё</button><p class="catalog-visible-note" id="catalog-visible-note"></p><noscript><p class="catalog-runtime-note">Показаны первые {min(PAGE_SIZE, len(rows))} из {len(rows)} моделей по алфавиту брендов. Для полного каталога, поиска и фильтров включите JavaScript. Ссылки «У продавца» доступны.</p></noscript></section></div>
<section class="portal-container catalog-about" aria-labelledby="catalog-about-title"><h2 id="catalog-about-title">О ценах и фотографиях</h2><div><p>Источник моделей и рублёвых цен — {source_link}. У каждой модели указана дата проверки. Цены старше 48 часов отмечены как требующие обновления; окончательные цену, размер, цвет и наличие уточняйте у продавца.</p><p id="catalog-rate">{rate_markup(rate, now)}</p><p>Сумма в USD приблизительная: рублёвая цена разделена на курс, результат округлён до двух знаков. ТОНКО помогает сравнить модели; покупка оформляется на сайте продавца.</p><p>Здесь показаны каталожные изображения изделий. Отдельные фотографии упаковок собраны в <a href="packaging.html">архиве упаковок</a>. Изображения и товарные знаки принадлежат их правообладателям.</p></div></section>
<dialog class="catalog-dialog" id="catalog-dialog" aria-labelledby="catalog-title"><div class="catalog-dialog-bar"><span>Каталожное изображение</span><button type="button" id="catalog-close" autofocus>Закрыть ×</button></div><div class="catalog-dialog-layout"><div class="catalog-photo-column"><div class="catalog-image-stage"><img id="catalog-full" alt=""><p id="catalog-photo-empty" hidden>Фото пока недоступно</p></div><div class="catalog-photos" id="catalog-photos" hidden></div><p class="catalog-photo-caption">Изображение изделия из каталога продавца. Цвет и вариант могут отличаться.</p></div><div class="catalog-detail"><p class="portal-eyebrow" id="catalog-dialog-brand"></p><h2 id="catalog-title"></h2><p class="catalog-price" id="catalog-detail-price"></p><p class="catalog-detail-checked" id="catalog-detail-checked"></p><p class="catalog-detail-description" id="catalog-description" hidden></p><dl class="catalog-facts" id="catalog-facts"></dl><p class="catalog-detail-rate" id="catalog-detail-rate"></p><div class="catalog-detail-actions"><a id="catalog-source" target="_blank" rel="noopener noreferrer">У продавца ↗</a><a id="catalog-package" hidden>Упаковка в архиве →</a></div><p class="catalog-source-note">Источник: <span id="catalog-source-name"></span>. Размер, цвет и итоговая цена — в карточке продавца.</p></div></div></dialog>'''


def validate(data: dict) -> None:
    if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("items"), list):
        raise ValueError("Catalogue must be a version 1 object with an items array")
    identifiers: set[str] = set()
    for item in data["items"]:
        for key in ("id", "brand", "title"):
            if not isinstance(item.get(key), str) or not item[key].strip():
                raise ValueError(f"Missing {key}: {item.get('id')}")
        if item["id"] in identifiers:
            raise ValueError(f"Duplicate product id: {item['id']}")
        identifiers.add(item["id"])
        if item.get("priceRub") is not None and not price_known(item["priceRub"]):
            raise ValueError(f"Price must be positive or null: {item['id']}")
        if not https_url(item.get("source")):
            raise ValueError(f"Missing HTTPS product source: {item['id']}")
        for key in ("image", "thumbnail"):
            if item.get(key) and not image_path(item[key]):
                raise ValueError(f"Unsafe catalogue image: {item['id']} {key}")


def script_data(global_name: str, data: object) -> str:
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False).replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    return f"window.{global_name} = {payload};\n"


def render_page(data: dict, rate: dict | None, shell: str, version: str, now: datetime) -> str:
    body = body_markup(data, rate, now)
    # Drop homepage-only news data and scripts. Retain the shared accessible menu and assistant.
    shell = re.sub(r'<script\b[^>]*(?:news-seed|news-reader\.js|news\.js)[^>]*>.*?</script>', '', shell, flags=re.S)
    result, replaced = re.subn(r'<main\b[^>]*>.*?</main>', lambda _: '<main id="content">' + body + '</main>', shell, count=1, flags=re.S)
    if replaced != 1:
        raise ValueError("index.html must contain one main element")
    result = re.sub(r'<title>.*?</title>', '<title>Колготки и чулки — модели и цены по брендам · ТОНКО</title>', result, count=1)
    description = f'Каталог ТОНКО: {len(data["items"])} моделей колготок и чулок. Бренды, цены в рублях и приблизительно в USD, поиск и фильтры.'
    result = re.sub(r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{esc(description)}">', result, count=1)
    result = re.sub(r'<meta property="og:title" content="[^"]*">', '<meta property="og:title" content="Колготки и чулки — модели и цены · ТОНКО">', result, count=1)
    # Mark only this page's nav link; integration of the rest of the site belongs to the release builder.
    def nav_current(match: re.Match) -> str:
        nav = re.sub(r'\s(?:class="active"|aria-current="page")', '', match.group())
        return nav.replace('<a href="catalog.html">', '<a href="catalog.html" class="active" aria-current="page">')
    result = re.sub(r'<nav class="portal-nav"[^>]*>.*?</nav>', nav_current, result, count=1, flags=re.S)
    result = result.replace('</head>', f'<link rel="stylesheet" href="catalog.css?v={version}"></head>')
    result = result.replace('</body>', f'<script src="data/catalog.js?v={version}"></script><script src="data/exchange-rate.js?v={version}"></script><script src="catalog.js?v={version}"></script></body>')
    return result


def build(catalog_path: Path, exchange_path: Path, output_dir: Path, *, site: Path = SITE, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    data = json.loads(catalog_path.read_text(encoding="utf-8"))
    validate(data)
    links_path = site / 'data/catalog-prices.json'
    if links_path.is_file():
        links = json.loads(links_path.read_text(encoding="utf-8"))
        packages = links.get('packageByCatalog', {})
        data = {**data, 'items': [{**item, 'packageId': packages.get(item['id']) or item.get('packageId')} for item in data['items']]}
    rate = None
    if exchange_path.is_file():
        try:
            rate = json.loads(exchange_path.read_text(encoding="utf-8"))
            json.dumps(rate, allow_nan=False)
        except (ValueError, OSError):
            rate = None  # A malformed rate never blocks the RUB catalogue or invents a USD value.
    catalog_js = script_data("TONKO_CATALOG", data)
    rate_js = script_data("TONKO_EXCHANGE_RATE", rate)
    hashed = catalog_js.encode() + rate_js.encode() + (site / 'catalog.js').read_bytes() + (site / 'catalog.css').read_bytes()
    version = hashlib.sha256(hashed).hexdigest()[:12]
    page = render_page(data, rate, (site / 'index.html').read_text(encoding="utf-8"), version, now)
    # Compute and validate everything before any existing output is changed.
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / 'data').mkdir(exist_ok=True)
    (output_dir / 'data/catalog.js').write_text(catalog_js, encoding="utf-8")
    (output_dir / 'data/exchange-rate.js').write_text(rate_js, encoding="utf-8")
    (output_dir / 'catalog.html').write_text(page, encoding="utf-8")
    return {"models": len(data['items']), "brands": len({item['brand'] for item in data['items']}), "rateAvailable": rate_valid(rate, now), "version": version}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog', type=Path, default=SITE / 'data/catalog.json', help='Local catalogue JSON; required, never fabricated.')
    parser.add_argument('--exchange', type=Path, default=SITE / 'data/exchange-rate.json', help='Local exchange JSON. Missing/invalid data leaves RUB only.')
    parser.add_argument('--output-dir', type=Path, default=SITE, help='Directory for catalog.html and its two data wrappers.')
    args = parser.parse_args()
    if not args.catalog.is_file():
        parser.error(f'Catalogue data is missing: {args.catalog}; run the catalogue importer first.')
    result = build(args.catalog, args.exchange, args.output_dir)
    print(f'Catalogue: {result["models"]} models, {result["brands"]} brands, USD rate {"available" if result["rateAvailable"] else "unavailable"}')


if __name__ == '__main__':
    main()
