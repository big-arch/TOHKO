"""Build after build-experience.py, before optimize-images.py. No network at build time."""
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
from urllib.parse import unquote, urlsplit
import argparse,hashlib,html,json,re

PUBLICATION_PATTERN = re.compile(r'\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2}))?')


def publication_time(value):
 """Use only explicit source dates; date-only values sort at midnight UTC."""
 if not isinstance(value, str) or not PUBLICATION_PATTERN.fullmatch(value):return None
 if len(value)>10 and value[-1]!='Z' and (int(value[-5:-3])>23 or int(value[-2:])>59):return None
 try:
  parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
  parsed=parsed.replace(microsecond=parsed.microsecond//1000*1000)
  return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed
 except ValueError:return None


def sorted_videos(videos, order='newest'):
 """Stable order by publication instant, with unknown dates last in both directions."""
 def key(video):
  instant=publication_time(video.get('publishedAt'))
  return (instant is None, (1 if order=='oldest' else -1)*instant.timestamp() if instant else 0)
 return sorted(videos,key=key)


def channel_identity(value):
 """URLs identify channels; names never do. YouTube handles are case insensitive."""
 parsed=urlsplit(value)
 host=(parsed.hostname or '').lower().removeprefix('www.')
 if host=='m.youtube.com':host='youtube.com'
 path=unquote(parsed.path).rstrip('/')
 if host=='youtube.com' and path.startswith('/@'):path=path.casefold()
 return host+path


def build_channels(videos, sources):
 """Union of configured channels and manual authors, including empty sources."""
 channels={}
 aliases={}
 publishers={}
 for source in sources:
  addresses=source.get('authorUrls',[])
  address=source.get('verificationUrl') if source.get('publisherHost') else None
  address=address or (addresses[0] if addresses else source['url'])
  channels[source['id']]={'id':source['id'],'name':source['name'],'url':address,'videoIds':[]}
  for alias in addresses:aliases[channel_identity(alias)]=source['id']
  if source.get('publisherHost'):publishers[source['publisherHost'].lower().removeprefix('www.')]=source['id']
 for video in videos:
  identity=channel_identity(video['authorUrl'])
  host=(urlsplit(video['authorUrl']).hostname or '').lower().removeprefix('www.')
  channel_id=aliases.get(identity) or publishers.get(host)
  if not channel_id and video.get('sourceId') in channels:channel_id=video['sourceId']
  if not channel_id:
   channel_id='author-'+hashlib.sha256(identity.encode('utf-8')).hexdigest()[:16]
   channels.setdefault(channel_id,{'id':channel_id,'name':video['author'],'url':video['authorUrl'],'videoIds':[]})
  channels[channel_id]['videoIds'].append(video['id'])
 names=Counter(channel['name'].casefold() for channel in channels.values())
 for channel in channels.values():
  channel['count']=len(channel['videoIds'])
  channel['label']=channel['name']
  if names[channel['name'].casefold()]>1:channel['label']+=' · '+channel_identity(channel['url'])
 return sorted(channels.values(),key=lambda channel:(channel['name'].casefold(),channel['id']))

def main(argv=None):
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--videos-only',action='store_true',help='Build videos.html and videos.js without touching other pages')
 args=parser.parse_args(argv)
 R=Path(__file__).resolve().parents[1];S=R/'tights-guide';H=html.escape
 videos=json.loads((S/'data/videos.json').read_text(encoding='utf-8'))
 sources=json.loads((S/'data/video-sources.json').read_text(encoding='utf-8'))['sources']
 channels=build_channels(videos,sources)
 channel_by_video={video_id:channel['id'] for channel in channels for video_id in channel['videoIds']}
 topics={'all':'Все видео','reviews':'Обзоры','tryon':'Примерки','styling':'Образы','choice':'Как выбрать','making':'Производство','asmr':'ASMR · звуки ткани'}
 languages={'ru':'На русском','en':'На английском','none':'Без речи','original':'Язык оригинала'}
 def provider(v):return 'Snag · HTML5' if v.get('provider')=='native' else 'Vimeo' if v.get('provider')=='vimeo' else 'YouTube'
 assert len({v['id'] for v in videos})==len(videos)
 for v in videos:
  assert re.fullmatch(r'snag-[a-z]+',v['id']) if v.get('provider')=='native' else re.fullmatch(r'vimeo-\d{6,12}',v['id']) if v.get('provider')=='vimeo' else re.fullmatch(r'[\w-]{11}',v['id'])
  if v.get('provider')=='native':assert v['streamUrl'].startswith('https://snagtights.com/cdn/shop/videos/') and '.mp4' in v['streamUrl']
  if v.get('provider')=='vimeo':assert v['id']=='vimeo-'+v['providerId']
  assert set(v['topics'])<=set(topics) and v['language'] in languages
  assert (S/v['thumbnail']).is_file()
 (S/'data/videos.js').write_text('window.TONKO_VIDEOS = '+json.dumps(videos,ensure_ascii=False,indent=2)+';\n',encoding='utf-8')

 def image(v,eager=False):
  return f'<img src="{v["thumbnail"]}" alt="{H(v["originalTitle"],quote=True)}" width="{v.get('thumbnailWidth',480)}" height="{v.get('thumbnailHeight',360)}" loading="{"eager" if eager else "lazy"}" decoding="async">'

 def published(v):
  value=v.get('publishedAt','')
  parsed=publication_time(value)
  if parsed:
   label='Архив · опубликовано' if v.get('archive') else 'Опубликовано'
   date_markup=f'<time class="video-published" datetime="{H(value)}">{label} {parsed.strftime("%d.%m.%Y")}</time>'
  else:
   label='Архив · дата публикации не подтверждена' if v.get('archive') else 'Дата публикации не подтверждена'
   date_markup=f'<span class="video-published">{label}</span>'
  # Recency is evaluated on opening the page, so a cached HTML badge cannot become stale.
  return date_markup+f'<span class="video-new" data-video-new="{v["id"]}" title="Опубликовано за последние 7 дней" hidden>Новое</span>'

 def card(v,i):
  return f'''<article class="video-card" data-video-card="{v['id']}" data-video-channel="{channel_by_video[v['id']]}"><div class="video-card-image">{image(v)}<button type="button" data-video-play="{v['id']}" aria-label="Смотреть на сайте: {H(v['title'])}" hidden><span aria-hidden="true">▶</span></button><span class="video-number" aria-hidden="true">{i:02}</span></div><div class="video-card-meta"><span>{H(v['kind'])}</span><span>{languages[v['language']]}</span><span class="video-provider">{provider(v)}</span></div><h3>{H(v['title'])}</h3><p>{H(v['description'])}</p><span class="video-author-name">{H(v['author'])}</span><div class="video-publication">{published(v)}</div><div class="video-card-actions"><button class="video-watch-button" type="button" data-video-play="{v['id']}" aria-label="Смотреть на сайте: {H(v['title'])}" hidden>Смотреть на сайте <span aria-hidden="true">▶</span></button><button type="button" data-video-save="{v['id']}" aria-pressed="false" aria-label="Смотреть позже: {H(v['title'])}" hidden>Смотреть позже</button></div><details class="video-source"><summary>Источник</summary><a href="{H(v['authorUrl'])}" target="_blank" rel="noopener">Канал {H(v['author'])} ↗</a><a href="{v['url']}" target="_blank" rel="noopener">Оригинал на {provider(v)} ↗</a></details></article>'''

 # The featured no-account player is independent of the chronological catalogue.
 first=next((v for v in videos if v['id']=='snag-motion'),next((v for v in videos if v.get('provider')=='native'),videos[0]))
 body=f'''<section class="portal-container video-intro"><p class="portal-eyebrow">Видеотека ТОНКО</p><h1>Увидеть в движении.</h1><p>Как ложится ткань, с чем сочетать рисунок и как появляется новая пара. Фильмы о производстве, обзоры, примерки и ASMR: шорох ткани и звуки упаковки. Смотрите внутри ТОНКО: место просмотра и ваша подборка сохраняются в этом браузере.</p><a href="#video-library" class="experience-text-link">Выбрать видео ↓</a></section>
 <section class="portal-container video-feature" id="video-player" aria-labelledby="video-current-title" tabindex="-1"><div class="video-screen is-portrait" id="video-screen">{image(first,True)}<button class="video-start" type="button" data-video-play="{first['id']}" hidden><span aria-hidden="true">▶</span><span>Смотреть на сайте</span></button></div><div class="video-feature-copy"><p class="portal-eyebrow" id="video-current-kind">{first['kind']} · {languages[first['language']]}</p><h2 id="video-current-title">{first['title']}</h2><p id="video-current-description">{first['description']}</p><div class="video-publication" id="video-current-publication">{published(first)}</div><p class="video-viewing-note" id="video-viewing-note">Плеер ТОНКО · Без аккаунта</p><p id="video-playback-status" class="video-playback-status" role="status" hidden></p><div class="video-player-actions" hidden><button id="video-alternative" type="button" hidden>Другие видео без YouTube</button><button id="video-retry" type="button" hidden>Повторить запуск</button><button id="video-stop" type="button" hidden>Закрыть плеер</button><button id="video-copy" type="button">Ссылка на видео</button><button id="video-next" type="button">Следующее →</button></div><input id="video-share-link" class="video-share-link" aria-label="Ссылка на выбранное видео" readonly hidden><p id="video-status" role="status"></p><details class="video-source"><summary>Об источнике</summary><a id="video-current-author" class="video-author" href="{first['authorUrl']}" target="_blank" rel="noopener">{first['author']} ↗</a><a id="video-original" href="{first['url']}" target="_blank" rel="noopener">Оригинал на {provider(first)} ↗</a><p class="video-connection-note" id="video-connection-note">Видео поступает с официального сайта Snag после нажатия. Звук, скорость и полноэкранный режим доступны в плеере.</p></details></div></section>
 <section class="portal-container video-library" id="video-library" aria-labelledby="video-library-title"><div class="video-section-heading"><div><p class="portal-eyebrow">Найдите свой ракурс</p><h2 id="video-library-title">Что посмотрим?</h2></div><p>Сохраните интересное, чтобы вернуться позже.<br>Ваша подборка останется в этом браузере.</p></div>
 <div class="video-tools" hidden><div class="video-filters" role="group" aria-label="Темы видео">'''
 body+=''.join(f'<button type="button" data-video-topic="{key}" aria-pressed="{str(key=="all").lower()}">{label}</button>' for key,label in topics.items())
 body+='''</div><div class="video-search-row"><label for="video-search">Поиск по названию, автору или бренду<input type="search" id="video-search" placeholder="Например, Wolford или микрофибра" autocomplete="off"></label><label for="video-language">Язык<select id="video-language"><option value="all">Любой язык</option><option value="ru">На русском</option><option value="en">На английском</option><option value="none">Без речи</option><option value="original">Язык оригинала</option></select></label><label for="video-provider">Плеер<select id="video-provider"><option value="all">Любой плеер</option><option value="native">Без аккаунта · плеер ТОНКО</option><option value="vimeo">Без YouTube · Vimeo</option><option value="youtube">YouTube</option></select></label><button type="button" id="video-saved" aria-pressed="false">Смотреть позже <span id="video-saved-count">0</span></button></div></div>'''
 channel_options=''.join(f'<option value="{H(c["id"])}" data-channel-name="{H(c["name"])}" data-channel-url="{H(c["url"])}" data-channel-count="{c["count"]}">{H(c["label"])} · {c["count"]}</option>' for c in channels)
 channel_menu=f'''<div class="video-channel-row"><div><label for="video-channel">Канал или автор</label><select id="video-channel" aria-describedby="video-channel-description"><option value="all">Все каналы · {len(channels)}</option>{channel_options}</select></div><div><label for="video-sort">Порядок</label><select id="video-sort"><option value="newest">Сначала новые</option><option value="oldest">Сначала старые</option></select></div></div><p class="video-channel-context"><span id="video-channel-description">Все каналы и авторы подборки, в том числе пока без видео. Число рядом с названием — ролики в каталоге.</span> <a id="video-channel-source" target="_blank" rel="noopener" hidden>Открыть канал ↗</a></p>'''
 body=body.replace('<div class="video-tools" hidden>','<div class="video-tools" hidden>'+channel_menu)
 body+='<p class="video-publication-note">Даты исходных публикаций. «Новое» — за последние 7 дней.</p>'
 body+=f'<p id="video-count" class="video-count" role="status">В подборке: {len(videos)} видео</p><p id="video-save-status" class="video-save-status" role="status"></p><div id="video-grid" class="video-grid">'
 body+=''.join(card(v,i) for i,v in enumerate(sorted_videos(videos),1))
 body+='''</div><div class="video-empty" id="video-empty" hidden><h3>Пока ничего не найдено.</h3><p id="video-empty-text">Попробуйте другую тему или сократите запрос.</p><button type="button" id="video-reset">Показать все видео</button></div><noscript><p>Для просмотра на сайте, поиска и личной подборки включите JavaScript. Прямые ссылки на ролики доступны в пункте «Источник» под каждым видео.</p></noscript></section>
 <section class="portal-container video-about"><div><h2>Продолжить просмотр.</h2><p>Нажмите «Смотреть на сайте» у выбранного ролика. Место просмотра сохраняется в этом браузере: вернувшись, вы сможете продолжить с того же момента. В подборке есть видео YouTube, Vimeo и с официального сайта Snag.</p><a href="videos.html?provider=native">Видео без аккаунта →</a><a href="https://www.youtube.com/results?search_query=%D0%BA%D0%BE%D0%BB%D0%B3%D0%BE%D1%82%D0%BA%D0%B8+%D0%BE%D0%B1%D0%B7%D0%BE%D1%80" target="_blank" rel="noopener">Найти ещё на YouTube ↗</a></div><div><h3>Об источниках</h3><p>Новые публикации добавляются автоматически из выбранных публичных каналов и официальных журналов брендов. Каталог отбирает видео о колготках, проверяет сведения автора и наличие официальной вставки. Архивные выпуски помечены отдельно. День публикации берётся из источника; если он не подтверждён, это указано на карточке. Доступность просмотра зависит от автора, платформы и сети посетителя.</p><p>Обзоры отражают опыт авторов, а брендовые ролики показывают ассортимент производителя. Для выбора размера и ухода сверяйтесь с карточкой изделия.</p><a href="guide.html">Перейти к мастерской выбора →</a></div></section>'''

 base=(S/'index.html').read_text(encoding='utf-8')
 base=re.sub(r'<script[^>]*(?:news-seed|news-reader\.js|news\.js)[^>]*>.*?</script>','',base,flags=re.S)
 t=re.sub(r'<main\b[^>]*>.*?</main>',lambda _: '<main id="content">'+body+'</main>',base,flags=re.S)
 t=re.sub(r'<title>.*?</title>','<title>Видео о колготках: обзоры, примерки, ASMR — ТОНКО</title>',t)
 t=re.sub(r'<meta name="description" content="[^"]*">','<meta name="description" content="Видеотека ТОНКО: обзоры колготок, примерки, сочетания, производство и ASMR. Поиск, фильтры и личная подборка видео Vimeo и YouTube.">',t)
 t=re.sub(r'<meta property="og:title" content="[^"]*">','<meta property="og:title" content="Видеотека ТОНКО">',t)
 t=re.sub(r'<meta property="og:image" content="[^"]*">',f'<meta property="og:image" content="https://big-arch.github.io/TOHKO/{first["thumbnail"]}">',t)
 t=t.replace('</body>','<script src="data/videos.js"></script><script src="video-memory.js?v=20261116-8"></script><script src="videos.js"></script></body>')
 (S/'videos.html').write_text(t,encoding='utf-8')

 def strip(t,marker):return re.sub('<!-- '+marker+' -->.*?<!-- /'+marker+' -->','',t,flags=re.S)

 nav=[('journal.html','Журнал'),('brands.html','Бренды'),('lookbook.html','Галерея'),('packaging.html','Упаковки'),('videos.html','Видео'),('men.html','Мужчинам'),('leggings.html','Легинсы'),('business.html','Индустрия'),('guide.html','Как выбрать'),('search.html','Поиск')]
 version=hashlib.sha256((S/'data/videos.js').read_bytes()+(S/'videos.js').read_bytes()+(S/'videos.css').read_bytes()).hexdigest()[:12]
 for path in ([S/'videos.html'] if args.videos_only else S.glob('*.html')):
  t=path.read_text(encoding='utf-8');current='journal.html' if path.name.startswith('read-') else path.name
  t=re.sub(r'(videos\.(?:js|css)|data/videos\.js)\?v=[^"\s]+',r'\1',t)
  n=''.join(f'<a href="{u}"'+(' class="active" aria-current="page"' if u==current else '')+f'>{label}</a>' for u,label in nav)
  t=re.sub(r'(<nav\b[^>]*class="portal-nav"[^>]*>).*?</nav>',lambda m:m[1]+n+'</nav>',t,count=1,flags=re.S)
  if 'href="videos.css"' not in t:t=t.replace('</head>','<link rel="stylesheet" href="videos.css"></head>')
  if path.name=='search.html':
   t=t.replace('<script src="data/videos.js"></script>','').replace('<script src="tools.js"></script>','<script src="data/videos.js"></script><script src="tools.js"></script>')
   if '<option value="Видео">' not in t:t=t.replace('<option>Фото</option>','<option value="Видео">Видео</option><option>Фото</option>')
  if path.name=='index.html':
   t=strip(t,'video-home');teaser=f'''<section class="portal-container home-video" data-reveal><a href="videos.html" class="home-video-preview">{image(first)}<span>Открыть видеотеку ↗</span></a><div><p class="portal-eyebrow">Теперь в движении</p><h2>Смотреть.<br>Сравнивать. Замечать.</h2><p>Видео Snag, фильмы Vimeo, обзоры и примерки YouTube. Новые публикации появляются автоматически. Выберите тему и сохраните ролики на потом.</p><a class="experience-text-link" href="videos.html">Все видео →</a></div></section>'''
   t=t.replace('</main>','<!-- video-home -->'+teaser+'<!-- /video-home --></main>')
  if path.name=='wardrobe.html':
   t=strip(t,'video-shelf');t=t.replace('</main>','<!-- video-shelf --><section class="portal-container experience-related"><h2>Ваша видеоподборка</h2><p>Ролики, к которым хочется вернуться, собраны в видеотеке.</p><a href="videos.html?saved=1">Смотреть позже →</a></section><!-- /video-shelf --></main>')
  if path.name=='privacy.html':
   t=strip(t,'video-privacy');t=t.replace('</main>','<!-- video-privacy --><section class="portal-container experience-related"><h2>Видеоплееры</h2><p>Превью размещены на сервере ТОНКО. Видео Snag воспроизводятся встроенным HTML5-плеером; медиапоток поступает с snagtights.com после нажатия. Браузер передаёт CDN бренда технические данные для доставки видео, включая IP-адрес. Vimeo и его API (player.vimeo.com) подключаются только при запуске ролика Vimeo; используется параметр dnt=1, но технические данные для доставки видео всё равно передаются платформе. Официальный проигрыватель YouTube и YouTube IFrame API с youtube.com подключаются после нажатия «Смотреть на сайте»: при этом браузер обращается к серверам YouTube и передаёт технические данные, в том числе IP-адрес. Ссылки на оригинал и каналы в пункте «Источник» открывают внешний сервис.</p><p>«Смотреть позже» и позиция просмотра сохраняются только в localStorage этого браузера. Браузер и видеосервис управляют cookies и доступом к существующему сеансу аккаунта. Подборка не отправляется в базу ТОНКО и не синхронизируется между устройствами; очистка данных сайта удаляет её.</p></section><!-- /video-privacy --></main>')
  if path.name=='sources.html':
   t=strip(t,'video-sources');t=t.replace('</main>','<!-- video-sources --><section class="portal-container experience-related"><h2>Видеотека и фотографии</h2><p>Галерея объединяет фотографии брендов, уличные образы и парные съёмки. Источник, известная модель и подтверждённая плотность указаны отдельно для каждого кадра.</p><p>Видеотека объединяет YouTube, Vimeo и видео Snag в плеере HTML5. Она автоматически пополняется из разрешённых каналов и официального журнала Swedish Stockings. Публикации проверяются по теме, исходной дате, автору и официальной вставке; повторные записи исключаются. Если источник недоступен, последняя подборка сохраняется. Фильмы Journey of a Thread взяты из официального журнала Swedish Stockings; для просмотра используются официальные встроенные проигрыватели. Новые названия, авторы и вставки проверяются через oEmbed соответствующей платформы. Превью и описания поступают от источников; автоматическая проверка не гарантирует воспроизведение в любой сети. Проверка не является сплошным просмотром каждого ролика или юридической экспертизой. Автор может изменить название, превью, описание и доступность видео.</p><p>Превью принадлежат авторам видео. Видеофайлы не скачиваются: используются официальные встроенные плееры Vimeo и YouTube, а видео Snag поступает с официального CDN в HTML5-плеер.</p><a href="videos.html">Каналы и оригиналы видео →</a></section><!-- /video-sources --></main>')
  for asset in ('videos.css','videos.js','data/videos.js'):
   t=t.replace('="'+asset+'"','="'+asset+'?v='+version+'"')
  path.write_text(t,encoding='utf-8')
 print(f'Built video library: {len(videos)} videos; '+('video page only.' if args.videos_only else 'navigation, search, shelf and privacy linked.'))


if __name__=='__main__':
 main()
