"""Resolve an aggregator discovery only to its allowlisted publisher."""
import re
from difflib import SequenceMatcher
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit, quote
from urllib.request import Request, HTTPRedirectHandler, build_opener
from news_feed import safe_url, plain, parse_feed

class SourceError(ValueError):
    def __init__(self,code):self.code=code;super().__init__(code)

def publisher_source(item,sources):
    origin=next((s for s in sources if s['id']==item.get('sourceId')),None)
    if not origin:raise SourceError('publisher_not_allowed')
    if not origin.get('publishers'):
        if not safe_url(item.get('url',''),origin):raise SourceError('publisher_not_allowed')
        return origin
    try:
        site=item.get('sourceSite','');host=(urlsplit(site).hostname or '').removeprefix('www.')
        if host not in origin['publishers'] or not safe_url(site,{'site':site}):raise ValueError()
    except (ValueError,AttributeError):raise SourceError('publisher_not_allowed') from None
    return next((s for s in sources if (urlsplit(s['site']).hostname or '').removeprefix('www.')==host),
                {'id':host.split('.')[0],'site':'https://'+host,'name':item.get('source','')})

def title_match(left,right):
    normalize=lambda t:re.sub(r'\W+','',plain(t).casefold())
    a,b=normalize(left),normalize(right)
    return len(a)>=12 and len(b)>=12 and SequenceMatcher(None,a,b).ratio()>=.94

class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[];self.href=None;self.parts=[];self.canonical=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='a':self.href=a.get('href');self.parts=[]
        if tag=='link' and a.get('rel')=='canonical':self.canonical.append(a.get('href',''))
    def handle_data(self,text):
        if self.href:self.parts.append(text)
    def handle_endtag(self,tag):
        if tag=='a' and self.href:self.links.append((self.href,' '.join(self.parts)));self.href=None

class GooglePublisherRedirect(HTTPRedirectHandler):
    max_redirections=3
    max_repeats=1
    def __init__(self,publisher):self.publisher=publisher
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        url=urljoin(req.full_url,newurl)
        if not (safe_url(url,self.publisher) or safe_url(url,{'site':'https://news.google.com'})):
            raise SourceError('publisher_not_allowed')
        return super().redirect_request(req,fp,code,msg,headers,url)

def google_destination(item,publisher):
    url=safe_url(item.get('url',''),{'site':'https://news.google.com'})
    if not url:raise SourceError('publisher_not_allowed')
    opener=build_opener(GooglePublisherRedirect(publisher))
    with opener.open(Request(url,headers={'User-Agent':'TONKO-News/1.0'}),timeout=12) as response:
        direct=safe_url(response.url,publisher)
        if direct:return direct
        raw=response.read(1_000_001)
    if len(raw)>1_000_000:raise SourceError('source_too_large')
    parser=Links();parser.feed(raw.decode('utf-8','replace'))
    for link in parser.canonical:
        if safe_url(link,publisher):return safe_url(link,publisher)
    for link,title in parser.links:
        if title_match(title,item['title']) and safe_url(link,publisher):return safe_url(link,publisher)
    raise SourceError('publisher_unresolved')

def resolve_publisher(item,sources,fetch,now,feed_cache=None,follow_google=google_destination):
    publisher=publisher_source(item,sources)
    if item.get('publisherUrl'):
        direct=safe_url(item['publisherUrl'],publisher)
        if not direct:raise SourceError('publisher_not_allowed')
        return direct,publisher
    if not item.get('via'):return safe_url(item['url'],publisher),publisher
    # RSS is both a direct source and a reliable title-to-URL index. Cache it
    # once per batch, so ten Google entries don't download ten identical feeds.
    feeds=feed_cache if feed_cache is not None else {}
    urls=[]
    if publisher.get('url'):urls.append(publisher['url'])
    if (urlsplit(publisher['site']).hostname or '').removeprefix('www.')=='bracatus.com':
        urls.append(publisher['site'].rstrip('/')+'/?s='+quote(item['title'])+'&feed=rss2')
    for url in urls:
        try:
            if url not in feeds:
                try:feeds[url]=parse_feed(fetch(url,publisher),{**publisher,'language':'mixed','mode':'brand'},now)
                except Exception:feeds[url]=[]
            match=next((row for row in feeds[url] if title_match(row['title'],item['title'])),None)
            if match:
                item['publisherUrl']=match['url'];return match['url'],publisher
        except (ValueError,KeyError):continue
    direct=follow_google(item,publisher)
    if not safe_url(direct,publisher):raise SourceError('publisher_not_allowed')
    item['publisherUrl']=direct
    return direct,publisher
