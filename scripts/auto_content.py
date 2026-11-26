"""Bounded, allowlisted public feeds. No credentials, arbitrary HTML or AI claims."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from hashlib import sha256
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, urljoin, parse_qsl, urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler
import html
import json
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'tights-guide'
MAX_FEED = 3_000_000
MAX_IMAGE = 8_000_000
MAX_ITEMS_PER_SOURCE = 24
MAX_PHOTOS = 48
AGENT = 'TONKO-Journal/1.0 (+https://big-arch.github.io/TOHKO/sources.html)'
# The public section is about clothing. These exclusions are conservative editorial rules,
# not an automated certification of source content or image subjects.
EXCLUDE = re.compile(r'fetish|erotic|porn|crotchless|open sheath|intimacy|sexual|bondage|bdsm|фетиш|эроти|порно', re.I)
PROMOTION = re.compile(r'black (?:week|friday)|cyber monday|discount|clearance|wyprzeda|rabat|zniżk|gift card', re.I)


def iso(dt):
    return dt.astimezone(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')


def date(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        try:
            dt = parsedate_to_datetime(value)
        except (ValueError, TypeError, OverflowError):
            return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def allowed_url(url, prefixes):
    """Require exact HTTPS origin and path prefix, including on every redirect."""
    try:
        u = urlsplit(url)
        if u.scheme != 'https' or not u.hostname or u.username or u.password or u.port not in (None, 443):
            return False
        if any(c in url for c in ('\\', '\r', '\n', '\t')):
            return False
        return any(u.netloc.lower() == urlsplit(p).netloc.lower() and u.path.startswith(urlsplit(p).path)
                   for p in prefixes if p)
    except ValueError:
        return False


def canonical(url):
    u = urlsplit(html.unescape(url))
    query = [(k, v) for k, v in parse_qsl(u.query) if not k.startswith('utm_') and k not in ('fbclid', 'gclid')]
    return urlunsplit((u.scheme, u.netloc.lower(), u.path, urlencode(query), ''))


class GuardedRedirect(HTTPRedirectHandler):
    def __init__(self, prefixes):
        self.prefixes = prefixes

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not allowed_url(newurl, self.prefixes):
            raise ValueError('Redirect outside configured source')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url, prefixes, limit=MAX_FEED):
    if not allowed_url(url, prefixes):
        raise ValueError('URL outside configured source')
    opener = build_opener(GuardedRedirect(prefixes))
    req = Request(url, headers={'User-Agent': AGENT, 'Accept': '*/*'})
    with opener.open(req, timeout=25) as response:
        raw = response.read(limit + 1)
        if len(raw) > limit:
            raise ValueError('Source exceeds byte limit')
        return raw


class PlainHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.images, self.skip = [], [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'noscript'):
            self.skip += 1
        if tag == 'img' and not self.skip:
            a = dict(attrs)
            self.images.append(a.get('src', ''))

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript'):
            self.skip = max(0, self.skip - 1)

    def handle_data(self, value):
        if not self.skip:
            self.parts.append(value)

    @property
    def text(self):
        return re.sub(r'\s+', ' ', ' '.join(self.parts)).strip()


def plain(value):
    parser = PlainHTML()
    parser.feed(value or '')
    return parser


def parse_feed(raw):
    if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
        raise ValueError('XML declarations are not accepted')
    root = ET.fromstring(raw)
    atom = '{http://www.w3.org/2005/Atom}'
    entries = root.findall(atom + 'entry') if root.tag == atom + 'feed' else root.findall('./channel/item')
    result = []
    for entry in entries[:100]:
        is_atom = entry.tag == atom + 'entry'
        prefix = atom if is_atom else ''
        link = entry.findtext('link', '')
        if is_atom:
            link = next((x.get('href', '') for x in entry.findall(atom + 'link')
                         if x.get('rel', 'alternate') == 'alternate'), '')
        result.append({
            'title': entry.findtext(prefix + 'title', ''), 'url': link,
            'published': entry.findtext(prefix + ('published' if is_atom else 'pubDate'), ''),
            'body': entry.findtext(prefix + ('content' if is_atom else 'description'), '')
                    or entry.findtext(prefix + 'summary', '')
        })
    if not entries:
        raise ValueError('Expected a non-empty RSS or Atom feed')
    return result


def parse_shopify(raw, source):
    data = json.loads(raw)
    products = data.get('products')
    if not isinstance(products, list) or not products:
        raise ValueError('Expected a non-empty public product list')
    return [{'title': p.get('title', ''), 'url': source['pagePrefix'] + p.get('handle', ''),
             'published': p.get('published_at', ''), 'body': p.get('body_html', '')}
            for p in products[:100] if isinstance(p, dict)]


def make_items(raw, source, now):
    entries = parse_shopify(raw, source) if source['format'] == 'shopify' else parse_feed(raw)
    items = {}
    for entry in entries:
        title = plain(entry['title']).text[:200]
        body = plain(entry['body'])
        url = canonical(entry['url'])
        if (not title or not allowed_url(url, [source['pagePrefix']])
                or not re.search(source['include'], title)
                or EXCLUDE.search(title + ' ' + body.text) or PROMOTION.search(title)):
            continue
        published = date(entry['published'])
        if published and published > now + timedelta(minutes=5):
            continue
        if source['kind'] == 'journal' and published and published < now - timedelta(days=540):
            continue
        identifier = sha256(url.encode()).hexdigest()[:16]
        # Retain only a short quoted lead; never republish entire third-party articles.
        excerpt = ' '.join(body.text.split()[:18])
        if len(body.text.split()) > 18:
            excerpt += '…'
        item = {'id': identifier, 'url': url, 'sourceId': source['id'], 'sourceName': source['name'],
                'language': source['language'], 'kind': source['kind'], 'title': title,
                'publishedAt': iso(published) if published else None,
                'excerpt': excerpt if source['kind'] == 'journal' else '',
                'topic': 'Мужской гардероб' if source['kind'] == 'men' else 'Стиль и коллекции'}
        item['sourceDigest'] = sha256((title + '\n' + body.text + '\n' + (item['publishedAt'] or '')).encode()).hexdigest()
        if re.search(r'changemakers|production|packaging|behind the scenes', title, re.I):
            item['topic'] = 'Изнутри индустрии'
        if source.get('imagePrefix'):
            for image in body.images:
                image = urljoin(source['url'], html.unescape(image))
                if (allowed_url(image, [source['imagePrefix']])
                        and re.search(source['imagePattern'], urlsplit(image).path)):
                    item['imageUrl'] = image
                    break
        item['fingerprint'] = sha256(json.dumps(item, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        items[identifier] = item
    return sorted(items.values(), key=lambda x: (x['publishedAt'] or '', x['id']), reverse=True)[:MAX_ITEMS_PER_SOURCE]


def collect(sources, previous, now, fetcher=fetch, verify_links=True):
    stamp = iso(now)
    old_items = {x['id']: x for x in previous.get('items', [])}
    old_health = {x['id']: x for x in previous.get('sources', [])}

    def read(source):
        try:
            raw = fetcher(source['url'], [source['url']])
            return source, make_items(raw, source, now), None
        except Exception as exc:
            return source, [], type(exc).__name__ + ': ' + str(exc)[:180]

    result, health, successes = [], [], 0
    with ThreadPoolExecutor(max_workers=4) as pool:
        batches = list(pool.map(read, sources))
    for source, candidates, error in batches:
        old = [x for x in old_items.values() if x['sourceId'] == source['id']]
        info = {'id': source['id'], 'name': source['name'], 'url': source['url'], 'kind': source['kind'],
                'checkedAt': stamp, 'lastSuccessAt': old_health.get(source['id'], {}).get('lastSuccessAt'),
                'status': 'error' if error else 'ok', 'error': error, 'newCount': 0}
        if error:
            result.extend(old)
        else:
            # Feed links for new items must resolve before they can enter the public site.
            def verify(item):
                if item['id'] in old_items or not verify_links:
                    return item
                try:
                    fetcher(item['url'], [source['pagePrefix']], MAX_FEED)
                    return item
                except Exception:
                    return None
            with ThreadPoolExecutor(max_workers=4) as pool:
                verified = [x for x in pool.map(verify, candidates) if x]
            if candidates and not verified:
                info.update(status='error', error='No candidate page could be verified')
                result.extend(old)
            else:
                successes += 1
                info['lastSuccessAt'] = stamp
                # Successful feeds are authoritative. Removed or newly excluded entries
                # must not remain published merely because they appeared in an older run.
                merged = {}
                for item in verified:
                    before = old_items.get(item['id'], {})
                    item['firstSeenAt'] = before.get('firstSeenAt', stamp)
                    changed = before.get('fingerprint') != item['fingerprint']
                    item['lastChangedAt'] = stamp if changed else before.get('lastChangedAt', stamp)
                    item['checkedAt'] = stamp
                    if before.get('mediaId') and before.get('imageUrl') == item.get('imageUrl'):
                        item['mediaId'] = before['mediaId']
                    info['newCount'] += not bool(before)
                    merged[item['id']] = item
                result.extend(sorted(merged.values(), key=lambda x: (x['publishedAt'] or '', x['id']), reverse=True)[:MAX_ITEMS_PER_SOURCE])
        info['itemCount'] = sum(x['sourceId'] == source['id'] for x in result)
        health.append(info)
    if not successes:
        raise RuntimeError('All sources failed; previous edition is preserved. ' + '; '.join(x['error'] or '' for x in health))
    return {'version': 1, 'checkedAt': stamp, 'lastChangedAt': previous.get('lastChangedAt', stamp),
            'schedule': 'Ежедневно около 09:17 по Москве', 'sources': health,
            'items': sorted(result, key=lambda x: (x['publishedAt'] or '', x['id']), reverse=True)}


def add_images(data, media, sources, site=SITE, fetcher=fetch):
    """Only women's editorial feed images; no unattended men's image imports."""
    from PIL import Image, ImageOps
    Image.MAX_IMAGE_PIXELS = 30_000_000
    source_map = {x['id']: x for x in sources}
    by_id = {x['id']: x for x in media}
    auto = {x['id']: x for x in media if x.get('origin') == 'feed'}
    used_hashes = {x.get('contentHash'): x['id'] for x in auto.values()}
    downloads = 0
    for item in data['items']:
        if item['kind'] != 'journal' or not item.get('imageUrl'):
            continue
        media_id = 'auto-' + item['id']
        # A changed image URL may be temporarily unavailable. Keep this article's
        # last usable photograph until a replacement has actually downloaded.
        if media_id in auto:
            item['mediaId'] = media_id
        if media_id in by_id and by_id[media_id].get('sourceImageUrl', item['imageUrl']) == item['imageUrl']:
            by_id[media_id]['sourceImageUrl'] = item['imageUrl']
            by_id[media_id]['title'] = item['title']
            by_id[media_id]['publishedAt'] = item['publishedAt']
            item['mediaId'] = media_id
            continue
        if downloads >= 12 or (item['publishedAt'] and date(item['publishedAt']) < date(data['checkedAt']) - timedelta(days=365)):
            continue
        source = source_map[item['sourceId']]
        try:
            raw = fetcher(item['imageUrl'], [source['imagePrefix']], MAX_IMAGE)
            digest = sha256(raw).hexdigest()
            if digest in used_hashes:
                item['mediaId'] = used_hashes[digest]
                continue
            with Image.open(BytesIO(raw)) as original:
                if original.format not in ('JPEG', 'PNG', 'WEBP') or getattr(original, 'is_animated', False):
                    raise ValueError('Unsupported editorial image')
                im = ImageOps.exif_transpose(original).convert('RGB')
                if min(im.size) < 300 or max(im.size) / min(im.size) > 4:
                    raise ValueError('Image is too small or banner-shaped')
                im.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
                destination = site / 'assets/updates' / (media_id + '.webp')
                destination.parent.mkdir(parents=True, exist_ok=True)
                im.save(destination, 'WEBP', quality=88, method=6)
                m = {'id': media_id, 'image': destination.relative_to(site).as_posix(),
                     'title': item['title'], 'category': 'collection', 'author': source['name'],
                     'source': item['url'], 'license': 'Фотография из публикации бренда. Свободная лицензия не заявлена.',
                     'licenseUrl': item['url'], 'width': im.width, 'height': im.height,
                     'origin': 'feed', 'alt': 'Иллюстрация ' + source['name'] + ': ' + item['title'],
                     'caption': 'Из публикации ' + source['name'] + '. ' + item['title'],
                     'addedAt': data['checkedAt'], 'publishedAt': item['publishedAt'], 'contentHash': digest,
                     'sourceImageUrl': item['imageUrl']}
            by_id[media_id] = m
            auto[media_id] = m
            used_hashes[digest] = media_id
            item['mediaId'] = media_id
            downloads += 1
        except Exception as exc:
            # An image outage must not discard the readable article or existing photos.
            print('Image skipped:', item['id'], type(exc).__name__)
    referenced = {x.get('mediaId') for x in data['items']}
    newest = sorted((x for x in auto.values() if x['id'] in referenced),
                    key=lambda x: (x.get('publishedAt') or '', x['id']), reverse=True)[:MAX_PHOTOS]
    kept = {x['id'] for x in newest}
    # Leaving the rolling gallery must not break photographs in published articles.
    # Keep original and responsive files even when their gallery record expires.
    article_photos = set()
    for registry in ('news.json', 'free-articles.json'):
        path = site / 'data' / registry
        if path.exists():
            for article in json.loads(path.read_text(encoding='utf-8')).get('items', []):
                if not article.get('summary') or not article.get('sections'):
                    continue
                match = re.fullmatch(r'assets/updates/(auto-[0-9a-f]{16})\.webp',
                                     article.get('illustration', {}).get('src', ''))
                if match:
                    article_photos.add(match[1])
    # Remove only our own expired generated files, inside these two resolved folders.
    for folder in (site / 'assets/updates', site / 'assets/responsive'):
        base = folder.resolve()
        for path in folder.glob('auto-*.webp'):
            match = re.fullmatch(r'(auto-[0-9a-f]{16})(?:-\d+)?\.webp', path.name)
            if match and match[1] not in kept | article_photos and path.resolve().parent == base:
                path.unlink()
    for item in data['items']:
        if item.get('mediaId') not in kept:
            item.pop('mediaId', None)
    for m in newest:
        m['category'] = 'collection'
    return [x for x in media if x.get('origin') != 'feed'] + newest


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def refresh():
    sources = json.loads((ROOT / 'scripts/content-sources.json').read_text(encoding='utf-8'))
    destination = SITE / 'data/publisher-feed.json'
    previous = json.loads(destination.read_text(encoding='utf-8')) if destination.exists() else {}
    now = datetime.now(timezone.utc)
    data = collect(sources, previous, now)
    media_path = SITE / 'data/editorial-media.json'
    media = add_images(data, json.loads(media_path.read_text(encoding='utf-8')), sources)
    if any(x['lastChangedAt'] == data['checkedAt'] for x in data['items']):
        data['lastChangedAt'] = data['checkedAt']
    write_json(media_path, media)
    write_json(destination, data)
    print(json.dumps({'items': len(data['items']), 'photos': sum(x.get('origin') == 'feed' for x in media),
                      'sources': [{k: x[k] for k in ('id', 'status', 'newCount')} for x in data['sources']]}, ensure_ascii=False))


if __name__ == '__main__':
    refresh()
