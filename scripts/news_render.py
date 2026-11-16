"""Accessible static equivalent of the on-site reader, including full editorials."""
from html import escape
from math import ceil
from urllib.parse import urlsplit
H=lambda v:escape(str(v),quote=True)

def link(label,url,cls='reader-source'):
    parsed=urlsplit(url or '')
    if parsed.scheme=='https' and not parsed.username:
        return f'<a class="{cls}" href="{H(url)}" target="_blank" rel="noopener noreferrer">{H(label)} ↗</a>'
    if not parsed.scheme and not parsed.netloc and parsed.path=='packaging.html':
        return f'<a class="{cls}" href="{H(url)}">{H(label)} →</a>'
    return ''

def story(item):
    sections=item.get('sections',[])
    brief=item.get('summary') or item.get('excerpt') or 'В ленте источника доступен только заголовок. Развёрнутый материал для чтения на ТОНКО пока не подготовлен.'
    words=len((brief+' '+' '.join(p for s in sections for p in s['paragraphs'])).split())
    length=f'{max(2,ceil(words/160))} мин чтения' if sections else 'Короткая новость'
    body=''.join('<section><h3>'+H(s['heading'])+'</h3>'+''.join('<p>'+H(p)+'</p>' for p in s['paragraphs'])+'</section>' for s in sections)
    photo=item.get('illustration',{});visual=''
    if photo.get('src','').startswith(('assets/','https://')):
        visual=f'<figure class="reader-visual"><img src="{H(photo["src"])}" alt="{H(photo.get("alt",""))}" loading="lazy"><figcaption>{H(photo.get("caption",""))}</figcaption>{link("Об изображении",photo.get("source"),"reader-image-source")}</figure>'
    credit='Разбор ТОНКО по указанным источникам. Рекомендации редакции отделены от сообщений изданий.' if sections else 'Короткий анонс из ленты источника. Полный текст издания здесь не перепечатывается.'
    refs=link('Первоисточник: '+item['source'],item['url'])+''.join(link(r['label'],r['url']) for r in item.get('references',[]))
    return f'''<article class="news-fallback" id="story-{H(item['id'])}"><div class="reader-article"><header class="reader-head"><p class="portal-eyebrow">ТОНКО / {'Разбор' if sections else 'Лента'}</p><p class="news-meta">{H(item['source'])} · {H(item['publishedAt'][:10])} · {length}</p><h2>{H(item.get('displayTitle') or item['title'])}</h2><p class="reader-excerpt">{H(brief)}</p></header><div class="reader-layout{' has-visual' if visual else ''}">{visual}<div class="reader-copy">{body}<footer class="reader-credits"><p class="reader-credit">{H(credit)}</p>{refs}</footer></div></div><a class="news-return" href="index.html#fashion-news">← Вернуться к ленте</a></div></article>'''
