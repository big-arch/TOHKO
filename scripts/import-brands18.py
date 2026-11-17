"""Scoped public-source research and reviewed asset import for brands18.

Never edits production data. Pages and candidates stay in qa/brands18;
the final packaging records are a separate manifest for the integrating agent.
"""
from __future__ import annotations
import argparse
import concurrent.futures
import hashlib
import html
import importlib.util
import io
import json
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, quote

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / 'qa/brands18'
SITE = ROOT / 'tights-guide'
sys.path.insert(0, str(Path.home() / 'Documents/CODEX_сайт_ТОНКО/.cache/pillow-runtime'))
from PIL import Image, ImageDraw, ImageFont, ImageOps
spec = importlib.util.spec_from_file_location('brand_source_helpers', ROOT / 'scripts/collect-brand-stories.py')
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)
helpers.QA = QA
sys.stdout.reconfigure(encoding='utf-8')


class Page(helpers.Page):
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'base' and a.get('href'):
            self.base = urljoin(self.base, a['href'])
        if tag in ('img', 'source'):
            for key in ('src', 'data-src', 'data-original', 'data-zoom-image', 'srcset', 'data-srcset'):
                if a.get(key) and not a[key].startswith('data:'):
                    values = a[key].split(',') if key.endswith('srcset') else [a[key]]
                    for value in values:
                        value = re.sub(r'\s+\d+[wx]$', '', value.strip())
                        self.images.append({'url': urljoin(self.base, value.replace(' ', '%20')), 'alt': a.get('alt', '')})
        if tag == 'a' and a.get('href'):
            self.links.append({'url': urljoin(self.base, a['href'])})


def page(entry):
    key, url = entry
    try:
        raw, final, encoding = helpers.get(url)
        # Loretta currently serves Windows-1251; preserve readable provenance.
        probe = raw[:5000].decode('ascii', errors='ignore').lower()
        if 'windows-1251' in probe or 'cp1251' in probe:
            encoding = 'cp1251'
        s = raw.decode(encoding, errors='replace')
        p = Page(final)
        p.feed(s)
        (QA / 'pages').mkdir(exist_ok=True)
        (QA / 'pages' / (key + '.html')).write_text(s, encoding='utf-8')
        return key, {'source':url, 'resolved':final, 'checked':'2026-11-17',
                     'images':list({i['url']:i for i in p.images}.values()), 'links':p.links,
                     'text':'\n'.join(p.text)[-44000:]}
    except Exception as exc:
        return key, {'source':url, 'error':str(exc)}


def write(name, data):
    (QA / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def photograph(item):
    item = dict(item)
    item['id'] = item.get('id') or hashlib.sha256((item['source'] + '|' + item['imageSource']).encode()).hexdigest()[:10]
    target = QA / 'candidates' / (item['id'] + '.webp')
    try:
        if not target.exists():
            raw, final, _ = helpers.get(item['imageSource'])
            with Image.open(io.BytesIO(raw)) as opened:
                image = ImageOps.exif_transpose(opened).convert('RGB')
                item['originalSize'] = list(image.size)
                image.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
                image.save(target, 'WEBP', quality=90, method=6)
            item['resolvedImage'] = final
            item['sourceSha256'] = hashlib.sha256(raw).hexdigest()
        with Image.open(target) as image:
            item['width'], item['height'] = image.size
        item['localCandidate'] = target.relative_to(ROOT).as_posix()
    except Exception as exc:
        item['error'] = str(exc)
    return item


def contacts(items, stem):
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 13)
    for chunk in range(0, len(items), 20):
        subset = items[chunk:chunk + 20]
        canvas = Image.new('RGB', (1200, 340 * ((len(subset) + 4) // 5)), '#eeeeee')
        draw = ImageDraw.Draw(canvas)
        for i, item in enumerate(subset):
            x, y = (i % 5) * 240, (i // 5) * 340
            path = ROOT / item['localCandidate']
            if not path.exists():
                path = SITE / 'assets/packaging18-special' / ('pkg-' + item['id'] + '.webp')
            with Image.open(path) as opened:
                thumb = ImageOps.contain(opened, (230, 285))
                canvas.paste(thumb, (x + (240 - thumb.width) // 2, y))
            label = f"{chunk+i+1}. {item['title']}"
            # Product identity plus candidate id lets a visual review be audited.
            lines = [label[k:k+32] for k in range(0, min(len(label),64),32)]
            draw.multiline_text((x+5, y+288), '\n'.join(lines + [item['id']]), font=font, fill='black', spacing=2)
        canvas.save(QA / f'{stem}-{chunk//20+1:02d}.jpg', quality=90)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pages', type=Path)
    parser.add_argument('--photos', type=Path)
    parser.add_argument('--approve', type=Path)
    parser.add_argument('--append', action='store_true', help='Keep existing reviewed records and assets unchanged when approving an expanded allowlist.')
    args = parser.parse_args()
    (QA / 'candidates').mkdir(parents=True, exist_ok=True)
    if args.pages:
        sources = json.loads(args.pages.read_text(encoding='utf-8'))
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            result = dict(pool.map(page, sources.items()))
        write(args.pages.stem + '-result.json', result)
        for key, item in result.items():
            print(key, item.get('error') or f"{len(item['images'])} images, {len(item['links'])} links")
    if args.photos:
        items = json.loads(args.photos.read_text(encoding='utf-8'))
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(photograph, items))
        write(args.photos.stem + '-result.json', results)
        contacts([r for r in results if not r.get('error')], args.photos.stem + '-contact')
        print(json.dumps({'candidates':len(results), 'downloaded':sum(not r.get('error') for r in results)}, ensure_ascii=False))
        for item in results:
            if item.get('error'): print(item['title'], item['error'])
    if args.approve:
        items = json.loads(args.approve.read_text(encoding='utf-8'))
        out = SITE / 'assets/packaging18-special'
        out.mkdir(parents=True, exist_ok=True)
        records = json.loads((QA / 'approved-records.json').read_text(encoding='utf-8')) if args.append else []
        existing = {r['id']: r for r in records}
        assert not args.append or set(existing) <= {'pkg-' + i['id'] for i in items}, 'Expanded allowlist must retain existing records.'
        seen = {hashlib.sha256((SITE / r['image']).read_bytes()).hexdigest() for r in records}
        for item in items:
            assert item['review']['approved'] is True
            assert item['review']['classification'] in ['packaging', 'branded-insert']
            assert item['productKind'] in ['колготки', 'чулки', 'гольфы', 'легинсы', 'носки']
            source = ROOT / item['localCandidate']
            identity = 'pkg-' + item['id']
            if identity in existing:
                old = existing[identity]
                assert all(old.get(k) == item.get(k) for k in ('brand', 'brandSlug', 'title', 'den', 'source', 'imageSource', 'productKind'))
                continue
            target = out / (identity + '.webp')
            thumb = out / (identity + '-320.webp')
            if source.exists():
                with Image.open(source) as opened:
                    image = opened.convert('RGB')
                    image.save(target, 'WEBP', quality=90, method=6)
                    width, height = image.size
                    image.thumbnail((320, 440), Image.Resampling.LANCZOS)
                    image.save(thumb, 'WEBP', quality=85, method=6)
            else:
                # Reviewed optimized assets are retained in a normal checkout;
                # transient downloads need not be redistributed or re-fetched.
                with Image.open(target) as image:
                    image.load()
                    width, height = image.size
                with Image.open(thumb) as image:
                    image.load()
            sha = hashlib.sha256(target.read_bytes()).hexdigest()
            assert sha not in seen, item['title']
            seen.add(sha)
            records.append(dict(id=identity, brand=item['brand'], brandSlug=item['brandSlug'], title=item['title'],
                den=item.get('den'), image=target.relative_to(SITE).as_posix(), thumbnail=thumb.relative_to(SITE).as_posix(),
                width=width, height=height, source=item['source'], imageSource=item['imageSource'],
                sourceName=item['sourceName'], checked='2026-11-17', variants=[], productKind=item['productKind'],
                caption='Фирменный вкладыш или упаковка модели ' + item['title'] + '. Тип изделия: ' + item['productKind'] + '. Оформление может отличаться у разных выпусков.',
                license='Изображение бренда из указанного каталога; свободная лицензия не заявлена. Товарные знаки принадлежат правообладателям.'))
        write('approved-records.json', records)
        contacts(items, 'approved-contact')
        print(json.dumps({'approvedRecords':len(records)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
