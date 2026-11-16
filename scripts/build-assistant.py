"""Build a bounded, local knowledge snapshot. --inject adds the widget to pages.

No network calls, keys, raw feed excerpts or user submissions. News are included
only after the site's publication gate confirms a prepared readable article.
Run after other page/catalog builders; repeat after editorial/catalog changes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlencode, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "tights-guide"
FUNCTION = ROOT / "supabase/functions/tonko-assistant"
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
from news_publication import is_ready
from news_feed import date, plain


def guide(key, title, href, text, intents, keywords=()):
    return {"id": "guide-" + key, "kind": "guide", "title": title, "href": href,
            "text": text, "intents": intents, "keywords": list(keywords)}


# Editorial summaries of the linked TONKO materials; no universal size chart.
GUIDES = [
    guide("choice", "Как выбрать колготки", "guide.html#picker",
          "Начните с задачи: повседневный или вечерний образ, слой под брюки, тренировка. Затем выберите прозрачность, рисунок и важные детали: пояс, швы, мысок, ластовица. На сайте есть интерактивный подбор критериев и сравнение DEN. ТОНКО — независимый справочник, не магазин; заказов, наличия и актуальных цен здесь нет.", ["catalog", "den", "style"]),
    guide("den", "Что означает DEN", "guide.html#den-lab",
          "DEN — линейная плотность нити: масса 9000 метров нити в граммах. 20 DEN означает 20 г на эту длину, а не толщину готового полотна. Впечатление прозрачности зависит также от вязки, оттенка, растяжения, посадки и света. По одному DEN нельзя обещать одинаковые тепло, прочность и прозрачность разных моделей. Лаборатория на сайте — условная схема, не физический расчёт и не модель конкретного изделия.", ["den"], ["ден", "плотность", "10", "20", "40", "80", "прозрачность"]),
    guide("size", "Посадка и размер: сначала таблица модели", "atlas.html",
          "Для размера нужна таблица конкретного бренда и модели; универсальной сетки нет. В этом справочном снимке числовые размерные таблицы производителей не приведены. Уточните бренд, модель и нужные по её таблице параметры, например рост, вес или обхваты. Не назначайте размер по цифрам другого производителя. При сползании, давлении пояса и недостатке длины оцените размер и конструкцию: увеличение DEN само по себе проблему не решает. Число на упаковке нужно сопоставить с таблицей именно этой пары.", ["size"], ["размер", "рост", "вес", "посадка", "таблица", "сетка", "XL", "XXL"]),
    guide("material", "Полиамид, капрон и эластан", "nylon.html",
          "Капрон — полиамидное волокно; в чулочном трикотаже используются полиамид и эластан. Эластан помогает полотну растягиваться и восстанавливать форму. Число DEN не заменяет состав. Проценты полиамида, эластана, хлопка или шерсти относятся к конкретному артикулу и могут различаться. Сверяйте состав с ярлыком или официальной карточкой выбранной модели, не переносите состав на весь бренд.", ["material"], ["капрон", "нейлон", "состав", "полиамид", "эластан", "шерсть", "хлопок"]),
    guide("care", "Уход за любимой парой", "guide.html#care",
          "Для обычных тонких колготок бережный ориентир — ручная стирка в чуть тёплой воде с мягким средством и тщательное полоскание. После стирки аккуратно уберите воду чистым полотенцем, не выкручивайте; расправьте и дайте высохнуть на воздухе, разложив или аккуратно развесив. Не кладите на батарею и не ускоряйте сушку горячим воздухом. Эти приёмы описаны в официальной инструкции Snag; конкретный ярлык имеет приоритет, особенно у шерсти, декора и специальных изделий. Snag рекомендует избегать прямого нагрева и барабанной сушки: они вредят эластичности. Машинный режим и точную температуру выбирают только по ярлыку; если машинная стирка разрешена, используйте мешочек и отделите молнии, крючки и липучки. Перед надеванием снимите украшения, проверьте ногти, соберите ногу изделия до мыска и распределяйте полотно постепенно. Источник: Snag, How to Care for Your Tights to Help them Last Longer, 16.02.2024; проверен 16.11.2026.", ["care"], ["стирка", "сушка", "сушить", "батарея", "полотенце", "зацепка", "надевать", "уход"]),
    guide("men", "Колготки в мужском гардеробе", "men.html",
          "На сайте разобраны полноценные одетые мужские образы: пиджак или рубашка, трикотаж, шорты, обувь и колготки; есть сочетания слоёв и выразительные фактуры. Выбор зависит от нужного эффекта, посадки и удобства, а не только гендерной надписи на изделии. Для незаметного слоя под брюки проверьте длину, швы и пояс; для открытого образа сравните плотность, рисунок и цвет с одеждой и обувью. Уточняйте, под брюки нужен слой или видимый образ, когда это меняет рекомендацию.", ["style", "size"], ["мужчинам", "мужские", "парням", "унисекс", "шорты", "образ"]),
    guide("card", "Пять вопросов к карточке товара", "read-product-card.html",
          "Перед выбором проверьте: что означает заявленная плотность, из чего сделана модель, как устроены пояс и швы, подходит ли размер по таблице, как ухаживать. Маркетинговое название не гарантирует свойства. Источник, артикул и материал конкретной пары важнее общих обещаний бренда.", ["catalog", "material", "size"]),
    guide("medical", "Поддержка и лечебная компрессия", "guide.html#picker",
          "Обычная поддержка, моделирование и утяжка одежды не являются назначением медицинской компрессии. Число DEN не задаёт класс компрессии. Медицинские изделия и класс давления подбираются отдельно с профильным специалистом. ТОНКО не ставит диагнозы и не подбирает лечение варикоза или отёков.", ["medical"], ["компрессия", "лечебный", "давление", "варикоз", "отёк"]),
    guide("packaging", "Архив упаковок по брендам", "packaging.html",
          "Архив показывает упаковки, фирменные вкладыши и каталоговые изображения с источниками. Можно выбрать бренд, найти модель и открыть изображение крупно. Оформление меняется между выпусками и рынками. DEN для фильтра извлечён из названия карточки и нуждается в сверке. Архив не является магазином, полным реестром выпусков, доказательством актуального наличия, состава или цены.", ["catalog"], ["упаковки", "коробка", "вкладыш", "фотография"]),
    guide("looks", "Галерея фактур и образов", "lookbook.html",
          "Галерея показывает прозрачность, сетку, кружево, узоры, блеск и цельные женские и мужские сочетания. Когда бренд или автор присланного снимка неизвестны, они не приписываются. Фотография помогает сравнить визуальные эффекты, но не измеряет DEN, состав или лечебные свойства.", ["style", "den"], ["фото", "блеск", "сетка", "кружево", "рисунок", "наряд"]),
    guide("textures", "Фактуры под лупой", "textures.html",
          "Мастерская показывает реальные снимки ткани с увеличением в пределах исходного разрешения. Можно сравнить поверхность и рисунок; визуальное сходство не доказывает одинаковый состав или характеристики модели.", ["material", "style"], ["текстура", "фактура", "полотно", "матовый"]),
    guide("leggings", "Легинсы: задача и конструкция", "leggings.html",
          "Для легинсов важны назначение, посадка, материал, швы и свобода движения. Спортивную модель выбирают под конкретную тренировку, повседневную — под гардероб и комфорт. Характеристики нужно сверять в карточке модели, а не выводить только из внешнего вида.", ["style", "material", "size"], ["легинсы", "лосины", "спорт", "тренировка"]),
    guide("videos", "Видео: обзоры, уход и производство", "videos.html",
          "Видеотека содержит курируемые обзоры, примерки, сочетания, уход, производство и звуки ткани или распаковки. Есть авторы и прямые ссылки. Можно выбрать раздел без YouTube. Доступность внешнего плеера зависит от сервиса, а подборка не охватывает все ролики.", ["catalog", "style", "care"], ["видео", "обзор", "примерка", "ролик"]),
]

ALIASES = {"wolford": ["вольфорд"], "falke": ["фальке", "фалке"], "conte": ["конте"],
           "calzedonia": ["кальцедония", "кальзедония"], "omsa": ["омса"], "sisi": ["сиси"],
           "golden-lady": ["голден леди"], "oroblu": ["ороблю"], "incanto": ["инканто"],
           "giulia": ["джулия"], "gabriella": ["габриэлла", "габриелла"], "snag": ["снэг"]}


def load_brands():
    # Only locally maintained executable data files; never run a feed or upload.
    script = """const fs = require('node:fs'); const vm = require('node:vm');
const context = vm.createContext({window:{}});
for (const file of ['brands.js','brand-research.js']) vm.runInContext(fs.readFileSync('tights-guide/data/'+file,'utf8'), context, {timeout:1000});
process.stdout.write(JSON.stringify(context.window.BRAND_DATA));"""
    result = subprocess.run(["node", "-e", script], cwd=ROOT, capture_output=True, check=True, encoding="utf-8")
    return json.loads(result.stdout)


def photo_registry():
    """Only maintained local registries; photos never come from model output.

    Legacy photos have no independently verified DEN. A number in their title
    never becomes a filter value. Exact package matches carry explicit evidence.
    """
    script = """const fs = require('node:fs'); const vm = require('node:vm');
const context = vm.createContext({window:{}});
vm.runInContext(fs.readFileSync('tights-guide/data/photos.js','utf8'), context, {timeout:1000});
process.stdout.write(JSON.stringify(context.window.PHOTO_DATA));"""
    result = subprocess.run(["node", "-e", script], cwd=ROOT, capture_output=True, check=True, encoding="utf-8")
    photos = []
    for p in json.loads(result.stdout):
        if p.get("category") == "packaging":
            continue
        source = p.get("source", "sources.html#photography")
        unknown_source = "google.com/search" in source or not source.startswith("https://")
        if unknown_source:
            source = "sources.html#photography"
        responsive = sorted(p.get("responsive", []), key=lambda x: x["width"])
        thumb = next((r["src"] for r in responsive if r["width"] >= 320), p["image"])
        photos.append({"id": "gallery-" + p["id"], "title": p["title"], "src": p["image"], "thumb": thumb,
                       "alt": p.get("alt") or p["title"], "caption": p.get("caption") or p["title"],
                       "source": source, "sourceLabel": "Об источниках фото" if unknown_source else p.get("author") or "Источник фото",
                       "credit": p.get("author") or "Автор не указан", "category": "men" if p.get("category") == "men" else "women",
                       "tags": list(dict.fromkeys([p.get("category", "style"), *p.get("tags", [])])),
                       "den": None, "denVerified": False, "width": p["width"], "height": p["height"]})
    styles = SITE / "data/style-photos.json"
    if styles.is_file():
        data = json.loads(styles.read_text(encoding="utf-8"))
        if data.get("version") != 1 or not isinstance(data.get("items"), list):
            raise ValueError("Invalid style-photos registry")
        for p in data["items"]:
            photos.append({**p, "id": p["id"] if p["id"].startswith("style-") else "style-" + p["id"]})
    packages = SITE / "data/package-looks.json"
    if packages.is_file():
        data = json.loads(packages.read_text(encoding="utf-8"))
        if data.get("version") != 1 or not isinstance(data.get("items"), list):
            raise ValueError("Invalid package-looks registry")
        for item in data["items"]:
            match = item.get("exactMatch", {})
            if not all(match.get(k) == item.get(k) for k in ["brand", "model", "den"]) or not match.get("brand") or not match.get("model"):
                raise ValueError("Unverified package look: " + str(item.get("id")))
            for p in item.get("photos", []):
                photos.append({**p, "id": "look-" + p["id"], "brand": match["brand"], "model": match["model"], "den": match["den"],
                               "denVerified": type(match["den"]) is int and match["den"] > 0, "category": p.get("category", "women"), "tags": p.get("tags", [])})
    ids = set()
    for p in photos:
        if not isinstance(p.get("id"), str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,100}", p["id"]) or p["id"] in ids:
            raise ValueError("Invalid/duplicate assistant photo id: " + str(p.get("id")))
        ids.add(p["id"])
        for field in ["src", "thumb"]:
            path = p.get(field, "")
            if not isinstance(path, str) or not re.fullmatch(r"assets/(?:[a-zA-Z0-9_-]+/)*[a-zA-Z0-9_-]+\.(?:jpe?g|png|webp|avif)", path):
                raise ValueError("Non-public assistant photo path: " + str(path))
            file = SITE / path
            if not file.is_file() or file.stat().st_size > 20 * 1024 * 1024:
                raise ValueError("Missing/oversized assistant photo: " + path)
        for field, limit in [("title", 160), ("alt", 360), ("caption", 600), ("sourceLabel", 120), ("credit", 240)]:
            if not isinstance(p.get(field), str) or not p[field].strip() or len(p[field]) > limit:
                raise ValueError("Invalid photo text: " + p["id"] + "/" + field)
        for field in ["width", "height"]:
            if type(p.get(field)) is not int or not 1 <= p[field] <= 20000:
                raise ValueError("Invalid photo dimensions: " + p["id"])
        if p.get("category") not in ["men", "couple", "women"] or type(p.get("denVerified")) is not bool:
            raise ValueError("Invalid photo category or DEN verification: " + p["id"])
        if p["denVerified"]:
            if type(p.get("den")) is not int or not 1 <= p["den"] <= 2000 or urlsplit(p.get("source", "")).scheme != "https":
                raise ValueError("Missing verified photo DEN/source: " + p["id"])
        else:
            p["den"] = None
    if len(photos) > 600:
        raise ValueError("Assistant photo registry exceeds 600 photos")
    # The public gallery may also import style-photos. Keep its richer canonical
    # entry rather than publishing two IDs for one file and showing it twice.
    unique = {}
    quality = lambda p: (p["denVerified"], not p["id"].startswith("gallery-"), bool(p.get("model")), bool(p.get("brand")))
    for p in photos:
        previous = unique.get(p["src"])
        if previous and previous["denVerified"] and p["denVerified"] and previous["den"] != p["den"]:
            raise ValueError("Conflicting verified DEN for photo: " + p["src"])
        if previous is None or quality(p) > quality(previous):
            unique[p["src"]] = p
    return sorted(unique.values(), key=lambda p: p["id"])


def news_documents(snapshot):
    """The same readable-text gate as the site; an image is never a substitute.

    Older snapshots may lack `publication`; then the structural gate still must
    pass. Explicit pending/failed records are always excluded, even with text.
    """
    ready = []
    for item in snapshot.get("items", []) if isinstance(snapshot, dict) else []:
        if not isinstance(item, dict) or not is_ready(item):
            continue
        publication = item.get("publication")
        if publication is not None and (not isinstance(publication, dict) or publication.get("status") != "ready"):
            continue
        ident = item.get("id", "")
        published = date(item.get("publishedAt"))
        title = item.get("displayTitle") or item.get("title")
        if not isinstance(ident, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,90}", ident) or not published or not isinstance(title, str) or not title.strip():
            continue
        source = plain(item.get("source", ""))[:120] or "указан в статье"
        prepared = "Автоматический AI-пересказ текста источника; возможны неточности." if item.get("ai") else "Подготовленный редакционный разбор по указанному источнику."
        lines = [f"Дата публикации источника: {published.date().isoformat()}. Источник: {source}. {prepared}", plain(item["summary"])]
        # Use only ready article text, never image/background captions or RSS excerpts.
        for section in item["sections"]:
            for paragraph in section["paragraphs"]:
                if sum(len(line) + 1 for line in lines) + len(paragraph) <= 1750:
                    lines.append(plain(paragraph))
        body = "\n".join(lines)[:1800]
        ready.append({"id": "news-" + ident, "kind": "news", "title": plain(title)[:220],
                      "href": "news.html#story-" + ident, "text": body,
                      "publishedAt": published.isoformat().replace("+00:00", "Z"),
                      "keywords": [source], "intents": ["news"]})
    return sorted(ready, key=lambda d: (d["publishedAt"], d["id"]), reverse=True)[:80]


def build_knowledge():
    documents = [dict(g) for g in GUIDES]
    brands = load_brands()
    for b in brands:
        slug, name = b["slug"], b["name"]
        text = b["summary"] + " Проверенные материалы и ссылки доступны в профиле бренда. "
        text += "Исторический статус карточки не подтверждает текущее наличие. "
        if b.get("status") == "archive":
            text += "На сайте бренд помечен как архивный; не предлагать его как подтверждённую текущую коллекцию. "
        models = b.get("models", [])
        text += "Примеры в справочнике: " + "; ".join(m["name"] for m in models) + "."
        documents.append({"id": "brand-" + slug, "kind": "brand", "brand": name, "brandKey": slug, "title": name + ": профиль и модели",
                          "href": "brand.html?" + urlencode({"brand": slug}), "text": text,
                          "aliases": [name, slug, *ALIASES.get(slug, [])], "keywords": [name, *ALIASES.get(slug, [])], "intents": ["catalog"]})
        for i, m in enumerate(models):
            documents.append({"id": f"model-{slug}-{i}", "kind": "model", "brand": name, "brandKey": slug,
                              "title": name + " " + m["name"], "href": "brand.html?" + urlencode({"brand": slug}),
                              "text": f"В справочнике ТОНКО: {name}, {m['name']}. Назначение из карточки: {m.get('use', '')}. Характеристики: {m.get('features', 'не уточнены')}. Тип источника: {m.get('sourceType', 'unknown')}. Это снимок редакционной карточки, не проверка текущего выпуска, состава для всех размеров или наличия. Размерная таблица не включена.",
                              "den": m["den"][0] if isinstance(m.get("den"), list) and len(m["den"]) == 2 and m["den"][0] == m["den"][1] else None,
                              "keywords": [name, m["name"]], "intents": ["catalog", "den", "material"]})
    rows = json.loads((SITE / "data/packaging.json").read_text(encoding="utf-8"))
    for p in rows:
        documents.append({"id": p["id"], "kind": "package", "brand": p["brand"], "brandKey": p["brandSlug"], "title": p["title"],
                          "href": "packaging.html?" + urlencode({"brand": p["brand"], "pack": p["id"]}),
                          "text": f"Архивное изображение упаковки / фирменного вкладыша {p['title']}, бренд {p['brand']}. DEN из названия карточки: {p.get('den') if p.get('den') is not None else 'не извлечён'}. Источник изображения: {p.get('sourceName', 'указан в карточке')}. Дата проверки источника: {p.get('checked', 'не указана')}. Можно открыть изображение и источник на сайте. Состав, размерная таблица, цена и текущее наличие в этих данных не подтверждены.",
                          "den": p.get("den"), "keywords": [p["brand"], p["title"], *(v["title"] for v in p.get("variants", []))], "intents": ["catalog"]})
    news_path = SITE / "data/news.json"
    if news_path.is_file():
        documents.extend(news_documents(json.loads(news_path.read_text(encoding="utf-8"))))
    for d in documents:
        assert (SITE / d["href"].split("?")[0].split("#")[0]).is_file(), d["href"]
    assert len({d["id"] for d in documents}) == len(documents)
    photos = photo_registry()
    canonical = json.dumps({"documents": documents, "photos": photos}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    snapshot = {"version": 1, "contentHash": hashlib.sha256(canonical.encode()).hexdigest(),
                "scope": "Редакционные материалы ТОНКО, архив упаковок, реестр фото и только готовые статьи новостей; без сырых RSS-анонсов, пользовательских сообщений и актуальных цен.", "documents": documents, "photos": photos}
    text = json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n"
    if len(documents) > 2500 or len(text.encode("utf-8")) > 2 * 1024 * 1024:
        raise ValueError("Assistant snapshot exceeds server limit: 2500 documents / 2 MiB")
    # Use the exact runtime validator before publishing either copy. A bad photo
    # registry must fail the build, not silently make Edge retain stale content.
    validation = """import {validateKnowledge} from './supabase/functions/tonko-assistant/knowledge-cache.mjs';
let text=''; for await (const chunk of process.stdin) text += chunk;
validateKnowledge(JSON.parse(text));"""
    subprocess.run(["node", "--input-type=module", "-e", validation], cwd=ROOT, input=text, encoding="utf-8", check=True)
    FUNCTION.mkdir(parents=True, exist_ok=True)
    (SITE / "data/assistant-knowledge.json").write_text(text, encoding="utf-8")
    (FUNCTION / "knowledge.json").write_text(text, encoding="utf-8")
    return len(documents)


def inject_pages():
    count = 0
    for path in SITE.glob("*.html"):
        if path.name == "fetish.html":
            continue
        text = path.read_text(encoding="utf-8")
        text = re.sub(r'<!-- tonko-assistant:(?:style|script) -->.*?<!-- /tonko-assistant -->\s*', '', text, flags=re.S)
        if "</head>" not in text or "</body>" not in text:
            continue
        text = text.replace("</head>", '<!-- tonko-assistant:style --><link rel="stylesheet" href="assistant.css?v=2"><!-- /tonko-assistant --></head>', 1)
        text = text.replace("</body>", '<!-- tonko-assistant:script --><script src="assistant.js?v=2" defer></script><!-- /tonko-assistant --></body>', 1)
        path.write_text(text, encoding="utf-8")
        count += 1
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inject", action="store_true", help="Add assistant CSS/JS to HTML pages, after other builders")
    args = parser.parse_args()
    print(f"Assistant knowledge: {build_knowledge()} records")
    if args.inject:
        print(f"Assistant added to {inject_pages()} pages")


if __name__ == "__main__":
    main()
