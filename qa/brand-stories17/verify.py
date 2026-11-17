"""Validate sourced histories, local photographs, and archive coverage without network."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / 'tights-guide'
sys.path.insert(0, str(ROOT / '.cache/pillow-runtime'))
sys.path.insert(0, r'C:\Users\Артур\Documents\CODEX_сайт_ТОНКО\.cache\pillow-runtime')
from PIL import Image

data = json.loads((SITE / 'data/brand-stories.json').read_text(encoding='utf-8'))['items']
archive = json.loads((SITE / 'data/packaging.json').read_text(encoding='utf-8'))
brands = {x['brand'] for x in archive}
assert len({x['brand'] for x in data}) == len(data)
assert brands <= {x['brand'] for x in data}
rows = []
for item in data:
    assert item['paragraphs'] and len(' '.join(item['paragraphs']).split()) <= 120
    assert item['sources'] and all(x['title'] and x['url'].startswith('https://') for x in item['sources'])
    row = {'brand': item['brand'], 'photo': bool(item['photo'])}
    photo = item['photo']
    if photo:
        assert all(photo.get(x) for x in ('alt', 'caption', 'credit', 'license'))
        assert all(photo[x].startswith('https://') for x in ('source', 'imageSource'))
        for key in ('src', 'thumb'):
            path = (SITE / photo[key]).resolve()
            assert path.is_relative_to(SITE.resolve()) and path.is_file()
            with Image.open(path) as image:
                image.load()
                if key == 'src':
                    assert image.size == (photo['width'], photo['height'])
                if photo[key].startswith('assets/brand-stories/'):
                    assert image.format == 'WEBP' and max(image.size) <= (1200 if key == 'src' else 480)
        row['sha256'] = hashlib.sha256((SITE / photo['src']).read_bytes()).hexdigest()
    rows.append(row)
report = {'histories': len(data), 'photos': sum(x['photo'] for x in rows),
          'archivePackages': len(archive), 'archiveBrands': len(brands),
          'photoExceptions': [x['brand'] for x in rows if not x['photo']], 'rows': rows}
Path(__file__).with_name('verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
sys.stdout.reconfigure(encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k != 'rows'}, ensure_ascii=False))
