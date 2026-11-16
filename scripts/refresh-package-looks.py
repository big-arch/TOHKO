"""Audit reviewed model photos; refresh only their explicit image URL allowlist.

Default: offline integrity check. --refresh: download the reviewed URLs and
compare decoded/re-encoded WebP hashes. Changed photographs are staged for human
review and never replace published images automatically. --restore-missing may
restore a missing full image only when its hash exactly matches the manifest.
No search results, recommendations, new models or inferred product matches enter
the catalogue through this script.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'tights-guide'
sys.path.insert(0, str(ROOT / '.cache/pillow-runtime'))
from PIL import Image, ImageOps

IMAGE_HOSTS = frozenset({
    'cdn.insales-shop.ru', 'cdn.shopify.com', 'cdn.shoplightspeed.com',
    'fiore.pl', 'is8.revolveassets.com', 'kolgotkiopt.com.ua',
    'static.falke.com', 'us.wolford.com', 'www.gabriella.pl', 'www.uktights.com',
})
SOURCE_HOSTS = frozenset({
    'fiore.pl', 'kolgotki-online.ru', 'kolgotkiopt.com.ua', 'swedishstockings.com',
    'us.wolford.com', 'www.brabary.com', 'www.falke.com', 'www.gabriella.pl',
    'www.revolve.com', 'www.uktights.com',
})
Image.MAX_IMAGE_PIXELS = 25_000_000


def allowed_url(value, hosts):
    parts = urlsplit(value)
    return parts.scheme == 'https' and parts.hostname in hosts and not parts.username and parts.port in (None, 443)


class RestrictedRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not allowed_url(newurl, IMAGE_HOSTS):
            raise ValueError('Redirect outside the reviewed image hosts')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true', help='Check the reviewed remote image URLs without publishing changed images.')
    parser.add_argument('--restore-missing', action='store_true', help='Restore only missing main files with an exactly matching reviewed hash; implies --refresh.')
    parser.add_argument('--limit', type=int, default=0, help='Check only the first N photographs (0 = all).')
    args = parser.parse_args()
    data = json.loads((SITE / 'data/package-looks.json').read_text(encoding='utf-8'))
    packages = {p['id']: p for p in json.loads((SITE / 'data/packaging.json').read_text(encoding='utf-8'))}
    stage = ROOT / '.cache/package-looks-review'
    opener = urllib.request.build_opener(RestrictedRedirect())  # TLS verification remains enabled.
    report = {'models': len(data['items']), 'checked': 0, 'unchanged': 0, 'restored': 0, 'reviewRequired': [], 'errors': []}
    seen = set()
    for item in data['items']:
        for package_id in item['packageIds']:
            package = packages[package_id]
            assert package['brand'] == item['exactMatch']['brand']
            assert package['den'] == item['exactMatch']['den']
            assert package['title'] in item['packageTitles']
        for photo in item['photos']:
            if args.limit and report['checked'] >= args.limit:
                break
            report['checked'] += 1
            try:
                assert re.fullmatch(r'pl-[a-f0-9]{12}', photo['id']) and photo['id'] not in seen
                seen.add(photo['id'])
                assert allowed_url(photo['source'], SOURCE_HOSTS)
                assert allowed_url(photo['imageSource'], IMAGE_HOSTS)
                assert re.fullmatch(r'[a-f0-9]{64}', photo['sha256'])
                target = SITE / 'assets/package-looks' / (photo['id'] + '.webp')
                thumb = SITE / 'assets/package-looks' / (photo['id'] + '-480.webp')
                assert photo['src'] == target.relative_to(SITE).as_posix()
                assert photo['thumb'] == thumb.relative_to(SITE).as_posix()
                assert thumb.is_file(), 'Missing thumbnail'
                if target.is_file():
                    assert hashlib.sha256(target.read_bytes()).hexdigest() == photo['sha256'], 'Published file differs from reviewed hash'
                    with Image.open(target) as im:
                        assert im.size == (photo['width'], photo['height'])
                elif not args.restore_missing:
                    raise ValueError('Missing reviewed image; use --restore-missing')
                if not (args.refresh or args.restore_missing):
                    report['unchanged'] += 1
                    continue
                req = urllib.request.Request(photo['imageSource'], headers={'User-Agent': 'TONKO reviewed-photo audit/1.0', 'Accept': 'image/*'})
                with opener.open(req, timeout=30) as response:
                    blob = response.read(12_000_001)
                if len(blob) > 12_000_000:
                    raise ValueError('Remote file exceeds 12 MB')
                with Image.open(io.BytesIO(blob)) as original:
                    im = ImageOps.exif_transpose(original).convert('RGB')
                    im.thumbnail((1300, 1600))
                    buffer = io.BytesIO()
                    im.save(buffer, 'WEBP', quality=84, method=5)
                result = buffer.getvalue()
                if hashlib.sha256(result).hexdigest() == photo['sha256']:
                    report['unchanged'] += 1
                    if not target.exists() and args.restore_missing:
                        target.write_bytes(result)
                        report['restored'] += 1
                else:
                    stage.mkdir(parents=True, exist_ok=True)
                    candidate = stage / (photo['id'] + '.webp')
                    candidate.write_bytes(result)
                    report['reviewRequired'].append({'id': photo['id'], 'source': photo['source'], 'candidate': str(candidate.relative_to(ROOT))})
            except Exception as error:
                report['errors'].append({'id': photo['id'], 'error': str(error)})
    stage.mkdir(parents=True, exist_ok=True)
    (stage / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report['errors'] or report['reviewRequired'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
