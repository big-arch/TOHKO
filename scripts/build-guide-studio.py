"""Enhance the existing guide with a visual, accessible fitting studio."""
from pathlib import Path
from hashlib import sha256
from html import escape as H
import json
import re

SITE=Path(__file__).resolve().parents[1]/'tights-guide'


def section(text, identifier):
    start=re.search(r'<section\b[^>]*\bid="'+re.escape(identifier)+r'"[^>]*>',text)
    if not start:raise ValueError('Missing guide section: '+identifier)
    depth=0
    for tag in re.finditer(r'</?section\b[^>]*>',text[start.start():]):
        depth+=-1 if tag[0].startswith('</') else 1
        if depth==0:return text[start.start():start.start()+tag.end()]
    raise ValueError('Unclosed guide section')


def build():
    path=SITE/'guide.html';text=path.read_text(encoding='utf-8')
    media={p['id']:p for p in json.loads((SITE/'data/editorial-media.json').read_text(encoding='utf-8'))}
    videos={p['id']:p for p in json.loads((SITE/'data/videos.json').read_text(encoding='utf-8'))}
    def image(key,eager=False):
        p=media[key]
        return f'<img src="{H(p["image"])}" alt="{H(p["alt"])}" width="{p["width"]}" height="{p["height"]}" loading="{"eager" if eager else "lazy"}" decoding="async">'
    def credit(key):
        p=media[key];return f'<a href="{H(p["source"],quote=True)}" target="_blank" rel="noopener noreferrer">{H(p["author"])} · источник фотографии ↗</a>'
    def choices(name,legend,options):
        return f'<fieldset><legend>{legend}</legend><div class="studio-options">'+''.join(f'<label><input type="radio" name="{name}" value="{value}" {"checked" if n==0 else ""}><span>{label}</span></label>' for n,(value,label) in enumerate(options))+'</div></fieldset>'
    form=choices('occasion','01 / Куда собираетесь?',[('daily','На каждый день'),('evening','На выход'),('under','Под брюки'),('sport','На тренировку')])
    form+=choices('look','02 / Что хочется увидеть?',[('sheer','Прозрачность'),('opaque','Матовую плотность'),('pattern','Выразительный рисунок')])
    form+=choices('weather','03 / Где будете больше времени?',[('inside','В помещении'),('mild','На улице, не холодно'),('cold','На прохладной улице')])
    form+=choices('priority','04 / Что важнее при примерке?',[('waist','Комфорт пояса'),('seams','Незаметные швы'),('wear','Повседневная носка')])
    hero=f'''<section class="portal-container studio-hero"><div><p class="portal-eyebrow">ТОНКО / Мастерская выбора</p><h1>Посмотрите.<br>Попробуйте.<br><em>Выберите.</em></h1><p>У каждой пары свой характер. Найдите подходящий, сравните настоящие фотографии и посмотрите, как ткань ведёт себя в движении.</p><a class="studio-primary" href="#picker">Собрать мой выбор ↓</a><span class="studio-small">Четыре ответа · без регистрации</span></div><figure>{image('cdr-gloss',True)}<figcaption>Блеск начинается со света. {credit('cdr-gloss')}</figcaption></figure></section>'''
    nav='<nav class="chapter-nav studio-nav" aria-label="Содержание мастерской">'+''.join(f'<a href="#{key}">{label}</a>' for key,label in [('picker','Моя пара'),('photo-lab','Сравнить фото'),('motion-room','В движении'),('anatomy','Посадка'),('care','Уход'),('quiz','Миф или факт')])+'</nav>'
    picker=f'''<section class="portal-container studio-section" id="picker"><div class="studio-heading"><p class="portal-eyebrow">01 / Личный ориентир</p><h2>Пара под ваш день.</h2><p>Меняйте ответы и наблюдайте, как меняются рекомендации. Размер уточняйте по таблице выбранного бренда.</p></div><div class="studio-picker"><form id="studio-picker">{form}<a class="studio-result-jump" href="#studio-choice-preview">Показать мой ориентир ↓</a><div class="studio-form-actions"><button type="button" id="studio-save">Сохранить мой выбор</button><button type="reset">Начать заново</button></div><p id="studio-save-status" class="studio-small" role="status">Можно сохранить ответы для следующего визита в этом браузере.</p></form><aside id="studio-choice-preview" class="studio-result" aria-label="Ваш ориентир"><figure id="studio-choice-photo">{image('wolford-1')}<figcaption>{credit('wolford-1')}</figcaption></figure><div id="studio-result" aria-live="polite"><p class="portal-eyebrow">Ваш ориентир</p><h3>Прозрачная пара на каждый день</h3><p>Проверьте посадку, мысок в вашей обуви и вид ткани при обычном освещении.</p><a href="read-product-card.html">Как прочитать карточку модели →</a></div></aside></div></section>'''
    compare=f'''<section class="studio-band" id="photo-lab"><div class="portal-container studio-section"><div class="studio-heading"><p class="portal-eyebrow">02 / Фотолаборатория</p><h2>Разницу лучше увидеть.</h2><p>Передвиньте границу, чтобы рассмотреть оба примера. Это разные изделия и съёмки: свет, цвет и посадка тоже влияют на впечатление.</p></div><div class="studio-compare-options" role="group" aria-label="Выбрать фотографии"><button type="button" data-compare="surface" aria-pressed="true">Фактура и блеск</button><button type="button" data-compare="den" aria-pressed="false">10 и 20 DEN</button><button type="button" data-compare="pattern" aria-pressed="false">Кружево и горошек</button></div><div class="studio-photo-lab"><div><div class="studio-compare-stage" id="studio-compare-stage"><img id="compare-back" src="{media['cdr-gloss']['image']}" alt="{H(media['cdr-gloss']['alt'])}" width="832" height="1248"><div id="compare-front">{image('wolford-3')}</div><div id="compare-line" aria-hidden="true"><span>↔</span></div></div><label class="studio-range" for="photo-boundary">Граница сравнения <output id="photo-boundary-value">50%</output></label><input id="photo-boundary" type="range" min="0" max="100" value="50" aria-describedby="compare-note"></div><div class="studio-compare-copy"><p class="portal-eyebrow">Смотрите на детали</p><h3 id="compare-title">Как полотно ловит свет</h3><p id="compare-note">Рассмотрите блик, прозрачность и участки натяжения. Фотография помогает увидеть эффект, но не измеряет свойства ткани.</p><div id="compare-credits">{credit('wolford-3')}<br>{credit('cdr-gloss')}</div><button type="button" id="compare-reset">Вернуть границу в центр</button><a href="textures.html">Ещё крупнее: под лупой →</a></div></div></div></section>'''
    clips=''
    for key,caption in [('snag-motion','Рассмотрите, как меняются петли и прозрачность при движении.'),('snag-details','Посмотрите, как цвет колготок работает вместе с обувью и одеждой.')]:
        v=videos[key]
        if v.get('provider')!='native' or not v.get('streamUrl','').startswith('https://snagtights.com/cdn/shop/videos/'):
            raise ValueError('Unverified native clip')
        clips+=f'''<article class="studio-clip"><div class="studio-video-frame"><video playsinline muted controls preload="none" poster="{H(v['thumbnail'])}" data-stream="{H(v['streamUrl'],quote=True)}" aria-label="{H(v['title'],quote=True)}"></video><button class="studio-video-start" type="button">▶ Смотреть здесь</button></div><div><p class="portal-eyebrow">Видеопетля · {round(v['duration'])} секунд · Snag</p><h3>{H(v['title'])}</h3><p>{caption}</p><label class="studio-loop"><input type="checkbox" data-loop> Повторять как GIF</label><p class="studio-video-status" role="status">Запускается по нажатию, без звука.</p><a href="{H(v['url'],quote=True)}" target="_blank" rel="noopener noreferrer">Источник: Snag ↗</a></div></article>'''
    motion=f'''<section class="portal-container studio-section" id="motion-room"><div class="studio-heading"><p class="portal-eyebrow">03 / Живые детали</p><h2>Ткань не стоит на месте.</h2><p>Короткие ролики прямо здесь. Включите повтор — получится петля, как у GIF. Можно остановиться на любом кадре.</p></div><div class="studio-clips">{clips}</div><a class="studio-more" href="videos.html">Больше обзоров и примерок в видеотеке →</a></section>'''
    anatomy=section(text,'anatomy').replace('03 / Устройство','04 / Устройство')
    quiz=section(text,'quiz').replace('04 / Пять','06 / Пять')
    care=section(text,'care')
    den=section(text,'den-lab').replace('02 / Плотность','Условная плотность')
    theory='<div class="portal-container studio-theory"><details><summary>Почему DEN не рассказывает всё? Открыть схему ↗</summary>'+den+'</details></div>'
    sources='''<div class="portal-container studio-sources"><p>Рекомендации по уходу: <a href="https://snagtights.eu/blogs/snag-it-yourself/how-to-care-for-your-tights-to-help-them-last-longer" target="_blank" rel="noopener noreferrer">Snag</a>. Указания на ярлыке конкретной пары имеют приоритет. Фотографии — иллюстрации моделей, а не обещание одинаковой посадки. Медицинские компрессионные изделия требуют отдельного подбора.</p></div>'''
    body=hero+nav+picker+compare+motion+anatomy+care+quiz+theory+sources
    text=re.sub(r'<main\b[^>]*>.*?</main>','<main id="content">'+body+'</main>',text,flags=re.S)
    config={'photos':{k:{field:p[field] for field in ('image','alt','width','height','source','author')} for k,p in media.items() if k in ['wolford-1','wolford-3','tummy','cdr-gloss','noq-lace','ss-argyle','swedish-rib','nike-leggings','style-nylo-white-shirt','campaign-red']}}
    text=text.replace('Кружево и горошек','Кружево и ромбы')
    text=re.sub(r'<!-- guide-studio:.*?<!-- /guide-studio -->','',text,flags=re.S)
    for name,tag in [('guide-studio.css','style'),('guide-studio.js','script')]:
        version=sha256((SITE/name).read_bytes()).hexdigest()[:12]
        if tag=='style':text=text.replace('</head>',f'<!-- guide-studio:style --><link rel="stylesheet" href="{name}?v={version}"><!-- /guide-studio --></head>')
        else:
            seed=json.dumps(config,ensure_ascii=False).replace('<','\\u003c')
            text=text.replace('</body>',f'<!-- guide-studio:script --><script type="application/json" id="guide-studio-data">{seed}</script><script src="{name}?v={version}" defer></script><!-- /guide-studio --></body>')
    path.write_text(text,encoding='utf-8')
    print('Built visual guide: picker, real photo comparison, two native video loops')


if __name__=='__main__':build()
