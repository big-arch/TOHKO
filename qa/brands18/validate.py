"""Validate the separate reviewed brands18 package without changing production."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
QA = Path(__file__).resolve().parent
SITE = ROOT / 'tights-guide'
sys.path.insert(0, str(Path.home() / 'Documents/CODEX_сайт_ТОНКО/.cache/pillow-runtime'))
from PIL import Image
sys.stdout.reconfigure(encoding='utf-8')

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

records = read(QA / 'approved-records.json')
inputs = read(QA / 'approved-input.json')
stories = read(QA / 'brand-stories.json')['items']
production = read(SITE / 'data/packaging.json')
ids = [r['id'] for r in records]
titles = [(r['brandSlug'], r['title']) for r in records]
hashes = []
missing = []
wrong_dimensions = []
size_bytes = 0
for row in records:
    assert row['source'].startswith('https://') and row['imageSource'].startswith('https://')
    assert row['productKind'] in ('колготки', 'чулки'), row['id']
    for field in ('image', 'thumbnail'):
        path = SITE / row[field]
        if not path.is_file():
            missing.append(row[field])
            continue
        size_bytes += path.stat().st_size
        with Image.open(path) as image:
            image.load()
            if field == 'image' and image.size != (row['width'], row['height']):
                wrong_dimensions.append(row['id'])
        if field == 'image':
            hashes.append(hashlib.sha256(path.read_bytes()).hexdigest())

photo_paths = [SITE / story['photo'][field] for story in stories for field in ('src', 'thumb')]
for path in photo_paths:
    if path.is_file():
        size_bytes += path.stat().st_size
        with Image.open(path) as image:
            image.load()

asset_paths = {row[field] for row in records for field in ('image', 'thumbnail')}
actual_paths = {p.relative_to(SITE).as_posix() for p in (SITE / 'assets/packaging18-special').glob('*.webp')}
production_ids = {r['id'] for r in production}
production_rows = {r['id']: r for r in production}
validation = {
    'packagingCount': len(records),
    'brandCounts': dict(Counter(r['brand'] for r in records)),
    'productKinds': dict(Counter(r['productKind'] for r in records)),
    'uniqueIds': len(ids) == len(set(ids)),
    'uniqueTitles': len(titles) == len(set(titles)),
    'uniqueImageHashes': len(hashes) == len(set(hashes)),
    'reviewedInputMatchesRecords': {r['id'] for r in records} == {'pkg-' + r['id'] for r in inputs},
    'allInputsVisuallyApproved': all(r['review']['approved'] and r['review']['noExplicitNudity'] for r in inputs),
    'productionIdCollisions': sorted(r['id'] for r in records if r['id'] in production_ids and r != production_rows[r['id']]),
    'integratedRecordsUnchanged': sum(r['id'] in production_ids and r == production_rows[r['id']] for r in records),
    'missingAssetPaths': missing,
    'wrongDimensions': wrong_dimensions,
    'unreferencedPackagingAssets': sorted(actual_paths - asset_paths),
    'storyCount': len(stories),
    'storyPhotoPathsExist': all(p.is_file() for p in photo_paths),
    'publishedImageFileCount': len(asset_paths) + len(photo_paths),
    'publishedImageBytes': size_bytes,
    'checked': '2026-11-17',
    'notes': [
        'Все 38 снимков Charnos из UK Tights исключены как обычные фотографии на модели.',
        '1 модель носков Platino исключена по области запроса.',
        'Варианты цвета и размера не создают отдельные записи.',
        '6 дополнительных упаковок Platino из Senorella визуально проверены; коллаж Reductor 538 с чужим вкладышем исключён.',
        'Дополнительные карточки Elegant Up не дали скачиваемого материала из-за просроченного TLS-сертификата; проверка TLS сохранена.'
    ]
}
(QA / 'validation.json').write_text(json.dumps(validation, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
assert validation['uniqueIds'] and validation['uniqueTitles'] and validation['uniqueImageHashes']
assert validation['reviewedInputMatchesRecords'] and validation['allInputsVisuallyApproved']
assert not validation['productionIdCollisions']
assert not missing and not wrong_dimensions and not validation['unreferencedPackagingAssets']
assert validation['storyPhotoPathsExist']
print(json.dumps(validation, ensure_ascii=False, indent=2))
