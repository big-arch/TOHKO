"""RSS/Atom announcements and explicit publisher cover images. Never embed HTML."""
import hashlib
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

TOPIC = re.compile(r'колгот|чулоч|чулк|легинс|леггинс|\b(tights|pantyhose|hosiery|stockings|denier|wolford|calzedonia|falke|leggings)\b', re.I)
EXCLUDE = re.compile(r'фетиш|эротик|порног|\b(fetish|porn|erotic)\b', re.I)

def requires_photo_review(title):
    return bool(re.search(r'\bwinter\b|зим|мороз|т[её]пл',title or '',re.I))

class Text(HTMLParser):
    def __init__(self): super().__init__(); self.parts=[]
    def handle_data(self, data): self.parts.append(data)

def plain(value):
    parser=Text(); parser.feed(unescape(value or ''))
    return re.sub(r'\s+', ' ', ' '.join(parser.parts)).strip()

def iso(value): return value.astimezone(timezone.utc).isoformat().replace('+00:00','Z')

def date(value):
    try:
        parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
    except (ValueError, AttributeError):
        try: parsed=parsedate_to_datetime(value)
        except (ValueError, TypeError, IndexError): return None
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)

def safe_url(value, source):
    try:
        parsed=urlsplit(value)
        allowed=urlsplit(source['site']).hostname.removeprefix('www.')
        host=(parsed.hostname or '').removeprefix('www.')
        if parsed.scheme!='https' or parsed.username or parsed.password or host!=allowed or parsed.port not in (None,443): return None
        query=[(k,v) for k,v in parse_qsl(parsed.query) if not k.lower().startswith('utm_') and k.lower() not in ('fbclid','gclid')]
        return urlunsplit(('https',parsed.netloc,parsed.path,urlencode(query),''))
    except (ValueError, AttributeError): return None

IMAGE_HOSTS={
    'whowhatwear':{'cdn.mos.cms.futurecdn.net','cdn.mos.cms.futurecdn.com'},
    'swedish':{'cdn.shopify.com'},'snag':{'cdn.shopify.com'},
    'fashionunited':{'media.fashionunited.com'},
}

def featured_image(node, source):
    # Only a cover explicitly attached to this feed entry, not an arbitrary
    # <img> from advertisements, article HTML, or a broad keyword match.
    if source.get('publishers'):return None
    for child in node.iter():
        name=child.tag.split('}')[-1]
        media=child.tag.startswith('{http://search.yahoo.com/mrss/}')
        if not ((media and name in ('content','thumbnail')) or name=='enclosure'):continue
        a=child.attrib
        if name not in ('thumbnail',) and a.get('medium')!='image' and not a.get('type','').startswith('image/'):continue
        try:
            url=urlsplit(a.get('url',''));host=(url.hostname or '').removeprefix('www.')
            allowed={urlsplit(source['site']).hostname.removeprefix('www.')}|IMAGE_HOSTS.get(source['id'],set())
            if url.scheme!='https' or url.username or url.password or url.port not in (None,443) or host not in allowed:continue
            if re.search(r'logo|favicon|placeholder|tracking|pixel|avatar|sprite|bracatus\.jpg',url.path,re.I):continue
            if not re.search(r'\.(?:jpg|jpeg|png|webp|avif)$',url.path,re.I):continue
            if any(int(a.get(size,'300'))<200 for size in ('width','height')):continue
        except (ValueError,AttributeError):continue
        return {'src':urlunsplit(url),'alt':'Иллюстрация к публикации '+source['name'],
                'caption':'Изображение, приложенное изданием к этой публикации в RSS.','source':source['site']}
    return None

def parse_feed(raw, source, now):
    if len(raw)>8_000_000: raise ValueError('Feed too large')
    if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper(): raise ValueError('DTD not supported')
    root=ET.fromstring(raw)
    tag=root.tag.split('}')[-1]
    if tag not in ('rss','feed','RDF'): raise ValueError('Not an RSS/Atom feed')
    items=[]
    for node in root.iter():
        if node.tag.split('}')[-1] not in ('item','entry'): continue
        fields={}; link=''
        for child in node:
            name=child.tag.split('}')[-1]
            fields.setdefault(name,''.join(child.itertext()))
            if name=='link' and child.attrib.get('rel','alternate')=='alternate':
                link=child.attrib.get('href') or child.text or ''
        title=plain(fields.get('title',''))[:240]
        published=date(fields.get('pubDate') or fields.get('published') or fields.get('date') or fields.get('updated'))
        url=safe_url(link.strip(),source)
        if not title or not url or not published or published>now or published<now-timedelta(days=365): continue
        publisher=source['name']; publisher_site=source['site']
        if source.get('publishers'):
            origin=next((c for c in node if c.tag.split('}')[-1]=='source'),None)
            if origin is None: continue
            publisher_site=origin.attrib.get('url','')
            host=(urlsplit(publisher_site).hostname or '').removeprefix('www.')
            if host not in source['publishers'] or not publisher_site.startswith('https://'): continue
            publisher=plain(origin.text)[:80]
            if title.endswith(' - '+publisher): title=title[:-(len(publisher)+3)]
        description=plain(fields.get('description') or fields.get('summary') or fields.get('content',''))
        context=title+' '+description[:700]
        if EXCLUDE.search(context): continue
        if source.get('mode')!='brand' and not TOPIC.search(context): continue
        # Only a short feed announcement, never the full publisher article.
        excerpt='' if source.get('publishers') or description.casefold()==title.casefold() else description[:280]
        if len(description)>280 and excerpt: excerpt=excerpt.rsplit(' ',1)[0]+'…'
        items.append({'id':hashlib.sha256(url.encode()).hexdigest()[:16], 'title':title, 'url':url,'excerpt':excerpt,
                      'publishedAt':iso(published),'sourceId':source['id'],'source':publisher,
                      'sourceSite':publisher_site,'via':'Google News' if source.get('publishers') else None,
                      'language':'ru' if re.search('[А-Яа-яЁё]',title) else source['language'] if source['language']!='mixed' else 'en'})
        image=None if requires_photo_review(title) else featured_image(node,source)
        if image:
            image['source']=url
            items[-1]['illustration']=image
    return items

def merge_items(items, now):
    seen_urls=set(); seen_titles=set(); result=[]
    valid=[i for i in items if date(i.get('publishedAt')) and date(i['publishedAt'])<=now
           and (i.get('sections') or date(i['publishedAt'])>=now-timedelta(days=365))]
    # Preserve a complete existing article and its deep link first. Otherwise,
    # prefer the publisher's direct record over an aggregator duplicate.
    for item in sorted(valid,key=lambda x:(bool(x.get('sections')),not bool(x.get('via')),bool(x.get('excerpt')),x['publishedAt']),reverse=True):
        title=re.sub(r'\W+','',item['title'].casefold())
        canonical=item.get('publisherUrl') or item['url']
        if canonical in seen_urls or item['url'] in seen_urls or title in seen_titles: continue
        seen_urls.update((item['url'],canonical)); seen_titles.add(title); result.append(item)
    ordered=sorted(result,key=lambda x:x['publishedAt'],reverse=True)
    # A burst of unresolved headlines cannot evict a complete article. The
    # readable archive and the discovery queue have independent budgets.
    ready=[i for i in ordered if i.get('sections')][:200]
    pending=[i for i in ordered if not i.get('sections')][:200]
    return sorted(ready+pending,key=lambda x:x['publishedAt'],reverse=True)

def collect(sources, previous, fetch, now):
    previous_status={s['id']:s for s in previous.get('sources',[])}
    items=[]; statuses=[]; success=False
    for source in sources:
        prior=previous_status.get(source['id'],{})
        # Previous entries are revalidated; disabling a source removes its entries.
        for old in previous.get('items',[]):
            if old.get('sourceId')==source['id'] and safe_url(old.get('url'),source) and old.get('title'):
                items.append({**old,'title':plain(old['title'])[:240]})
        status={k:source[k] for k in ('id','name','site','language')}
        status['lastSuccessfulAt']=prior.get('lastSuccessfulAt')
        try:
            entries=parse_feed(fetch(source),source,now)
            retained={i['url']:i for i in items}
            for entry in entries:
                old=retained.get(entry['url'],{})
                for field in ('publisherUrl','publication','displayTitle','summary','sections','ai','illustration','references','checked'):
                    if field in old:entry[field]=old[field]
            # New feed values replace previous versions of the same story.
            urls={i['url'] for i in entries}
            items=[i for i in items if i['url'] not in urls]+entries
            status.update(status='ok',lastSuccessfulAt=iso(now),matched=len(entries))
            success=True
        except Exception as error:
            status.update(status='error',error=type(error).__name__)
        statuses.append(status)
    return {'version':1,'checkedAt':iso(now),'lastSuccessfulAt':iso(now) if success else previous.get('lastSuccessfulAt'),
            'intervalMinutes':15,'sources':statuses,'items':merge_items(items,now)}
