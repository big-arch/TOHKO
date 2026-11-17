"""Build small source/price links for packaging cards without copying the full catalogue."""
import json
from pathlib import Path
from catalog_links import link_catalog

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'tights-guide/data'


def main():
    source = DATA / 'catalog.json'
    if not source.exists():
        raise SystemExit('Verified catalogue is required before building price links')
    result = link_catalog(json.loads((DATA / 'packaging.json').read_text('utf-8')),
                          json.loads(source.read_text('utf-8')))
    (DATA / 'catalog-prices.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    (DATA / 'catalog-prices.js').write_text('window.TONKO_CATALOG_PRICES = ' +
        json.dumps(result, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c') + ';\n', 'utf-8')
    print(f'Exact archive/price matches: {len(result["matches"])}; catalogue brands: {len(result["brands"])}')


if __name__ == '__main__':
    main()
