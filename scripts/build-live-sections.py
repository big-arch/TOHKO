"""Free, dated source updates beside the existing complete TONKO articles."""
from hashlib import sha256
from html import escape as H
from pathlib import Path
from urllib.parse import urlsplit
import json
import re
from news_publication import is_ready
from news_render import newest_publications, publication_markup, publication_time

SITE = Path(__file__).resolve().parents[1] / 'tights-guide'
MEN = re.compile(r'мужск|мужчин|\bmen\b|\bmens\b|\bmale\b|męsk', re.I)
EXCLUDE = re.compile(r'фетиш|эроти|порно|fetish|erotic|porn|intimacy|crotchless|black (?:week|friday)|cyber monday|скидк|rabat|zniżk', re.I)


def prepare(news, publisher, media):
    photos = {p['id']: p for p in media if p.get('origin') == 'feed'}
    extras = [{'id': p['id'], 'title': p['title'], 'url': p['url'], 'source': p['sourceName'],
               'sourceId': p['sourceId'], 'language': p['language'], 'excerpt': p['excerpt'],
               'publishedAt': p['publishedAt'], 'mediaId': p.get('mediaId')} for p in publisher.get('items', [])]
    items, seen, seen_titles = [], set(), set()
    # Keep a full on-site article when its URL also occurs in a fresh feed.
    candidates = sorted(news.get('items', []) + extras, key=lambda p: is_ready(p), reverse=True)
    photo_for_url = {p['source']: p for p in photos.values()}
    for p in candidates:
        # A visible article always has its complete Russian edition on TONKO.
        if not is_ready(p):
            continue
        url = p.get('publisherUrl') or p.get('url', '')
        u = urlsplit(url)
        title = p.get('displayTitle') or p.get('title', '')
        if u.scheme != 'https' or not u.hostname or u.username or u.password or not title or EXCLUDE.search(title):
            continue
        title_key = re.sub(r'\W+', ' ', p.get('title', '').casefold()).strip()
        if url in seen or title_key in seen_titles:
            continue
        seen.add(url)
        seen_titles.add(title_key)
        ready = is_ready(p)
        text = p.get('summary') if ready else p.get('excerpt', '')
        text = ' '.join((text or '').split()[:35 if ready else 18])
        if text:
            text = text.rstrip('.…') + '…'
        image = photo_for_url.get(url)
        if p.get('illustration'):
            photo=p['illustration']
            image={'image':photo['src'],'alt':photo.get('alt',''),'width':photo.get('width',1000),
                   'height':photo.get('height',750),'srcset':''}
        items.append({'id': p['id'], 'title': title, 'excerpt': text, 'source': p['source'],
                      'via': 'Google News' if u.hostname == 'news.google.com' else None,
                      'publishedAt': p.get('publishedAt'), 'language': p.get('language', 'en'),
                      'ready': ready, 'url': 'news.html#story-' + p['id'] if ready else url,
                      'article': p,
                      'men': p.get('sourceId') == 'nylo' or bool(MEN.search(title + ' ' + (text or ''))),
                      'image': {'src': image['image'], 'alt': image['alt'], 'width': image['width'], 'height': image['height'], 'srcset': image.get('srcset', '')} if image else None})
    return {'version': 1, 'checkedAt': news.get('lastSuccessfulAt'), 'photoCheckedAt': publisher.get('checkedAt'),
            'sourcesFailed': sum(p.get('status') != 'ok' for p in news.get('sources', [])),
            'items': newest_publications(items)[:180],
            'photos': sorted(photos.values(), key=lambda p: p.get('publishedAt') or '', reverse=True)}


def render_item(item):
    external = '' if item['ready'] else ' target="_blank" rel="noopener noreferrer"'
    image = item.get('image')
    photo = ''
    if image:
        photo = f'<img src="{H(image["src"])}" alt="{H(image["alt"])}" width="{image["width"]}" height="{image["height"]}" loading="lazy" decoding="async" srcset="{H(image.get("srcset", ""))}" sizes="(max-width:700px) 90vw, 40vw">'
    return (f'<article class="live-item" data-live-item="{H(item["id"])}">{photo}<div class="live-meta"><span>{H(item["source"])}</span>{publication_markup(item["publishedAt"])}</div>'
            f'<h3><a href="{H(item["url"])}"{external}>{H(item["title"])}</a></h3>'
            + (f'<p lang="ru">{H(item["excerpt"])}</p>' if item['excerpt'] else '')
            + f'<a class="live-link" href="{H(item["url"])}"{external}>{"Читать на ТОНКО →" if item["ready"] else "Открыть через Google News ↗" if item.get("via") else "Полный текст у источника ↗"}</a></article>')


def block(data, audience, title):
    items = [p for p in data['items'] if audience != 'men' or p['men']]
    return (f'<section class="portal-container live-section" data-live-feed="{audience}" id="live-{audience}">'
            f'<p class="portal-eyebrow">Обновляется из источников</p><h2>{H(title)}</h2>'
            '<p class="live-intro">Статьи и обзоры на русском. Открывайте и читайте здесь — источник указан под текстом.</p>'
            '<p class="live-status" role="status"></p><button type="button" class="live-refresh" hidden>Появились обновления. Показать</button>'
            '<div class="live-filters" role="group" aria-label="Источники материалов" hidden><button type="button" data-live-filter="all" aria-pressed="true">Все материалы</button>'
            '<button type="button" data-live-filter="ru" aria-pressed="false">Российские источники</button><button type="button" data-live-filter="translated" aria-pressed="false">Зарубежные — по-русски</button></div>'
            '<div class="live-list">' + ''.join(render_item(p) for p in items[:6]) + '</div><button type="button" class="live-more" hidden>Ещё публикации</button>'
            '<noscript><p><a href="news.html">Полные статьи ТОНКО →</a>. Перезагрузите страницу для обновления подборки.</p></noscript></section>')


def build():
    news = json.loads((SITE / 'data/news.json').read_text(encoding='utf-8'))
    publisher = json.loads((SITE / 'data/publisher-feed.json').read_text(encoding='utf-8'))
    media = json.loads((SITE / 'data/editorial-media.json').read_text(encoding='utf-8'))
    data = prepare(news, publisher, media)
    (SITE / 'data/live-feed.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    gallery = ('<section class="portal-container live-section" id="live-gallery"><p class="portal-eyebrow">Поступления из публикаций брендов</p><h2>Новые фотографии</h2>'
               '<p class="live-intro">Галерея пополняется из выбранных официальных журналов. Дата относится к публикации бренда; источник каждого кадра доступен в просмотрщике.</p>'
               '<p class="live-photo-status"></p><div class="live-photos">' + ''.join(
                   f'<figure><a href="lookbook.html?filter=updates#photo-{p["id"]}"><img src="{H(p["image"])}" alt="{H(p["alt"])}" width="{p["width"]}" height="{p["height"]}" loading="lazy" srcset="{H(p.get("srcset", ""))}" sizes="(max-width:700px) 45vw, 30vw"></a><figcaption>{H(p["author"])} · {publication_markup(p.get("publishedAt"))}</figcaption></figure>' for p in data['photos'][:3])
               + '</div><a class="live-link" href="lookbook.html?filter=updates#photo-collection">Все поступления →</a></section>')
    sections = {'index.html': block(data, 'home', 'Читайте на ТОНКО'),
                'journal.html': block(data, 'journal', 'Новые публикации'),
                'men.html': block(data, 'men', 'Новое о мужском гардеробе'), 'lookbook.html': gallery}
    seed = json.dumps(data, ensure_ascii=False).replace('<', '\\u003c')
    for filename, content in sections.items():
        path = SITE / filename
        text = path.read_text(encoding='utf-8')
        text = re.sub(r'<!-- live-sections -->.*?<!-- /live-sections -->', '', text, flags=re.S)
        text = re.sub(r'<!-- live-photo-filter -->.*?<!-- /live-photo-filter -->', '', text, flags=re.S)
        text = re.sub(r'<script id="live-seed".*?</script>', '', text, flags=re.S)
        text = re.sub(r'<script src="live-sections\.js[^"]*"[^>]*></script>|<link rel="stylesheet" href="live-sections\.css[^"]*">', '', text)
        if filename == 'index.html':
            anchor = '<div class="news-toolbar">'
            # A secondary free source feed belongs to the existing fashion section.
            content = content.replace('class="portal-container live-section"', 'class="live-section live-home"')
            if anchor not in text:
                raise ValueError('Fashion feed insertion point missing')
            content += '<h3 class="live-ready-title">Готовые разборы ТОНКО</h3>'
            text = text.replace(anchor, '<!-- live-sections -->' + content + '<!-- /live-sections -->' + anchor, 1)
        else:
            point = text.index('</section>', text.index('<main')) + len('</section>')
            text = text[:point] + '<!-- live-sections -->' + content + '<!-- /live-sections -->' + text[point:]
        if filename == 'journal.html':
            text = text.replace('Журнал ТОНКО · Выпуск 01', 'Журнал ТОНКО').replace('Материалы выпуска', 'Авторские разборы ТОНКО')
        if filename == 'lookbook.html':
            text = re.sub(r'(<button[^>]+data-gallery-filter="all"[^>]*>.*?</button>)',
                          r'\1<!-- live-photo-filter --><button type="button" data-gallery-filter="updates" aria-pressed="false">Новые из публикаций</button><!-- /live-photo-filter -->', text, count=1)
        css = sha256((SITE / 'live-sections.css').read_bytes()).hexdigest()[:12]
        js = sha256((SITE / 'live-sections.js').read_bytes()).hexdigest()[:12]
        text = text.replace('</head>', f'<link rel="stylesheet" href="live-sections.css?v={css}"></head>')
        text = text.replace('</body>', f'<script id="live-seed" type="application/json">{seed}</script><script src="live-sections.js?v={js}" defer></script></body>')
        if filename!='lookbook.html':
            if 'src="publication-dates.js' not in text:
                text=text.replace('</head>','<script src="publication-dates.js?v=20261117-17" defer></script></head>')
            if 'href="news-reader.css' not in text:
                text=text.replace('</head>','<link rel="stylesheet" href="news-reader.css?v=20261117-17"></head>')
            if 'src="news-reader.js' not in text:
                text=text.replace('<script id="live-seed"','<script src="news-reader.js" defer></script><script id="live-seed"')
            version=sha256((SITE/'news-reader.js').read_bytes()).hexdigest()[:12]
            text=re.sub(r'news-reader\.js(?:\?v=[^"\s]+)?','news-reader.js?v='+version,text)
        path.write_text(text, encoding='utf-8')
    version = sha256((SITE / 'editorial.js').read_bytes()).hexdigest()[:12]
    for path in SITE.glob('*.html'):
        text = path.read_text(encoding='utf-8')
        text = re.sub(r'(["\'])editorial\.js(?:\?v=[^"\']*)?(["\'])', lambda m: m[1] + 'editorial.js?v=' + version + m[2], text)
        path.write_text(text, encoding='utf-8')
    print(f'Live sections: {len(data["items"])} source records, {sum(p["men"] for p in data["items"])} men, {len(data["photos"])} new photos')


if __name__ == '__main__':
    build()
