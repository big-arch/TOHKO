"""Link archive images to retailer models only by source URL or exact model identity."""
from collections import defaultdict
import re
import unicodedata
from urllib.parse import urlsplit, urlunsplit


def normal(value):
    value = unicodedata.normalize('NFKD', str(value or '').casefold().replace('ё', 'е'))
    value = ''.join(letter for letter in value if not unicodedata.combining(letter))
    return re.sub(r'[^a-zа-я0-9]+', ' ', value).strip()


def source_key(value):
    parts = urlsplit(value or '')
    host = (parts.hostname or '').encode('idna').decode('ascii').removeprefix('www.')
    if parts.scheme != 'https' or not host or parts.username:
        return ''
    return urlunsplit(('https', host, parts.path.rstrip('/'), '', ''))


def model_key(row):
    brand = normal(row.get('brand'))
    title = normal(row.get('model') or row.get('title'))
    # Only boundary labels are removed. No fuzzy matching, token reordering, or DEN guessing.
    for prefix in ('колготки ', 'чулки ', 'tights ', 'stockings '):
        if title.startswith(prefix):
            title = title[len(prefix):]
            break
    if title.startswith(brand + ' '):
        title = title[len(brand) + 1:]
    if title.endswith(' ' + brand):
        title = title[:-len(brand) - 1]
    if not brand or not title:
        return None
    return brand, title, row.get('productKind', 'колготки'), row.get('den')


def link_catalog(packages, catalogue):
    by_source, by_model = defaultdict(list), defaultdict(list)
    for row in catalogue['items']:
        source = source_key(row.get('source'))
        if source:
            by_source[source].append(row)
        key = model_key(row)
        if key:
            by_model[key].append(row)
    matches, reverse, modes = {}, {}, defaultdict(int)
    for package in packages:
        # A variant can describe a different size/model; only the package's primary source is exact.
        candidates = by_source.get(source_key(package.get('source')), [])
        mode = 'source'
        candidates = [row for row in candidates if normal(row.get('brand')) == normal(package.get('brand'))]
        if not candidates:
            candidates = by_model.get(model_key(package), [])
            mode = 'model'
        if len(candidates) != 1:
            continue
        row = candidates[0]
        matches[package['id']] = {key: row.get(key) for key in
            ('brand', 'title', 'priceRub', 'oldPriceRub', 'priceFrom', 'availability', 'checkedAt', 'source')}
        matches[package['id']].update(catalogId=row['id'], matchType=mode)
        reverse.setdefault(row['id'], package['id'])
        modes[mode] += 1
    return {'version': 1, 'checkedAt': catalogue.get('checkedAt'),
            'brands': sorted({row['brand'] for row in catalogue['items']}, key=str.casefold),
            'matches': matches, 'packageByCatalog': reverse, 'matchCounts': dict(modes)}
