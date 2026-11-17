"""Decode every published catalogue image and thumbnail without changing any assets."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'tights-guide'


def run():
    runtime = Path(r'C:\Users\Артур\Documents\CODEX_сайт_ТОНКО\.cache\pillow-runtime')
    if runtime.is_dir():
        sys.path.insert(0, str(runtime))
    from PIL import Image

    source = SITE / 'data/catalog.json'
    payload = source.read_bytes()
    data = json.loads(payload)
    assets = {}
    displayed = 0
    for item in data['items']:
        if item.get('image'):
            displayed += 1
            assert item.get('thumbnail'), item['id']
        for key in ['image', 'thumbnail']:
            relative = item.get(key)
            if not relative:
                continue
            file = (SITE / relative).resolve()
            assert relative.startswith('assets/catalog/') and file.is_relative_to(SITE.resolve()), relative
            with Image.open(file) as image:
                image.load()  # Actual pixel decode, stronger than a file/header existence check.
                assert image.format == 'WEBP' and image.width > 0 and image.height > 0, relative
                if key == 'image':
                    assert image.size == (item['width'], item['height']), (item['id'], image.size, item['width'], item['height'])
                assets[relative] = {'width': image.width, 'height': image.height, 'bytes': file.stat().st_size}
    assert source.read_bytes() == payload, 'Catalogue changed while its images were being checked'
    report = {'checkedAt': datetime.now(timezone.utc).isoformat(), 'models': len(data['items']), 'modelsWithPhoto': displayed, 'modelsAwaitingPhoto': len(data['items']) - displayed, 'decodedFiles': len(assets), 'totalBytes': sum(asset['bytes'] for asset in assets.values()), 'catalogSha256': hashlib.sha256(payload).hexdigest(), 'errors': []}
    output = ROOT / 'qa/catalog18-ui'
    output.mkdir(parents=True, exist_ok=True)
    (output / 'image-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    run()
