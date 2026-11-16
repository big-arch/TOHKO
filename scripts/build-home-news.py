"""Idempotent home enhancement; run after editorial/experience/videos builders."""
import html
import json
import re
from pathlib import Path
from datetime import datetime
from news_editorial import apply_editorial
from news_render import story

ROOT=Path(__file__).resolve().parents[1]/'tights-guide'
esc=lambda value:html.escape(str(value),quote=True)
news_path=ROOT/'data/news.json'
news=json.loads(news_path.read_text(encoding='utf-8')) if news_path.exists() else {'items':[],'sources':[]}
apply_editorial(news)
news_path.write_text(json.dumps(news,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
media={m['id']:m for m in json.loads((ROOT/'data/editorial-media.json').read_text(encoding='utf-8'))}

def card(item):
    stamp=datetime.fromisoformat(item['publishedAt'].replace('Z','+00:00')).strftime('%d.%m.%Y')
    via=' · через Google News' if item.get('via') else ''
    return f'''<article class="news-item"><div class="news-meta"><span>{esc(item['source'])}{via}</span><time datetime="{esc(item['publishedAt'])}">{stamp}</time><span>{esc(item['language'].upper())}</span></div><h3><a href="news.html#story-{esc(item['id'])}" data-news-id="{esc(item['id'])}" lang="{'ru' if item.get('displayTitle') else esc(item['language'])}">{esc(item.get('displayTitle') or item['title'])}</a></h3><span class="news-read">Читать на ТОНКО →</span></article>'''

stamp=news.get('lastSuccessfulAt')
checked='Проверка источников ещё не завершена.'
if stamp:
    checked='Последняя успешная проверка: '+datetime.fromisoformat(stamp.replace('Z','+00:00')).strftime('%d.%m.%Y %H:%M UTC')+'.'
sources=''.join(f'<li><a href="{esc(s["site"])}" target="_blank" rel="noopener noreferrer">{esc(s["name"])}</a><span>{"Доступен" if s["status"]=="ok" else "Временно недоступен"}</span></li>' for s in news.get('sources',[]))
section=f'''<!-- tonko-news --><section class="portal-container news-section" id="fashion-news" aria-labelledby="news-title">
<div class="news-heading"><div><p class="portal-eyebrow">Лента публикаций</p><h2 id="news-title">Сейчас в<br>чулочной моде.</h2></div><div class="news-heading-note"><p>Коллекции, сочетания и новые взгляды на знакомую вещь. Публикации брендов и модных изданий в одной ленте.</p><p class="news-status" id="news-status" role="status">{esc(checked)}</p></div></div>
<div class="news-toolbar"><div class="news-filters" role="group" aria-label="Язык публикаций"><button type="button" data-news-language="all" aria-pressed="true">Все</button><button type="button" data-news-language="ru" aria-pressed="false">На русском</button><button type="button" data-news-language="en" aria-pressed="false">На английском</button></div><button type="button" id="news-refresh">Проверить ленту ↻</button></div>
<button type="button" id="news-new" hidden>Показать новые публикации</button>
<div id="news-list" class="news-list">{''.join(card(i) for i in news.get('items',[])[:6]) or '<p>Публикаций пока нет. Источники проверяются автоматически.</p>'}</div>
<button type="button" id="news-more" hidden>Ещё публикации ↓</button>
<details class="news-about"><summary>Как обновляется лента и откуда новости</summary><p>Источники проверяются по расписанию каждые 15 минут. Возможны задержки сервиса и самих изданий. Новость появляется после попадания в RSS или поисковую ленту, а не в момент любой публикации в интернете.</p><p>Часть заголовков переведена на русский. Автоматические пересказы помечены «AI-пересказ»; при недостатке данных остаётся короткий анонс. Дата рядом с материалом принадлежит источнику; время проверки ленты указано отдельно. Для ссылок с отметкой Google News сначала открывается агрегатор. При сбое сохраняем предыдущие записи.</p><ul id="news-sources">{sources}</ul></details>
<noscript><p>Показан сохранённый выпуск. Для проверки обновлений перезагрузите страницу.</p></noscript></section><!-- /tonko-news -->'''

ids=['ss-clara','outfit-pattern-walk','ss-argyle','outfit-men-white']
photos=[]
for ident in ids:
    m=media[ident]
    responsive=f' srcset="{esc(m["srcset"])}" sizes="auto, (max-width: 700px) 50vw, 25vw" decoding="async"' if m.get('srcset') else ''
    photos.append(f'''<figure><a href="lookbook.html?filter=outfits#photo-{ident}" aria-label="{esc(m['title'])}: открыть в галерее"><img src="{esc(m['image'])}" alt="{esc(m['alt'])}" width="{m['width']}" height="{m['height']}" loading="lazy"{responsive}></a><figcaption>{esc(m['title'])}</figcaption></figure>''')
looks='''<!-- tonko-looks --><section class="portal-container home-looks" aria-labelledby="looks-title"><div class="looks-heading"><div><p class="portal-eyebrow">Колготки в гардеробе</p><h2 id="looks-title">Вещи складываются<br>в образ.</h2></div><p>Косуха, трикотаж, юбка или шорты. Женские и мужские сочетания из вашей подборки.</p></div><div class="looks-grid">'''+''.join(photos)+'''</div><div class="looks-bottom"><a class="experience-text-link" href="lookbook.html?filter=outfits">Все семь образов ↗</a><span>Подборка владельца ТОНКО · авторы кадров не установлены</span></div></section><!-- /tonko-looks -->'''
looks=looks.replace('из вашей подборки','из съёмок брендов и подборки ТОНКО').replace('Все семь образов',f'Все образы: {sum("outfit" in m.get("tags",[]) for m in media.values())}').replace('Подборка владельца ТОНКО · авторы кадров не установлены','Источник каждой фотографии — в галерее')
archive=json.loads((ROOT/'data/packaging.json').read_text(encoding='utf-8'))
packs=[]
for ident in ['pkg-falke','pkg-wolford','pkg-a003df0fca','pkg-c05d201da8']:
    m=next(r for r in archive if r['id']==ident)
    packs.append(f'<figure><a href="packaging.html?pack={ident}"><img src="{esc(m["thumbnail"])}" alt="Упаковка {esc(m["title"])}" loading="lazy" width="{m["width"]}" height="{m["height"]}"></a><figcaption>{esc(m["title"])}</figcaption></figure>')
packaging=f'<!-- tonko-packaging --><section class="portal-container home-looks home-packaging"><div class="looks-heading"><div><p class="portal-eyebrow">Логотипы. Модели. Детали.</p><h2>Знакомство<br>с упаковки.</h2></div><p>{len(archive)} изображений, {len(set(r["brand"] for r in archive))} брендов. Упаковки и фирменные вкладыши: поиск по модели, сравнение оформления и просмотр крупным планом.</p></div><div class="looks-grid">'+''.join(packs)+'</div><a class="experience-text-link" href="packaging.html">Открыть архив упаковок →</a></section><!-- /tonko-packaging -->'

p=ROOT/'index.html';text=p.read_text(encoding='utf-8')
for marker in ('tonko-news','tonko-looks','tonko-packaging'):
    text=re.sub(r'<!-- '+marker+r' -->.*?<!-- /'+marker+r' -->','',text,flags=re.S)
anchor='<!-- experience-home -->'
if anchor not in text: anchor='<section class="portal-section">'
if anchor not in text: raise SystemExit('Home insertion anchor missing')
text=text.replace(anchor,section+looks+packaging+anchor,1)
if 'href="news.css' not in text:text=text.replace('</head>','<link rel="stylesheet" href="news.css?v=20261116-1"></head>')
if 'href="news-reader.css' not in text:text=text.replace('</head>','<link rel="stylesheet" href="news-reader.css?v=20261116-10"></head>')
if 'src="news.js' not in text:text=text.replace('</body>','<script src="news.js?v=20261116-1" defer></script></body>')
text=re.sub(r'<script id="news-seed".*?</script>','',text,flags=re.S)
text=re.sub(r'<script src="news-reader.js[^\"]*"[^>]*></script>','',text)
seed=json.dumps(news,ensure_ascii=False).replace('<','\\u003c')
text=text.replace('<script src="news.js',f'<script id="news-seed" type="application/json">{seed}</script><script src="news-reader.js?v=20261116-10" defer></script><script src="news.js')
text=re.sub(r'(news\.(?:css|js))\?v=[^"\s]+',r'\1?v=20261116-10',text)
p.write_text(text,encoding='utf-8')
# A readable, linkable fallback also works without JavaScript.
stories=[story(i) for i in news.get('items',[])]
fallback=re.sub(r'<main\b[^>]*>.*?</main>',lambda m:'<main id="content" class="portal-container"><h1>В фокусе чулочной моды.</h1>'+''.join(stories)+'</main>',text,flags=re.S)
fallback=re.sub(r'<script[^>]*(?:news-seed|news-reader\.js|news\.js)[^>]*>.*?</script>','',fallback,flags=re.S)
fallback=re.sub(r'<title>.*?</title>','<title>Новости чулочной моды — ТОНКО</title>',fallback)
(ROOT/'news.html').write_text(fallback,encoding='utf-8')
print('Home news and outfit sections generated')
