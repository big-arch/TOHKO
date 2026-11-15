"""Build after build-experience.py, before optimize-images.py. No network at build time."""
from pathlib import Path
import html,json,re

R=Path(__file__).resolve().parents[1];S=R/'tights-guide';H=html.escape
videos=json.loads((S/'data/videos.json').read_text(encoding='utf-8'))
topics={'all':'Все видео','reviews':'Обзоры','tryon':'Примерки','styling':'Образы','choice':'Как выбрать','making':'Производство','asmr':'ASMR'}
languages={'ru':'На русском','en':'На английском','none':'Без речи'}
assert len({v['id'] for v in videos})==len(videos)
for v in videos:
 assert re.fullmatch(r'[\w-]{11}',v['id'])
 assert set(v['topics'])<=set(topics) and v['language'] in languages
 assert (S/v['thumbnail']).is_file()
(S/'data/videos.js').write_text('window.TONKO_VIDEOS = '+json.dumps(videos,ensure_ascii=False,indent=2)+';\n',encoding='utf-8')

def image(v,eager=False):
 return f'<img src="{v["thumbnail"]}" alt="{H(v["originalTitle"],quote=True)}" width="480" height="360" loading="{"eager" if eager else "lazy"}" decoding="async">'

def card(v,i):
 return f'''<article class="video-card" data-video-card="{v['id']}"><div class="video-card-image">{image(v)}<button type="button" data-video-play="{v['id']}" aria-label="Смотреть на сайте: {H(v['title'])}" hidden><span aria-hidden="true">▶</span></button><span class="video-number" aria-hidden="true">{i:02}</span></div><div class="video-card-meta"><span>{H(v['kind'])}</span><span>{languages[v['language']]}</span></div><h3>{H(v['title'])}</h3><p>{H(v['description'])}</p><span class="video-author-name">{H(v['author'])}</span><div class="video-card-actions"><button class="video-watch-button" type="button" data-video-play="{v['id']}" aria-label="Смотреть на сайте: {H(v['title'])}" hidden>Смотреть на сайте <span aria-hidden="true">▶</span></button><button type="button" data-video-save="{v['id']}" aria-pressed="false" aria-label="Смотреть позже: {H(v['title'])}" hidden>Смотреть позже</button></div><details class="video-source"><summary>Источник</summary><a href="{H(v['authorUrl'])}" target="_blank" rel="noopener">Канал {H(v['author'])} ↗</a><a href="{v['url']}" target="_blank" rel="noopener">Оригинал на YouTube ↗</a></details></article>'''

first=videos[0]
body=f'''<section class="portal-container video-intro"><p class="portal-eyebrow">Видеотека ТОНКО</p><h1>Увидеть в движении.</h1><p>Как ложится ткань, с чем сочетать рисунок и как появляется новая пара. Обзоры, примерки и звуки материала — смотрите прямо здесь, на ТОНКО.</p><a href="#video-library" class="experience-text-link">Выбрать видео ↓</a></section>
<section class="portal-container video-feature" id="video-player" aria-labelledby="video-current-title" tabindex="-1"><div class="video-screen" id="video-screen">{image(first,True)}<button class="video-start" type="button" data-video-play="{first['id']}" hidden><span aria-hidden="true">▶</span><span>Смотреть на сайте</span></button></div><div class="video-feature-copy"><p class="portal-eyebrow" id="video-current-kind">{first['kind']} · {languages[first['language']]}</p><h2 id="video-current-title">{first['title']}</h2><p id="video-current-description">{first['description']}</p><p class="video-viewing-note">Просмотр на ТОНКО · Полный экран в плеере</p><p id="video-playback-status" class="video-playback-status" role="status" hidden></p><div class="video-player-actions" hidden><button id="video-retry" type="button" hidden>Повторить запуск</button><button id="video-stop" type="button" hidden>Закрыть плеер</button><button id="video-copy" type="button">Ссылка на видео</button><button id="video-next" type="button">Следующее →</button></div><input id="video-share-link" class="video-share-link" aria-label="Ссылка на выбранное видео" readonly hidden><p id="video-status" role="status"></p><details class="video-source"><summary>Об источнике</summary><a id="video-current-author" class="video-author" href="{first['authorUrl']}" target="_blank" rel="noopener">{first['author']} ↗</a><a id="video-original" href="{first['url']}" target="_blank" rel="noopener">Оригинал на YouTube ↗</a><p class="video-connection-note">После нажатия «Смотреть на сайте» загружается проигрыватель YouTube. Управление звуком, субтитрами и полноэкранным режимом находится внутри него.</p></details></div></section>
<section class="portal-container video-library" id="video-library" aria-labelledby="video-library-title"><div class="video-section-heading"><div><p class="portal-eyebrow">Найдите свой ракурс</p><h2 id="video-library-title">Что посмотрим?</h2></div><p>Сохраните интересное, чтобы вернуться позже.<br>Ваша подборка останется в этом браузере.</p></div>
<div class="video-tools" hidden><div class="video-filters" role="group" aria-label="Темы видео">'''
body+=''.join(f'<button type="button" data-video-topic="{key}" aria-pressed="{str(key=="all").lower()}">{label}</button>' for key,label in topics.items())
body+='''</div><div class="video-search-row"><label for="video-search">Поиск по названию, автору или бренду<input type="search" id="video-search" placeholder="Например, Wolford или микрофибра" autocomplete="off"></label><label for="video-language">Язык<select id="video-language"><option value="all">Любой язык</option><option value="ru">На русском</option><option value="en">На английском</option><option value="none">Без речи</option></select></label><button type="button" id="video-saved" aria-pressed="false">Смотреть позже <span id="video-saved-count">0</span></button></div></div>'''
body+=f'<p id="video-count" class="video-count" role="status">В подборке: {len(videos)} видео</p><p id="video-save-status" class="video-save-status" role="status"></p><div id="video-grid" class="video-grid">'
body+=''.join(card(v,i) for i,v in enumerate(videos,1))
body+='''</div><div class="video-empty" id="video-empty" hidden><h3>Пока ничего не найдено.</h3><p id="video-empty-text">Попробуйте другую тему или сократите запрос.</p><button type="button" id="video-reset">Показать все видео</button></div><noscript><p>Для просмотра на сайте, поиска и личной подборки включите JavaScript. Прямые ссылки на ролики доступны в пункте «Источник» под каждым видео.</p></noscript></section>
<section class="portal-container video-about"><div><h2>Продолжить просмотр.</h2><p>Это редакционная подборка, а не полный каталог YouTube. Новые обзоры и примерки появляются постоянно.</p><a href="https://www.youtube.com/results?search_query=%D0%BA%D0%BE%D0%BB%D0%B3%D0%BE%D1%82%D0%BA%D0%B8+%D0%BE%D0%B1%D0%B7%D0%BE%D1%80" target="_blank" rel="noopener">Найти ещё на YouTube ↗</a></div><div><h3>Об источниках</h3><p>Под каждым видео указан канал. Названия, каналы, ссылки и превью сверены 16 ноября 2026 года. Видеофайлы не копируются на ТОНКО; доступность и возможность встраивания могут меняться.</p><p>Обзоры отражают опыт авторов, а брендовые ролики показывают ассортимент производителя. Для выбора размера и ухода сверяйтесь с карточкой изделия.</p><a href="guide.html">Перейти к мастерской выбора →</a></div></section>'''

base=(S/'index.html').read_text(encoding='utf-8')
t=re.sub(r'<main\b[^>]*>.*?</main>',lambda _: '<main id="content">'+body+'</main>',base,flags=re.S)
t=re.sub(r'<title>.*?</title>','<title>Видео о колготках: обзоры, примерки, ASMR — ТОНКО</title>',t)
t=re.sub(r'<meta name="description" content="[^"]*">','<meta name="description" content="Видеотека ТОНКО: обзоры колготок, примерки, сочетания, производство и ASMR. Поиск, фильтры и личная подборка видео YouTube.">',t)
t=re.sub(r'<meta property="og:title" content="[^"]*">','<meta property="og:title" content="Видеотека ТОНКО">',t)
t=re.sub(r'<meta property="og:image" content="[^"]*">',f'<meta property="og:image" content="https://big-arch.github.io/TOHKO/{first["thumbnail"]}">',t)
t=t.replace('</body>','<script src="data/videos.js"></script><script src="videos.js"></script></body>')
(S/'videos.html').write_text(t,encoding='utf-8')

def strip(t,marker):return re.sub('<!-- '+marker+' -->.*?<!-- /'+marker+' -->','',t,flags=re.S)

nav=[('journal.html','Журнал'),('brands.html','Бренды'),('lookbook.html','Галерея'),('videos.html','Видео'),('men.html','Мужчинам'),('leggings.html','Легинсы'),('business.html','Индустрия'),('guide.html','Как выбрать'),('search.html','Поиск')]
for path in S.glob('*.html'):
 t=path.read_text(encoding='utf-8');current='journal.html' if path.name.startswith('read-') else path.name
 n=''.join(f'<a href="{u}"'+(' class="active" aria-current="page"' if u==current else '')+f'>{label}</a>' for u,label in nav)
 t=re.sub(r'(<nav\b[^>]*class="portal-nav"[^>]*>).*?</nav>',lambda m:m[1]+n+'</nav>',t,count=1,flags=re.S)
 if 'href="videos.css"' not in t:t=t.replace('</head>','<link rel="stylesheet" href="videos.css"></head>')
 if path.name=='search.html':
  t=t.replace('<script src="data/videos.js"></script>','').replace('<script src="tools.js"></script>','<script src="data/videos.js"></script><script src="tools.js"></script>')
  if '<option value="Видео">' not in t:t=t.replace('<option>Фото</option>','<option value="Видео">Видео</option><option>Фото</option>')
 if path.name=='index.html':
  t=strip(t,'video-home');teaser=f'''<section class="portal-container home-video" data-reveal><a href="videos.html" class="home-video-preview">{image(first)}<span>Открыть видеотеку ↗</span></a><div><p class="portal-eyebrow">Теперь в движении</p><h2>Смотреть.<br>Сравнивать. Замечать.</h2><p>Примерки, обзоры, производство и ASMR. Выберите тему и сохраните ролики на потом.</p><a class="experience-text-link" href="videos.html">Все видео →</a></div></section>'''
  t=t.replace('</main>','<!-- video-home -->'+teaser+'<!-- /video-home --></main>')
 if path.name=='wardrobe.html':
  t=strip(t,'video-shelf');t=t.replace('</main>','<!-- video-shelf --><section class="portal-container experience-related"><h2>Ваша видеоподборка</h2><p>Ролики, к которым хочется вернуться, собраны в видеотеке.</p><a href="videos.html?saved=1">Смотреть позже →</a></section><!-- /video-shelf --></main>')
 if path.name=='privacy.html':
  t=strip(t,'video-privacy');t=t.replace('</main>','<!-- video-privacy --><section class="portal-container experience-related"><h2>Видео YouTube</h2><p>Превью размещены на сервере ТОНКО. Проигрыватель youtube-nocookie.com и официальный YouTube IFrame API с youtube.com подключаются после нажатия «Смотреть на сайте»: при этом браузер обращается к серверам YouTube и передаёт технические данные, в том числе IP-адрес. Режим повышенной конфиденциальности не означает отсутствия передачи данных. Ссылки на оригинал и каналы в пункте «Источник» открывают внешний сервис.</p><p>«Смотреть позже» сохраняет идентификаторы роликов только в localStorage этого браузера. Подборка не отправляется в базу ТОНКО и не синхронизируется между устройствами; очистка данных сайта удаляет её.</p></section><!-- /video-privacy --></main>')
 if path.name=='sources.html':
  t=strip(t,'video-sources');t=t.replace('</main>','<!-- video-sources --><section class="portal-container experience-related"><h2>Видеотека и мужской гардероб: выпуск 05</h2><p>Добавлены три каталожных кадра одетых образов Adrian из публикации Activskin. Прежние три фотографии мужских моделей без полного комплекта одежды исключены из опубликованной коллекции.</p><p>Видеотека содержит 11 роликов. Названия, каналы и ссылки проверены через YouTube oEmbed; просмотрены превью. Проверка не является сплошным просмотром каждого ролика или юридической экспертизой. Автор может изменить название, превью, описание и доступность видео.</p><p>Превью принадлежат авторам видео. Видеофайлы не скачиваются: используются ссылки и проигрыватель YouTube.</p><a href="videos.html">Каналы и оригиналы видео →</a></section><!-- /video-sources --></main>')
 path.write_text(t,encoding='utf-8')
print(f'Built video library: {len(videos)} videos; navigation, search, shelf and privacy linked.')
