"""Accessible static equivalent of the on-site reader, including full editorials."""
from html import escape
from math import ceil
from datetime import datetime, timedelta, timezone
import re
from urllib.parse import urlsplit
from news_publication import is_ready
H=lambda v:escape(str(v),quote=True)
PUBLICATION_WINDOW = timedelta(days=7)
MONTHS = ('января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря')

def publication_time(value):
    """Only an explicit publication date is usable; never borrow a check/import time."""
    if not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?(?:Z|[+-]\d{2}:\d{2}))?',value):
        return None
    if len(value)>10:
        # Keep the same clock bounds as the browser, even if Python normalizes 24:00.
        clock=re.match(r'(\d{2}):(\d{2})(?::(\d{2}))?',value[11:])
        if any(int(part or 0)>limit for part,limit in zip(clock.groups(),(23,59,59))):
            return None
        if value[-1]!='Z' and (int(value[-5:-3])>23 or int(value[-2:])>59):
            return None
    try:
        stamp=datetime.fromisoformat(value.replace('Z','+00:00'))
        return stamp.replace(tzinfo=timezone.utc) if stamp.tzinfo is None else stamp.astimezone(timezone.utc)
    except (ValueError,OverflowError):
        return None

def newest_publications(items):
    """Stable chronological order, with undated materials at the end."""
    return sorted(items,key=lambda item:publication_time(item.get('publishedAt')) or datetime.min.replace(tzinfo=timezone.utc),reverse=True)

def is_new_publication(value,now=None):
    stamp=publication_time(value)
    now=now or datetime.now(timezone.utc)
    return stamp is not None and timedelta(0)<=now-stamp<PUBLICATION_WINDOW

def publication_markup(value,now=None):
    stamp=publication_time(value)
    if stamp is None:
        return '<span class="publication-meta" data-publication-date=""><span class="publication-undated">Дата публикации не указана</span></span>'
    label=f'{stamp.day} {MONTHS[stamp.month-1]} {stamp.year}'
    hidden='' if is_new_publication(value,now) else ' hidden'
    return f'<span class="publication-meta" data-publication-date="{H(value)}"><span>Опубликовано <time datetime="{H(value)}" aria-label="Дата публикации: {label}">{label}</time></span><span class="publication-new" data-publication-new title="Опубликовано за последние 7 дней"{hidden}>Новое</span></span>'

def refresh_publication_badges(text,now=None):
    """Refresh already-rendered journal/readers during the normal offline page build."""
    pattern=r'(<span class="publication-meta" data-publication-date="([^"]+)">.*?<span class="publication-new" data-publication-new title="Опубликовано за последние 7 дней")(?: hidden)?(>Новое</span></span>)'
    return re.sub(pattern,lambda m:m[1]+('' if is_new_publication(m[2],now) else ' hidden')+m[3],text,flags=re.S)

def link(label,url,cls='reader-source'):
    parsed=urlsplit(url or '')
    if parsed.scheme=='https' and not parsed.username:
        return f'<a class="{cls}" href="{H(url)}" target="_blank" rel="noopener noreferrer">{H(label)} ↗</a>'
    if not parsed.scheme and not parsed.netloc and parsed.path=='packaging.html':
        return f'<a class="{cls}" href="{H(url)}">{H(label)} →</a>'
    return ''

def story(item):
    if not is_ready(item):return ''
    sections=item.get('sections',[])
    brief=item.get('summary') or item.get('excerpt') or 'В ленте источника доступен только заголовок. Развёрнутый материал для чтения на ТОНКО пока не подготовлен.'
    words=len((brief+' '+' '.join(p for s in sections for p in s['paragraphs'])).split())
    length=f'{max(2,ceil(words/160))} мин чтения' if sections else 'Короткая новость'
    if item.get('ai'):length+=' · AI-пересказ'
    if item.get('localSummary'):length+=' · Обзор на русском'
    body=''.join('<section><h3>'+H(s['heading'])+'</h3>'+''.join('<p>'+H(p)+'</p>' for p in s['paragraphs'])+'</section>' for s in sections)
    photo=item.get('illustration',{});visual=''
    if photo.get('src','').startswith(('assets/','https://')):
        dimensions=''
        if all(type(photo.get(k)) is int and photo[k]>0 for k in ('width','height')):
            dimensions=f' width="{photo["width"]}" height="{photo["height"]}"'
        visual=f'<figure class="reader-visual"><img src="{H(photo["src"])}" alt="{H(photo.get("alt",""))}"{dimensions} loading="lazy" decoding="async"><figcaption>{H(photo.get("caption",""))}{link("Источник фотографии",photo.get("source"),"reader-image-source")}</figcaption></figure>'
    credit='Разбор ТОНКО по указанным источникам. Рекомендации редакции отделены от сообщений изданий.' if sections else 'Короткий анонс из ленты источника. Полный текст издания здесь не перепечатывается.'
    if item.get('ai'):credit='Автоматический пересказ ТОНКО с помощью AI по тексту источника. Может содержать неточности; подробности и актуальные условия — в оригинале.'
    if item.get('localSummary'):credit='Самостоятельный обзор ТОНКО по материалу указанного источника. Подготовлен на русском с помощью локальной модели; возможны неточности. Дата относится к оригинальной публикации.'
    if item.get('localSummary',{}).get('sourceExcerpt'):credit+=' Обзор подготовлен по фрагменту длинного материала и не охватывает весь оригинал.'
    refs=link('Первоисточник: '+item['source'],item.get('publisherUrl') or item['url'])+''.join(link(r['label'],r['url']) for r in item.get('references',[]))
    return f'''<article class="news-fallback" id="story-{H(item['id'])}"><div class="reader-article"><header class="reader-head"><p class="portal-eyebrow">ТОНКО / {'Разбор' if sections else 'Лента'}</p><p class="news-meta"><span>{H(item['source'])}</span>{publication_markup(item.get('publishedAt'))}<span>{length}</span></p><h2>{H(item.get('displayTitle') or item['title'])}</h2><p class="reader-excerpt">{H(brief)}</p></header><div class="news-story-layout">{visual}<div class="reader-copy">{body}<footer class="reader-credits"><p class="reader-credit">{H(credit)}</p>{refs}</footer></div></div><a class="news-return" href="index.html#fashion-news">← Вернуться к ленте</a></div></article>'''
