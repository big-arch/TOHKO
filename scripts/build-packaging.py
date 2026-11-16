"""Build the locally curated package archive. Run after build-videos.py."""
from pathlib import Path
import html,json,re
R=Path(__file__).resolve().parents[1];S=R/'tights-guide';esc=lambda s:html.escape(str(s),quote=True)
rows=json.loads((S/'data/packaging.json').read_text(encoding='utf-8'));brands=sorted({r['brand'] for r in rows})
assert len({r['id'] for r in rows})==len(rows)
for r in rows:
    assert (S/r['image']).is_file() and (S/r['thumbnail']).is_file()
    assert r['source'].startswith('https://')
(S/'data/packaging.js').write_text('window.TONKO_PACKAGING = '+json.dumps(rows,ensure_ascii=False).replace('<','\\u003c')+';\n',encoding='utf-8')
def card(r):
    return f'<article class="pack-card"><a class="pack-open" href="{esc(r["image"])}" data-pack="{r["id"]}" aria-label="Рассмотреть упаковку: {esc(r["title"])}"><img src="{esc(r["thumbnail"])}" alt="Упаковка {esc(r["title"])}" width="{r["width"]}" height="{r["height"]}" loading="lazy" decoding="async"></a><p>{esc(r["brand"])}</p><h2>{esc(r["title"])}</h2></article>'
body=f'''<section class="portal-container pack-intro"><p class="portal-eyebrow">Архив оформления</p><h1>Упаковки.<br>Узнаваемые с первого взгляда.</h1><div class="pack-intro-bottom"><p>Логотипы, оттенки, фотографии и обозначения. Рассмотрите упаковки и фирменные вкладыши, сравните оформление разных моделей.</p><p><strong>{len(rows)}</strong> изображений · <strong>{len(brands)}</strong> брендов<br><span>Источники и варианты указаны у каждого изображения.</span></p></div></section>
<section class="portal-container pack-collection" id="package-archive"><form class="pack-tools" role="search" hidden><label>Найти модель<input type="search" id="pack-search" placeholder="Например, Attiva, Conte или кашемир" autocomplete="off"></label><label>Бренд<select id="pack-brand"><option value="all">Все бренды</option>{''.join(f'<option value="{esc(b)}">{esc(b)} · {sum(r["brand"]==b for r in rows)}</option>' for b in brands)}</select></label><label>DEN в названии<select id="pack-den"><option value="all">Любая плотность</option><option value="thin">До 20</option><option value="medium">21–50</option><option value="dense">От 60</option><option value="unknown">Не указано</option></select></label><button id="pack-reset" type="button">Сбросить</button></form><p class="pack-count" id="pack-count" role="status">В архиве {len(rows)} изображений</p><div class="pack-grid" id="pack-grid">{''.join(card(r) for r in rows[:36])}</div><button class="pack-more" id="pack-more" type="button" hidden>Показать ещё 36</button><noscript><p>Показаны первые 36 изображений. Для поиска по полному архиву включите JavaScript.</p></noscript></section>
<section class="portal-container pack-about"><h2>Что можно прочитать на упаковке</h2><div><p>Сопоставьте название модели, состав, размерную сетку и обозначения ухода. Число DEN описывает линейную плотность нити; оно само по себе не гарантирует одинаковую прозрачность, тепло или прочность у разных изделий.</p><p>Архив объединяет фотографии упаковок, фирменные вкладыши и их каталожные изображения. Дизайн меняется со временем и может отличаться по рынкам. Плотность в фильтре извлечена из названия карточки: сверяйте её с самой упаковкой. Каталог пополняется и не является полным реестром всех выпусков.</p><a href="brands.html">Читать о брендах →</a></div></section>
<dialog class="pack-dialog" id="pack-dialog" aria-labelledby="pack-title"><div class="pack-dialog-bar"><span id="pack-position"></span><button type="button" id="pack-close" autofocus>Закрыть ×</button></div><div class="pack-dialog-layout"><div class="pack-image-area" id="pack-image-area"><img id="pack-full" alt=""></div><div class="pack-detail"><p class="portal-eyebrow" id="pack-label"></p><h2 id="pack-title"></h2><p id="pack-caption"></p><p class="pack-source-note">Изображение бренда из каталога. Актуальный состав и размеры уточняйте по упаковке конкретной пары.</p><div id="pack-variants"></div><a id="pack-source" target="_blank" rel="noopener noreferrer">Карточка источника ↗</a><div class="pack-dialog-actions"><button type="button" id="pack-previous" aria-label="Предыдущая упаковка">←</button><button type="button" id="pack-zoom" aria-pressed="false">Увеличить</button><button type="button" id="pack-next" aria-label="Следующая упаковка">→</button></div></div></div></dialog>'''
base=(S/'index.html').read_text(encoding='utf-8')
base=re.sub(r'<script[^>]*(?:news-seed|news-reader\.js|news\.js)[^>]*>.*?</script>','',base,flags=re.S)
text=re.sub(r'<main\b[^>]*>.*?</main>',lambda _:'<main id="content">'+body+'</main>',base,flags=re.S)
text=re.sub(r'<title>.*?</title>','<title>Упаковки колготок по брендам и моделям — ТОНКО</title>',text)
text=re.sub(r'<meta property="og:title" content="[^"]*">','<meta property="og:title" content="Архив упаковок колготок — ТОНКО">',text)
text=re.sub(r'<meta name="description" content="[^"]*">',f'<meta name="description" content="Архив ТОНКО: {len(rows)} изображений упаковок колготок, {len(brands)} брендов. Поиск, фильтры, увеличение и ссылки на источники.">',text)
text=text.replace('</head>','<link rel="stylesheet" href="packaging.css?v=9"></head>').replace('</body>','<script src="data/packaging.js?v=9"></script><script src="packaging.js?v=9"></script></body>')
(S/'packaging.html').write_text(text,encoding='utf-8')
for path in S.glob('*.html'):
    t=path.read_text(encoding='utf-8')
    nav=re.search(r'<nav\b.*?</nav>',t,re.S)
    if nav and '<a href="packaging.html"' not in nav[0]:
        t=t.replace('<a href="videos.html"', '<a href="packaging.html"'+(' class="active" aria-current="page"' if path.name=='packaging.html' else '')+'>Упаковки</a><a href="videos.html"',1)
    if path.name=='packaging.html':
        t=t.replace('<a href="packaging.html">Упаковки</a>','<a href="packaging.html" class="active" aria-current="page">Упаковки</a>',1)
    if path.name in ('lookbook.html','brands.html'):
        t=re.sub(r'<!-- pack-link -->.*?<!-- /pack-link -->','',t,flags=re.S)
        t=t.replace('</main>',f'<!-- pack-link --><section class="portal-container experience-related"><h2>Упаковки: {len(rows)} изображений</h2><p>{len(brands)} брендов, поиск по моделям и просмотр деталей.</p><a href="packaging.html">Открыть архив упаковок →</a></section><!-- /pack-link --></main>')
    if path.name=='sources.html':
        t=re.sub(r'<!-- pack-sources -->.*?<!-- /pack-sources -->','',t,flags=re.S)
        t=t.replace('</main>',f'<!-- pack-sources --><section class="portal-container experience-related"><h2>Архив упаковок</h2><p>{len(rows)} изображений упаковок и фирменных вкладышей {len(brands)} брендов. Источники: карточки Колготки-Онлайн, Nordstrom, отдельная фотография Wolford из eBay и ранее проверенные материалы Swedish Stockings, OMSA и Gabriella. У каждого изображения указана ссылка на конкретную карточку. Свободная лицензия на каталожные изображения не заявлена; товарные знаки принадлежат правообладателям.</p><p>Одинаковые изображения сгруппированы: варианты перечислены внутри карточки. Оформление и наличие могут меняться. Это пополняемый архив, а не исчерпывающий реестр всех упаковок.</p><a href="packaging.html">Открыть архив →</a></section><!-- /pack-sources --></main>')
    path.write_text(t,encoding='utf-8')
print(f'Packaging archive: {len(rows)} images, {len(brands)} brands')
