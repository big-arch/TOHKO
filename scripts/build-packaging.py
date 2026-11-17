"""Build the locally curated package archive. Run after build-videos.py."""
from pathlib import Path
import argparse,hashlib,html,json,re,unicodedata
from urllib.parse import urlsplit
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--packaging-only',action='store_true',help='Rebuild only the archive page and its data; leave other pages untouched.')
args=parser.parse_args()
R=Path(__file__).resolve().parents[1];S=R/'tights-guide';esc=lambda s:html.escape(str(s),quote=True)
def order(value):
    return unicodedata.normalize('NFKD',value).casefold()
rows=sorted(json.loads((S/'data/packaging.json').read_text(encoding='utf-8')),key=lambda r:(order(r['brand']),order(r['title'])))
brands=sorted({r['brand'] for r in rows},key=order)
assert len({r['id'] for r in rows})==len(rows)
for r in rows:
    assert (S/r['image']).is_file() and (S/r['thumbnail']).is_file()
    assert r['source'].startswith('https://')
(S/'data/packaging.js').write_text('window.TONKO_PACKAGING = '+json.dumps(rows,ensure_ascii=False).replace('<','\\u003c')+';\n',encoding='utf-8')

# Exact model photographs are reviewed independently of the package archive.
looks_path=S/'data/package-looks.json'
looks=json.loads(looks_path.read_text(encoding='utf-8')) if looks_path.exists() else {'version':1,'items':[]}
package_by_id={r['id']:r for r in rows}
photo_ids=set();assigned_packages=set()
for item in looks['items']:
    assert item['photos'] and item['packageIds'],item['id']
    for package_id in item['packageIds']:
        package=package_by_id[package_id]
        assert package['brand']==item['exactMatch']['brand'] and package['den']==item['exactMatch']['den'],item['id']
        assert package['title'] in item['packageTitles'] and package_id not in assigned_packages,item['id']
        assigned_packages.add(package_id)
    for photo in item['photos']:
        assert photo['id'] not in photo_ids,photo['id']
        photo_ids.add(photo['id'])
        assert photo['source'].startswith('https://') and photo['imageSource'].startswith('https://')
        for key in ('src','thumb'):
            assert photo[key].startswith('assets/package-looks/') and '..' not in photo[key]
            assert (S/photo[key]).is_file(),photo[key]
(S/'data/package-looks.js').write_text('window.TONKO_PACKAGE_LOOKS = '+json.dumps(looks,ensure_ascii=False).replace('<','\\u003c')+';\n',encoding='utf-8')

# Brand history is explicitly sourced; no generic gallery images are substituted.
stories=json.loads((S/'data/brand-stories.json').read_text(encoding='utf-8'))
assert stories['version']==1 and isinstance(stories['items'],list)
story_brands=set()
for story in stories['items']:
    assert story['brand'] not in story_brands,story['brand']
    story_brands.add(story['brand'])
    assert story['title'] and 1<=len(story['paragraphs'])<=3 and all(isinstance(p,str) and 20<=len(p)<=1500 for p in story['paragraphs']),story['brand']
    assert story['sources'] and all(s['title'] and urlsplit(s['url']).scheme=='https' and urlsplit(s['url']).netloc for s in story['sources']),story['brand']
    photo=story['photo']
    if photo is None:
        continue  # A sourced text is preferable to a photograph of another brand.
    assert all(photo.get(key) for key in ('alt','caption','credit','license')),story['brand']
    assert all(urlsplit(photo[key]).scheme=='https' and urlsplit(photo[key]).netloc for key in ('source','imageSource')),story['brand']
    assert isinstance(photo['width'],int) and photo['width']>0 and isinstance(photo['height'],int) and photo['height']>0
    for key in ('src','thumb'):
        asset=(S/photo[key]).resolve()
        assert photo[key].startswith('assets/') and asset.is_relative_to(S.resolve()) and asset.is_file(),photo[key]
assert set(brands)<=story_brands,'Missing brand stories: '+', '.join(sorted(set(brands)-story_brands))
(S/'data/brand-stories.js').write_text('window.TONKO_BRAND_STORIES = '+json.dumps(stories,ensure_ascii=False).replace('<','\\u003c')+';\n',encoding='utf-8')
price_assets=('data/catalog-prices.js','data/exchange-rate.js','catalog.js')
price_assets=tuple(path for path in price_assets if (S/path).exists())
version=hashlib.sha256(b''.join((S/path).read_bytes() for path in ('data/packaging.js','data/package-looks.js','data/brand-stories.js','packaging.js','packaging.css')+price_assets)).hexdigest()[:12]
def card(r):
    return f'<article class="pack-card"><a class="pack-open" href="{esc(r["image"])}" data-pack="{esc(r["id"])}" aria-label="Рассмотреть упаковку: {esc(r["title"])}"><img src="{esc(r["thumbnail"])}" alt="Упаковка {esc(r["title"])}" width="{r["width"]}" height="{r["height"]}" loading="lazy" decoding="async"></a><h3>{esc(r["title"])}</h3></article>'
def group(brand):
    items=[r for r in rows if r['brand']==brand]
    kinds={kind:sum(r.get('productKind','колготки')==kind for r in items) for kind in ('колготки','чулки','гольфы','легинсы')}
    note='<p class="pack-kind-note">Типы изделий: '+', '.join(f'{kind} — {count}' for kind,count in kinds.items() if count)+'.</p>' if any(kinds[kind] for kind in ('чулки','гольфы','легинсы')) else ''
    return f'<section class="pack-brand-section" data-brand-section="{esc(brand)}" aria-labelledby="brand-{esc(items[0]["brandSlug"])}"><header class="pack-brand-heading"><h2 id="brand-{esc(items[0]["brandSlug"])}">{esc(brand)}</h2><p>Упаковок: {len(items)}</p></header>'+note+'<div class="pack-grid">'+''.join(card(r) for r in items)+'</div></section>'
brand_links='<a href="#package-archive" data-brand="all" aria-current="true"><span>Все бренды</span><span class="pack-brand-total">'+str(len(rows))+'</span></a>'
for brand in brands:
    items=[r for r in rows if r['brand']==brand]
    brand_links+=f'<a href="#brand-{esc(items[0]["brandSlug"])}" data-brand="{esc(brand)}"><span>{esc(brand)}</span><span class="pack-brand-total">{len(items)}</span></a>'
body=f'''<section class="portal-container pack-intro"><p class="portal-eyebrow">Архив оформления</p><h1>Упаковки по брендам.</h1><div class="pack-intro-bottom"><p>Коллекция по брендам, от Conte до Wolford. Выберите производителя, найдите модель и рассмотрите её упаковку в деталях.</p><p><strong>{len(rows)}</strong> изображений · <strong>{len(brands)}</strong> брендов<br><span>Источники и варианты указаны у каждого изображения.</span></p></div></section>
<div class="portal-container pack-browser"><details class="pack-brand-directory" id="pack-directory" open><summary><span>Бренды в архиве</span><span class="pack-directory-toggle" aria-hidden="true">+</span></summary><p>По алфавиту. Число рядом с названием показывает количество упаковок.</p><nav id="pack-brand-links" aria-label="Выбрать бренд упаковок">{brand_links}</nav></details>
<section class="pack-collection" id="package-archive"><form class="pack-tools" role="search" hidden><label>Найти модель<input type="search" id="pack-search" placeholder="Например, Attiva, Conte или кашемир" autocomplete="off"></label><label>Бренд<select id="pack-brand"><option value="all">Все бренды</option>{''.join(f'<option value="{esc(b)}">{esc(b)} · {sum(r["brand"]==b for r in rows)}</option>' for b in brands)}</select></label><label>DEN в названии<select id="pack-den"><option value="all">Любая плотность</option><option value="thin">До 20</option><option value="medium">21–50</option><option value="dense">От 60</option><option value="unknown">Не указано</option></select></label><button id="pack-reset" type="button">Сбросить</button></form><p class="pack-count" id="pack-count" role="status">В архиве {len(rows)} изображений</p><div class="pack-groups" id="pack-grid">{''.join(group(b) for b in brands)}</div><noscript><p>Показан полный архив по брендам. Для поиска и фильтров включите JavaScript.</p></noscript></section></div>
<section class="portal-container pack-about"><h2>Что можно прочитать на упаковке</h2><div><p>Сопоставьте название модели, состав, размерную сетку и обозначения ухода. Число DEN описывает линейную плотность нити; оно само по себе не гарантирует одинаковую прозрачность, тепло или прочность у разных изделий.</p><p>Архив объединяет фотографии упаковок, фирменные вкладыши и их каталожные изображения. Дизайн меняется со временем и может отличаться по рынкам. Плотность в фильтре извлечена из названия карточки: сверяйте её с самой упаковкой. Каталог пополняется и не является полным реестром всех выпусков.</p><a href="brands.html">Читать о брендах →</a></div></section>
<dialog class="pack-dialog" id="pack-dialog" aria-labelledby="pack-title"><div class="pack-dialog-bar"><span id="pack-position"></span><button type="button" id="pack-close" autofocus>Закрыть ×</button></div><div class="pack-dialog-layout"><div class="pack-image-area" id="pack-image-area"><img id="pack-full" alt=""></div><div class="pack-detail"><p class="portal-eyebrow" id="pack-label"></p><h2 id="pack-title"></h2><p id="pack-caption"></p><p class="pack-source-note">Изображение бренда из каталога. Актуальный состав и размеры уточняйте по упаковке конкретной пары.</p><div id="pack-variants"></div><a id="pack-source" target="_blank" rel="noopener noreferrer">Карточка источника ↗</a><div class="pack-dialog-actions"><button type="button" id="pack-previous" aria-label="Предыдущая упаковка">←</button><button type="button" id="pack-zoom" aria-pressed="false">Увеличить</button><button type="button" id="pack-next" aria-label="Следующая упаковка">→</button></div></div></div></dialog>'''
body=body.replace('<div id="pack-variants"></div>','<dl class="pack-facts" id="pack-facts"></dl><div id="pack-variants"></div>')
if price_assets:
    body=body.replace('<dl class="pack-facts"', '<div class="pack-retail" id="pack-retail"></div><dl class="pack-facts"',1)
brand_section='''<section class="pack-brand-story" id="pack-brand-story" aria-labelledby="pack-brand-story-title" hidden>
<div class="pack-brand-story-heading"><p class="portal-eyebrow" id="pack-brand-story-meta"></p><h3 id="pack-brand-story-title"></h3><p class="pack-brand-story-subtitle" id="pack-brand-story-subtitle"></p></div>
<figure class="pack-brand-figure"><button type="button" class="pack-brand-photo-open" id="pack-brand-photo-open" aria-label="Увеличить фотографию бренда"><img id="pack-brand-photo" alt="" decoding="async"><span aria-hidden="true">↗</span></button><figcaption><span id="pack-brand-photo-caption"></span><small id="pack-brand-photo-credit"></small></figcaption></figure>
<div class="pack-brand-story-text" id="pack-brand-story-text"></div><details class="pack-brand-story-sources"><summary>Источники истории</summary><div id="pack-brand-story-sources"></div></details></section>'''
model_section='''<section class="pack-looks" aria-labelledby="pack-looks-title" hidden><h3 id="pack-looks-title"></h3><p class="pack-looks-note" id="pack-looks-note"></p><div class="pack-looks-grid" id="pack-looks-grid"></div></section>'''
photo_dialog='''<dialog class="pack-photo-dialog" id="pack-photo-dialog" aria-labelledby="pack-photo-title"><div class="pack-photo-bar"><span id="pack-photo-position"></span><button type="button" id="pack-photo-close" autofocus>Закрыть фото ×</button></div><div class="pack-photo-stage"><img id="pack-photo-full" alt=""></div><div class="pack-photo-info"><p id="pack-photo-match"></p><h2 id="pack-photo-title"></h2><p id="pack-photo-caption"></p><a id="pack-photo-source" target="_blank" rel="noopener noreferrer">Источник фотографии ↗</a><div class="pack-photo-navigation"><button type="button" id="pack-photo-previous" aria-label="Предыдущее фото">←</button><button type="button" id="pack-photo-next" aria-label="Следующее фото">→</button></div></div></dialog>'''
body=body.replace('</div></div></div></dialog>','</div>'+brand_section+model_section+'</div></div></dialog>'+photo_dialog)
base=(S/'index.html').read_text(encoding='utf-8')
base=re.sub(r'<script[^>]*(?:news-seed|news-reader\.js|news\.js)[^>]*>.*?</script>','',base,flags=re.S)
text=re.sub(r'<main\b[^>]*>.*?</main>',lambda _:'<main id="content">'+body+'</main>',base,flags=re.S)
text=re.sub(r'<title>.*?</title>','<title>Упаковки колготок по брендам и моделям — ТОНКО</title>',text)
text=re.sub(r'<meta property="og:title" content="[^"]*">','<meta property="og:title" content="Архив упаковок колготок — ТОНКО">',text)
text=re.sub(r'<meta name="description" content="[^"]*">',f'<meta name="description" content="Архив ТОНКО: {len(rows)} изображений упаковок колготок, {len(brands)} брендов. Поиск, фильтры, увеличение и ссылки на источники.">',text)
price_scripts=''.join(f'<script src="{path}?v={version}"></script>' for path in price_assets)
text=text.replace('</head>',f'<link rel="stylesheet" href="packaging.css?v={version}"></head>').replace('</body>',f'<script src="data/packaging.js?v={version}"></script><script src="data/package-looks.js?v={version}"></script><script src="data/brand-stories.js?v={version}"></script>'+price_scripts+f'<script src="packaging.js?v={version}"></script></body>')
(S/'packaging.html').write_text(text,encoding='utf-8')
for path in ([S/'packaging.html'] if args.packaging_only else S.glob('*.html')):
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
        t=t.replace('</main>',f'<!-- pack-sources --><section class="portal-container experience-related"><h2>Архив упаковок</h2><p>{len(rows)} изображений упаковок и фирменных вкладышей {len(brands)} брендов. Источники: каталоги Колготки-Онлайн, КолготкиОпт, Nbielizna, MAKEUP и других продавцов, фотографии Nordstrom и eBay, материалы Swedish Stockings, OMSA и Gabriella. У каждого изображения указан источник; архив также содержит фотографии из обзоров и материалы брендов. Колготки, чулки, гольфы и легинсы подписаны раздельно. Свободная лицензия на каталожные изображения не заявлена; товарные знаки принадлежат правообладателям.</p><p>Короткие истории брендов опираются на официальные хронологии, корпоративные страницы и каталоги. Ссылки раскрываются в карточке упаковки. Фирменная фотография иллюстрирует бренд; её подпись не утверждает совпадение с выбранной моделью. Подтверждённые фотографии конкретной модели вынесены в отдельный блок.</p><p>Одинаковые изображения сгруппированы: варианты перечислены внутри карточки. Оформление и наличие могут меняться. Это пополняемый архив, а не исчерпывающий реестр всех упаковок.</p><a href="packaging.html">Открыть архив →</a></section><!-- /pack-sources --></main>')
    path.write_text(t,encoding='utf-8')
print(f'Packaging archive: {len(rows)} images, {len(brands)} brands')
print(f'Exact model photographs: {len(looks["items"])} models, {len(photo_ids)} photos')
