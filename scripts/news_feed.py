"""RSS/Atom headlines only. No external HTML, scripts, or images are published."""
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
    return items

def merge_items(items, now):
    seen_urls=set(); seen_titles=set(); result=[]
    valid=[i for i in items if date(i.get('publishedAt')) and now-timedelta(days=365)<=date(i['publishedAt'])<=now]
    # Prefer the publisher's direct record with an announcement over a Google
    # headline for the same story, even when the aggregator timestamp is newer.
    for item in sorted(valid,key=lambda x:(not bool(x.get('via')),bool(x.get('excerpt')),x['publishedAt']),reverse=True):
        title=re.sub(r'\W+','',item['title'].casefold())
        if item['url'] in seen_urls or title in seen_titles: continue
        seen_urls.add(item['url']); seen_titles.add(title); result.append(item)
    return sorted(result,key=lambda x:x['publishedAt'],reverse=True)[:60]

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
