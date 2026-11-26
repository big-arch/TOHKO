"""Build the journal's hands-on series and the industry dossier for each Pages edition."""
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "tights-guide"
TEMPLATES = ROOT / "scripts" / "series"
ARCHIVE = json.loads((TEMPLATES / "archive-objects.json").read_text("utf-8"))
MEDIA = {row["id"]: row for row in json.loads((SITE / "data/editorial-media.json").read_text("utf-8"))}
MEDIA.update({row["key"]: row for row in ARCHIVE})


def versioned(filename):
    return filename + "?v=" + sha256((SITE / filename).read_bytes()).hexdigest()[:12]


def photo(key, eager=False):
    item = MEDIA[key]
    path, width, height, alt = (item[name] for name in ("image", "width", "height", "alt"))
    srcset = ", ".join(f'{size["src"]} {size["width"]}w' for size in item["responsive"])
    loading = 'loading="eager" fetchpriority="high"' if eager else 'loading="lazy"'
    return (f'<img src="{path}" srcset="{srcset}" sizes="(max-width: 720px) 100vw, (max-width: 1400px) 50vw, 720px" '
            f'width="{width}" height="{height}" alt="{escape(alt, quote=True)}" {loading} decoding="async">')


def template(name, values):
    source = (TEMPLATES / (name + ".html")).read_text("utf-8")
    return re.sub(r"\{\{([a-z_]+)\}\}", lambda match: values[match[1]], source)


def wear_days():
    days = []
    for number in range(1, 6):
        days.append(f'''<details class="diary-day"{' open' if number == 1 else ''}>
  <summary><span>Носка {number}</span><span class="day-state" id="day-state-{number}">Без записи</span></summary>
  <div class="day-fields">
    <label>Дата носки<input type="date" name="date-{number}" aria-label="Дата носки {number}"></label>
    <label>Обувь<input type="text" name="shoes-{number}" maxlength="100" placeholder="Например, лоферы"></label>
    <label>Стирка после носки<select name="wash-{number}"><option value="">Не отмечено</option><option>Без стирки</option><option>Вручную</option><option>В машине</option></select></label>
    <label class="day-note">Что заметили?<textarea name="note-{number}" maxlength="1000" rows="2" placeholder="Мысок, пятка, пояс, зацепки или посадка"></textarea></label>
  </div></details>''')
    return "\n".join(days)


def wear_uploads():
    cards = []
    for key, label in (("before", "До первой носки"), ("after", "После пятой носки")):
        cards.append(f'''<div class="diary-upload">
  <label for="wear-{key}">{label}</label>
  <img data-preview="{key}" alt="Фото пары — {label.lower()}" hidden>
  <input type="file" id="wear-{key}" data-wear-photo="{key}" accept="image/jpeg,image/png,image/webp">
  <button class="series-quiet" type="button" data-remove-photo="{key}" hidden>Убрать фото</button></div>''')
    return "\n".join(cards)


def clear_block(text, name):
    return re.sub(r"<!-- " + name + r" -->.*?<!-- /" + name + r" -->", "", text, flags=re.S)


def before(text, marker, content):
    if marker not in text:
        raise ValueError("Missing series insertion point: " + marker)
    return text.replace(marker, content + marker, 1)


def block(name, html):
    return f"<!-- {name} -->{html}<!-- /{name} -->"


def assets(text, include_script):
    style = f'<link rel="stylesheet" href="{versioned("journal-series.css")}">'
    text = clear_block(clear_block(text, "journal-series:style"), "journal-series:script")
    style_at = "<!-- tonko-assistant:style -->" if "<!-- tonko-assistant:style -->" in text else "</head>"
    text = before(text, style_at, block("journal-series:style", style))
    if include_script:
        script_at = "<!-- tonko-assistant:script -->" if "<!-- tonko-assistant:script -->" in text else "</body>"
        script = f'<script src="{versioned("journal-series.js")}" defer></script>'
        text = before(text, script_at, block("journal-series:script", script))
    return text


def save(path, text):
    if not path.exists() or path.read_text("utf-8") != text:
        path.write_text(text, encoding="utf-8")


def article(journal, title, description, cover_image, body):
    def element(name):
        return re.search(fr"<{name}\b[^>]*>.*?</{name}>", journal, re.S)[0]

    # Use the published navigation and type system; feed payloads belong only to their own pages.
    shared_links = "".join(link for link in re.findall(r"<link\b[^>]*>", element("head"))
                           if re.search(r'assets/favicon|fonts\.(googleapis|gstatic)|href="(portal|tonko|editorial|experience)\.css', link))
    assistant = {kind: re.search(rf"<!-- tonko-assistant:{kind} -->.*?<!-- /tonko-assistant -->", journal, re.S)
                 for kind in ("style", "script")}
    page_title = escape(title + " — ТОНКО", quote=True)
    header = element("header").replace('aria-current="page"', 'aria-current="location"')
    html = f'''<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{page_title}</title><meta name="description" content="{escape(description, quote=True)}">
<meta property="og:title" content="{page_title}"><meta property="og:image" content="https://big-arch.github.io/TOHKO/{cover_image}">
{shared_links}{assistant["style"][0] if assistant["style"] else ""}</head>
<body><a class="portal-skip" href="#content">Перейти к содержимому</a>{header}
<main id="content">{body}</main>{element("footer")}
<script src="portal.js" defer></script>{assistant["script"][0] if assistant["script"] else ""}</body></html>'''
    return assets(html, True)


def archive_article(journal, item):
    values = {key: escape(item[key]) for key in ("key", "title", "lead", "article_title", "credit")}
    values.update({
        "archive_original": item["image"],
        "archive_photo": photo(item["key"], True),
        "facts": "".join(f"<div><dt>{escape(label)}</dt><dd>{escape(value)}</dd></div>" for label, value in item["facts"]),
        "paragraphs": "\n".join(f"<p>{escape(p)}</p>" for p in item["paragraphs"]),
        "whole_caption": escape(item["views"][0][2]),
        "buttons": "\n".join(f'<button type="button" data-archive-view="{key}" data-caption="{escape(caption, quote=True)}" '
                             f'aria-pressed="{str(key == "whole").lower()}">{escape(label)}</button>'
                             for key, label, caption in item["views"]),
        "sources": " ".join(f'<a href="{escape(url, quote=True)}">{escape(label)} ↗</a>' for label, url in item["sources"]),
        "other_objects": " ".join(f'<a href="{other["slug"]}.html">Из архива. {escape(other["title"])} →</a>'
                                  for other in ARCHIVE if other["key"] != item["key"])
    })
    title = "Одна вещь из архива. " + item["title"]
    return article(journal, title, item["lead"], item["image"], template("one-from-the-archive", values))


def build():
    journal_path = SITE / "journal.html"
    journal = clear_block(journal_path.read_text("utf-8"), "journal-series")
    covers = f'''<section class="portal-container journal-series" id="journal-series" aria-labelledby="series-title">
  <h2 id="series-title">Рубрики журнала</h2>
  <div class="series-cards">
    <a href="five-wears.html"><div class="series-thumb wear-thumb">{photo("wolford-3")}</div><div><h3>После пяти носок</h3><p>Одна пара, пять записей и ваши фотографии до и после.</p><span>Открыть дневник →</span></div></a>
    <div class="archive-card"><a href="one-from-the-archive.html"><div class="series-thumb museum-thumb">{photo("museum")}</div><div><h3>Одна вещь из архива</h3><p>Опытные чулки 1937 года. Разглядываем нейлон, шёлк и шов.</p><span>Рассмотреть пару →</span></div></a><a class="other-issue" href="archive-blue-silk.html">Ещё выпуск · Золото на синем шёлке →</a></div>
  </div></section>'''
    end = journal.index("</section>", journal.index('<section class="journal-cover')) + len("</section>")
    journal = assets(journal[:end] + block("journal-series", covers) + journal[end:], False)
    save(journal_path, journal)

    wear = template("five-wears", {"wear_photo": photo("wolford-3", True), "wear_credit": MEDIA["wolford-3"]["source"],
                                   "wear_days": wear_days(), "wear_uploads": wear_uploads()})
    save(SITE / "five-wears.html", article(journal, "После пяти носок", "Дневник одной пары с наблюдениями и фотографиями.",
                                           MEDIA["wolford-3"]["image"], wear))
    for item in ARCHIVE:
        save(SITE / (item["slug"] + ".html"), archive_article(journal, item))

    path = SITE / "business.html"
    business = clear_block(clear_block(path.read_text("utf-8"), "industry-dossier"), "industry-contents")
    links = '<a href="#factory-floor">На фабрике</a><a href="#private-label">Чья марка</a><a href="#batch-plan">План партии</a>'
    business = before(business, '<a href="#business-cases">', block("industry-contents", links))
    dossier = template("industry", {"factory_photo": photo("swedish-factory"), "factory_credit": MEDIA["swedish-factory"]["source"]})
    business = before(business, '<section class="portal-container business-cases"', block("industry-dossier", dossier))
    save(path, assets(business, True))
    print("Journal series and industry dossier built.")


if __name__ == "__main__":
    build()
