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
from urllib.parse import urlencode

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
          "Перед надеванием снимите украшения, проверьте ногти, соберите ногу изделия до мыска и распределяйте полотно постепенно. Перед стиркой сверьтесь с ярлыком конкретной пары. Держите тонкие изделия отдельно от молний, крючков и липучек. Температура, машинная стирка, отбеливание и способ сушки зависят от материала и указаний производителя. Универсальный режим для всех моделей не утверждается.", ["care"], ["стирка", "сушка", "зацепка", "надевать", "уход"]),
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
    canonical = json.dumps(documents, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    snapshot = {"version": 1, "contentHash": hashlib.sha256(canonical.encode()).hexdigest(),
                "scope": "Редакционные материалы ТОНКО, архив упаковок и только готовые статьи новостей; без сырых RSS-анонсов, пользовательских сообщений и актуальных цен.", "documents": documents}
    text = json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n"
    if len(documents) > 2500 or len(text.encode("utf-8")) > 2 * 1024 * 1024:
        raise ValueError("Assistant snapshot exceeds server limit: 2500 documents / 2 MiB")
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
        text = text.replace("</head>", '<!-- tonko-assistant:style --><link rel="stylesheet" href="assistant.css?v=1"><!-- /tonko-assistant --></head>', 1)
        text = text.replace("</body>", '<!-- tonko-assistant:script --><script src="assistant.js?v=1" defer></script><!-- /tonko-assistant --></body>', 1)
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
