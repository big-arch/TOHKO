"""Import the explicitly reviewed packaging16 images (offline; no discovery).

The approved manifests in qa/packaging16 are the human-reviewed allowlist.
Source downloads and contact sheets remain in QA; only optimized WebP images
and thumbnails are published. Run with Python + Pillow available.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'tights-guide'
QA = ROOT / 'qa/packaging16'
# Reuse the project's existing runtime, without modifying its installation.
for runtime in (
    os.environ.get('TONKO_PILLOW_RUNTIME', ''),
    str(ROOT / '.cache/pillow-runtime'),
    str(Path.home() / 'Documents/CODEX_сайт_ТОНКО/.cache/pillow-runtime'),
):
    if runtime and Path(runtime).is_dir():
        sys.path.insert(0, runtime)
from PIL import Image, ImageOps

Image.MAX_IMAGE_PIXELS = 25_000_000


def main():
    reviewed = []
    for path in sorted(QA.glob('approved-*.json')):
        reviewed.extend(json.loads(path.read_text(encoding='utf-8')))
    if not reviewed:
        raise ValueError('No explicitly approved photographs')
    reviewed.sort(key=lambda r: (r['brand'].casefold(), r['title'].casefold()))
    target = SITE / 'data/packaging.json'
    original = json.loads(target.read_text(encoding='utf-8'))
    old = {item['id']: item for item in original}
    output = []
    ids, titles, hashes = set(), set(), set()
    for item in reviewed:
        short_id = item['id']
        assert re.fullmatch(r'[a-f0-9]{10}', short_id), short_id
        package_id = 'pkg-' + short_id
        assert package_id not in ids, package_id
        ids.add(package_id)
        title_key = (item['brand'], item['title'])
        assert title_key not in titles, title_key
        titles.add(title_key)
        assert item['productKind'] in ('колготки', 'чулки', 'гольфы', 'носки')
        assert item['den'] is None or (isinstance(item['den'], int) and 0 < item['den'] <= 500)
        for field in ('source', 'imageSource'):
            parts = urlsplit(item[field])
            assert parts.scheme == 'https' and parts.hostname and not parts.username
        image_path = SITE / 'assets/packaging' / (package_id + '.webp')
        thumb_path = image_path.with_name(package_id + '-320.webp')
        downloaded = QA / (short_id + '.img')
        if downloaded.exists():
            with Image.open(downloaded) as opened:
                image = ImageOps.exif_transpose(opened).convert('RGB')
                image.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
                image.save(image_path, 'WEBP', quality=88, method=6)
                size = image.size
                image.thumbnail((320, 440), Image.Resampling.LANCZOS)
                image.save(thumb_path, 'WEBP', quality=84, method=6)
        else:
            # A checkout contains the already reviewed optimized assets, not the
            # temporary research downloads. Do not recompress them on a rerun.
            with Image.open(image_path) as image:
                image.load()
                size = image.size
            with Image.open(thumb_path) as thumbnail:
                thumbnail.load()
        digest = hashlib.sha256(image_path.read_bytes()).hexdigest()
        assert digest not in hashes, 'Repeated reviewed image: ' + item['title']
        hashes.add(digest)
        record = dict(
            id=package_id,
            brand=item['brand'],
            brandSlug=re.sub(r'[^a-z0-9]+', '-', item['brand'].lower()).strip('-'),
            title=item['title'],
            den=item['den'],
            image=image_path.relative_to(SITE).as_posix(),
            thumbnail=thumb_path.relative_to(SITE).as_posix(),
            width=size[0], height=size[1],
            source=item['source'], imageSource=item['imageSource'],
            sourceName=item['sourceName'], checked='2026-11-17',
            variants=item.get('variants', []),
            caption=('Фирменный вкладыш или фотография упаковки модели ' + item['title']
                     + '. Тип изделия: ' + item['productKind'] + '.'
                     + ' Название и оформление сверены с изображением и указанным источником.'
                     + ' Оформление может отличаться у разных выпусков.'),
            license=('Изображение бренда из розничного каталога; свободная лицензия не заявлена.'
                     + ' Товарные знаки принадлежат правообладателям.'),
            productKind=item['productKind'],
        )
        output.append(record)
    # Retain unrelated edits and all original records verbatim.
    combined = [item for item in original if item['id'] not in ids] + output
    assert len({item['id'] for item in combined}) == len(combined)
    target.write_text(json.dumps(combined, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    report = {
        'reviewedImages': len(output), 'newRecords': len(ids - old.keys()),
        'totalRecords': len(combined),
        'totalBrands': len({item['brand'] for item in combined}),
        'newBrandCounts': dict(sorted(Counter(item['brand'] for item in output).items())),
        'localFilesWritten': len(output) * 2,
        'checks': ['unique ids', 'unique reviewed titles', 'unique image hashes',
                   'decoded source images', 'HTTPS provenance', 'explicit product kind'],
        'files': [item['image'] for item in output] + [item['thumbnail'] for item in output],
    }
    (QA / 'import-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'files'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
