"""Real-browser catalogue QA at 320/390/768/1440 px; --fixture never changes production data."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
from threading import Thread
from urllib.parse import urlencode, urlsplit, parse_qs

RUNTIME = Path(r'C:\Users\Артур\Documents\CODEX_сайт_ТОНКО\.cache\pw-runtime')
if RUNTIME.is_dir():
    sys.path.insert(0, str(RUNTIME))
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'tights-guide'
SPEC = importlib.util.spec_from_file_location('build_catalog', ROOT / 'scripts/build-catalog.py')
BUILD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD)


def make_fixture(folder: Path) -> dict:
    """Synthetic records stay in a temporary QA directory and are labelled as such."""
    now = datetime.now(timezone.utc).isoformat()
    packages = json.loads((SITE / 'data/packaging.json').read_text(encoding='utf-8'))
    package = next(item for item in packages if (SITE / item['image']).is_file())
    (folder / 'assets/catalog').mkdir(parents=True)
    shutil.copyfile(SITE / package['image'], folder / 'assets/catalog/qa-fixture.webp')
    rows = []
    for index in range(117):
        brand = ['QA Alpha', 'QA Beta', 'QA Gamma'][index % 3]
        rows.append({'id': f'qa-{index:03d}', 'brand': brand, 'brandSlug': brand.lower().replace(' ', '-'), 'model': f'Тестовая модель {index:03d}', 'title': f'{brand} Тестовая модель {index:03d}', 'productKind': 'колготки' if index % 2 else 'чулки', 'gender': 'men' if index % 5 == 0 else 'women', 'den': 20 if index % 2 else 40, 'priceRub': None if index % 13 == 0 else [450, 900, 1500, 2500, 6000][index % 5], 'priceFrom': index % 7 == 0, 'availability': 'out_of_stock' if index % 11 == 0 else 'in_stock', 'checkedAt': now, 'source': 'https://example.org/qa/' + str(index), 'sourceName': 'QA only', 'image': 'assets/catalog/qa-fixture.webp', 'thumbnail': 'assets/catalog/qa-fixture.webp', 'width': package['width'], 'height': package['height'], 'description': 'Синтетическая запись только для проверки интерфейса.', 'categories': [], 'packageId': package['id'] if index == 1 else None})
    data = {'version': 1, 'source': {'id': 'qa', 'name': 'QA only', 'url': 'https://example.org/'}, 'checkedAt': now, 'items': rows}
    (folder / 'input.json').write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    rate = {'version': 1, 'base': 'USD', 'quote': 'RUB', 'rubPerUsd': 82.5143, 'date': now[:10], 'checkedAt': now, 'source': 'https://www.cbr.ru/currency_base/daily/', 'sourceName': 'Банк России'}
    (folder / 'rate.json').write_text(json.dumps(rate), encoding='utf-8')
    BUILD.build(folder / 'input.json', folder / 'rate.json', folder)
    return data


def check_real_integration(context, base, rows, output):
    """Exercise actual archive cards, not only the serialized match index."""
    packages = json.loads((SITE / 'data/packaging.json').read_text(encoding='utf-8'))
    links = json.loads((SITE / 'data/catalog-prices.json').read_text(encoding='utf-8'))
    rate = json.loads((SITE / 'data/exchange-rate.json').read_text(encoding='utf-8'))
    by_product = {row['id']: row for row in rows}
    by_package = {row['id']: row for row in packages}
    report = {'matches': len(links['matches']), 'checks': [], 'errors': [], 'browserWarnings': [], 'archiveCardsChecked': 0}
    page = context.new_page()
    all_errors = []
    page.on('pageerror', lambda error: all_errors.append({'url': page.url, 'message': str(error), 'stack': error.stack}))
    page.goto(base + 'packaging.html', wait_until='networkidle')
    page.locator('.portal-nav a[href="brands.html"]').click()
    page.wait_for_load_state('networkidle')
    baseline = list(all_errors)
    all_errors.clear()
    report['baselineBrowserMessages'] = baseline
    now = datetime.now(timezone.utc)

    def same_spacing(value):
        return re.sub(r'\s+', ' ', value).strip()

    def expected_price(offer):
        prefix = 'от ' if offer.get('priceFrom') else ''
        rub = prefix + BUILD.rub_text(offer['priceRub']) + ' ₽'
        usd = '≈ ' + prefix + f'${offer["priceRub"] / rate["rubPerUsd"]:,.2f}' if BUILD.rate_valid(rate, now) else ''
        return same_spacing(rub), same_spacing(usd)

    # This catches accidental differences between the static first page and hydration.
    page.goto(base + 'catalog.html', wait_until='networkidle')
    ssr_ids = re.findall(r'<article class="catalog-card" data-id="([^"]+)"', (SITE / 'catalog.html').read_text(encoding='utf-8'))
    hydrated_ids = page.locator('.catalog-card').evaluate_all('(nodes) => nodes.map(node => node.dataset.id)')
    assert hydrated_ids == ssr_ids
    report['checks'].append('static first 48 and hydrated default order agree for real Latin/Cyrillic brands')

    for width in (320, 390, 768, 1440):
        page.set_viewport_size({'width': width, 'height': 1000})
        page.goto(base + 'catalog.html', wait_until='networkidle')
        nav = page.locator('.portal-nav')
        assert nav.locator('a[href="catalog.html"]').count() == 1
        assert nav.locator('a[aria-current="page"]').get_attribute('href') == 'catalog.html'
        if width <= 768:
            toggle = page.locator('[data-nav-toggle]')
            toggle.click()
            assert toggle.get_attribute('aria-expanded') == 'true'
            assert nav.locator('a[href="catalog.html"]').is_visible()
            assert page.evaluate('''() => [...document.querySelectorAll('.portal-nav a')].every(el => {const r=el.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth+1;})''')
            page.screenshot(path=str(output / f'catalog-nav-{width}.png'))
            nav.locator('a[href="catalog.html"]').click()
            page.wait_for_load_state('networkidle')
            assert page.locator('[data-nav-toggle]').get_attribute('aria-expanded') == 'false'
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    nav_pages = 0
    for file in SITE.glob('*.html'):
        nav = re.search(r'<nav\b[^>]*class="portal-nav"[^>]*>.*?</nav>', file.read_text(encoding='utf-8'), re.S)
        if nav:
            assert nav.group().count('href="catalog.html"') == 1, file.name
            nav_pages += 1
    report['navigationPages'] = nav_pages
    report['checks'].append('new catalogue link appears once in every shared navigation; mobile menu and active page work at all four widths')

    for package_id, offer in links['matches'].items():
        assert package_id in by_package and offer['catalogId'] in by_product
        product = by_product[offer['catalogId']]
        for key in ['brand', 'title', 'priceRub', 'oldPriceRub', 'priceFrom', 'availability', 'checkedAt', 'source']:
            assert offer.get(key) == product.get(key), (package_id, key)
        reverse = links['packageByCatalog'][offer['catalogId']]
        assert links['matches'][reverse]['catalogId'] == offer['catalogId']

    page.set_viewport_size({'width': 1440, 'height': 1100})
    page.goto(base + 'packaging.html', wait_until='networkidle')
    matched_brands = sorted({by_package[package_id]['brand'] for package_id in links['matches']})
    checked = set()
    for brand in matched_brands:
        page.locator('#pack-brand').select_option(brand)
        while page.locator('[data-more-brand]').count():
            page.locator('[data-more-brand]').first.evaluate('(button) => button.click()')
        cards = page.locator('.pack-card').evaluate_all('''nodes => nodes.map(node => ({id: node.querySelector('[data-pack]').dataset.pack, rub: node.querySelector('.pack-retail-price strong')?.textContent || null, usd: node.querySelector('.pack-retail-price span')?.textContent || '', note: node.querySelector('.pack-retail-price small')?.textContent || ''}))''')
        for card in cards:
            offer = links['matches'].get(card['id'])
            if not offer or not BUILD.price_known(offer.get('priceRub')):
                assert card['rub'] is None, card
            else:
                rub, usd = expected_price(offer)
                assert same_spacing(card['rub']) == rub, card
                assert same_spacing(card['usd']) == usd, card
                assert BUILD.date_text(offer.get('checkedAt')) in card['note']
                assert ('цена требует обновления' in card['note']) == BUILD.stale(offer.get('checkedAt'), now)
            if offer:
                checked.add(card['id'])
        report['archiveCardsChecked'] += len(cards)
    assert checked == set(links['matches']), (len(checked), len(links['matches']))
    report['knownPrices'] = sum(BUILD.price_known(offer.get('priceRub')) for offer in links['matches'].values())
    report['unknownPrices'] = len(checked) - report['knownPrices']
    report['checks'].append('every actual archive match renders the same RUB/USD/date as its catalogue model; unmatched and unknown prices stay absent')

    known = [package_id for package_id, offer in links['matches'].items() if BUILD.price_known(offer.get('priceRub'))]
    unknown = [package_id for package_id, offer in links['matches'].items() if not BUILD.price_known(offer.get('priceRub'))]
    representatives = [known[0]]
    if unknown:
        representatives.append(unknown[0])
    long_title = max(known, key=lambda package_id: len(by_package[package_id]['title']))
    representatives.append(long_title)
    for index, package_id in enumerate(dict.fromkeys(representatives)):
        offer = links['matches'][package_id]
        page.goto(base + 'packaging.html?' + urlencode({'pack': package_id}), wait_until='networkidle')
        assert page.locator('#pack-dialog').is_visible()
        assert page.locator('#pack-retail .pack-price-source').get_attribute('href') == offer['source']
        assert page.locator('#pack-source').get_attribute('href') == by_package[package_id]['source']
        link = page.locator('#pack-retail a[href^="catalog.html"]')
        assert parse_qs(urlsplit(link.get_attribute('href')).query)['product'] == [offer['catalogId']]
        link.click()
        page.locator('#catalog-dialog').wait_for(state='visible')
        page.wait_for_load_state('networkidle')
        assert page.locator('#catalog-title').inner_text() == by_product[offer['catalogId']]['title']
        assert page.locator('#catalog-source').get_attribute('href') == offer['source']
        assert page.locator('#catalog-package').get_attribute('href') == 'packaging.html?pack=' + links['packageByCatalog'][offer['catalogId']]
        if not BUILD.price_known(offer.get('priceRub')):
            assert page.locator('#catalog-detail-price').inner_text() == 'Цена не указана'
        if index == 0:
            page.locator('#catalog-package').click()
            page.locator('#pack-dialog').wait_for(state='visible')
            page.wait_for_load_state('networkidle')
    report['checks'].append('real known/unknown/long-title archive links open the exact product and return to its linked archive entry; image and price source links remain distinct')

    for width in (320, 390, 768, 1440):
        page.set_viewport_size({'width': width, 'height': 1000})
        page.goto(base + 'packaging.html?' + urlencode({'pack': long_title}), wait_until='networkidle')
        page.locator('#pack-retail').scroll_into_view_if_needed()
        assert page.evaluate('document.getElementById("pack-dialog").scrollWidth <= document.getElementById("pack-dialog").clientWidth + 1')
        page.evaluate('''async () => {await Promise.all([...document.images].filter(image=>{const r=image.getBoundingClientRect();return r.width&&r.height&&r.top<innerHeight&&r.bottom>0;}).map(image=>image.decode().catch(()=>{})));}''')
        page.screenshot(path=str(output / f'archive-price-{width}.png'))
    report['checks'].append('long real model name, price and sources fit archive details at 320/390/768/1440')

    stories = json.loads((SITE / 'data/brand-stories.json').read_text(encoding='utf-8'))
    story_by_brand = {story['brand']: story for story in stories['items']}
    report['brandStories'] = []
    for brand in ['Aristoc', 'Charnos', 'Platino', 'Pearl & Poseidon']:
        story = story_by_brand[brand]
        brand_packages = [package for package in packages if package['brand'] == brand]
        assert brand_packages, brand
        page.set_viewport_size({'width': 1440, 'height': 1100})
        page.goto(base + 'packaging.html?' + urlencode({'brand': brand, 'pack': brand_packages[0]['id']}), wait_until='networkidle')
        section = page.locator('#pack-brand-story')
        assert section.is_visible()
        heading = ('История ' if story.get('founded') else 'О бренде ') + brand
        assert page.locator('#pack-brand-story-title').inner_text() == heading
        assert page.locator('#pack-brand-story-text p').all_text_contents() == story['paragraphs']
        assert page.locator('#pack-brand-story-sources a').evaluate_all('(nodes) => nodes.map(node => node.getAttribute("href"))') == [source['url'] for source in story['sources']]
        assert page.locator('#pack-brand-photo-caption').inner_text() == story['photo']['caption']
        assert page.locator('#pack-brand-photo-credit').inner_text() == story['photo']['credit']
        assert page.locator('#pack-brand-photo').get_attribute('src') == story['photo']['src']
        page.locator('#pack-brand-photo').evaluate('async image => {await image.decode();if (!image.naturalWidth) throw Error("Brand image did not decode");}')
        section.evaluate('(section) => {const modal=document.getElementById("pack-dialog");modal.scrollTop += section.getBoundingClientRect().top-modal.getBoundingClientRect().top-82;}')
        page.screenshot(path=str(output / f'history-{story["slug"]}-1440.png'))
        page.locator('#pack-brand-photo-open').click()
        page.locator('#pack-photo-dialog').wait_for(state='visible')
        assert 'Фотография бренда' in page.locator('#pack-photo-match').inner_text()
        assert page.locator('#pack-photo-source').get_attribute('href') == story['photo']['source']
        page.locator('#pack-photo-full').evaluate('async image => {await image.decode();if (!image.naturalWidth) throw Error("Brand viewer image did not decode");}')
        page.keyboard.press('Escape')
        page.locator('#pack-photo-dialog').wait_for(state='hidden')
        assert page.locator('#pack-dialog').is_visible()
        page.wait_for_function('document.activeElement.id === "pack-brand-photo-open"')
        page.set_viewport_size({'width': 390, 'height': 1000})
        page.locator('.pack-brand-story-sources summary').click()
        page.locator('#pack-brand-story-text').evaluate('(section) => {const modal=document.getElementById("pack-dialog");modal.scrollTop += section.getBoundingClientRect().top-modal.getBoundingClientRect().top-82;}')
        assert page.evaluate('document.getElementById("pack-dialog").scrollWidth <= document.getElementById("pack-dialog").clientWidth + 1')
        page.screenshot(path=str(output / f'history-{story["slug"]}-390.png'))
        report['brandStories'].append({'brand': brand, 'archivePackages': len(brand_packages), 'heading': heading, 'paragraphs': len(story['paragraphs']), 'sources': len(story['sources']), 'photoDecoded': True, 'nestedViewerFocusRestored': True})
    report['checks'].append('Aristoc, Charnos, Platino and Pearl & Poseidon: correct story text, dates from data, sources, captions, decoded brand photos, nested viewer and Escape focus restoration')
    native_message = 'Transition was aborted because of invalid state. ViewTransition opt-in disabled'
    baseline_native = any(error['message'] == native_message and not error['stack'] for error in baseline)
    report['browserWarnings'] = [error for error in all_errors if baseline_native and error['message'] == native_message and not error['stack']]
    report['errors'] = [error for error in all_errors if error not in report['browserWarnings']]
    page.close()
    assert not report['errors'], report['errors']
    return report


def run(fixture: bool) -> dict:
    temporary = tempfile.TemporaryDirectory(prefix='catalog18-browser-') if fixture else None
    overlay = Path(temporary.name) if temporary else SITE
    data = make_fixture(overlay) if fixture else json.loads((SITE / 'data/catalog.json').read_text(encoding='utf-8'))
    rows = data['items']
    counts = Counter(item['brand'] for item in rows)
    by_id = {item['id']: item for item in rows}
    out = ROOT / 'qa' / ('catalog18-ui-fixture' if fixture else 'catalog18-ui')
    out.mkdir(exist_ok=True)

    class Handler(SimpleHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'

        def log_message(self, *args):
            pass

        def translate_path(self, path):
            relative = urlsplit(path).path.lstrip('/')
            candidate = (overlay / relative).resolve()
            if fixture and candidate.is_relative_to(overlay.resolve()) and candidate.is_file():
                return str(candidate)
            return super().translate_path(path)

    class Server(ThreadingHTTPServer):
        request_queue_size = 128
        daemon_threads = True

        def handle_error(self, request, client_address):
            # Closing a test page cancels lazy image downloads; that is not a server failure.
            if not isinstance(sys.exc_info()[1], (ConnectionAbortedError, ConnectionResetError, BrokenPipeError)):
                super().handle_error(request, client_address)

    server = Server(('127.0.0.1', 0), partial(Handler, directory=str(SITE)))
    Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}/'
    errors = []
    report = {'fixture': fixture, 'models': len(rows), 'brands': len(counts), 'viewports': [], 'checks': [], 'errors': errors}
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel='chrome', headless=True)
            context = browser.new_context(viewport={'width': 1440, 'height': 1100}, reduced_motion='reduce')
            context.route('**/*', lambda route: route.continue_() if urlsplit(route.request.url).hostname == '127.0.0.1' else route.abort())
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))

            def visit(query=''):
                page.goto(base + 'catalog.html' + query, wait_until='networkidle')
                page.locator('#catalog-tools').wait_for(state='visible')

            def ids():
                return page.locator('.catalog-card').evaluate_all('(els) => els.map(e => e.dataset.id)')

            def wait_visible_images():
                page.evaluate('''async () => { await document.fonts.ready; await Promise.all([...document.images].filter(image => { const r=image.getBoundingClientRect();return r.width&&r.height&&r.top<innerHeight&&r.bottom>0; }).map(image => image.decode().catch(() => {}))); }''')

            visit()
            assert page.locator('h1').inner_text() == 'Колготки и чулки.'
            assert page.locator('.catalog-card').count() == min(48, len(rows))
            assert page.locator('[data-catalog-brand]').count() == len(counts) + 1
            assert len(page.locator('#catalog-brand option').all()) == len(counts) + 1
            assert page.locator('#catalog-brand').input_value() == 'all'
            report['checks'].append('48-card initial DOM, all source brands and meaningful counts')

            for width, height in [(320, 900), (390, 900), (768, 1024), (1440, 1100)]:
                page.set_viewport_size({'width': width, 'height': height})
                visit()
                wait_visible_images()
                page.screenshot(path=str(out / f'catalog-{width}.png'))
                metrics = page.evaluate('''() => ({viewport: innerWidth, document: document.documentElement.scrollWidth, columns: getComputedStyle(document.getElementById('catalog-grid')).gridTemplateColumns.split(' ').length, directoryOpen: document.getElementById('catalog-directory').open, imageFit: getComputedStyle(document.querySelector('.catalog-image img') || document.querySelector('.catalog-image')).objectFit})''')
                assert metrics['document'] <= width + 1, metrics
                assert metrics['columns'] == (2 if width < 600 else 3 if width < 900 else 4), metrics
                if page.locator('.catalog-image img').count():
                    assert metrics['imageFit'] == 'contain'
                report['viewports'].append(metrics)
                page.locator('.catalog-results').evaluate('(el) => window.scrollTo(0, el.getBoundingClientRect().top + scrollY - 100)')
                wait_visible_images()
                page.screenshot(path=str(out / f'catalog-grid-{width}.png'))
            report['checks'].append('320/390/768/1440 layout, no horizontal overflow, contained images')

            page.set_viewport_size({'width': 1440, 'height': 1100})
            visit()
            if len(rows) > 48:
                page.locator('#catalog-more').click()
                assert page.locator('.catalog-card').count() == min(96, len(rows))
                assert page.evaluate('document.activeElement.dataset.product') == ids()[48]
                report['checks'].append('load-more adds at most 48 and focuses the first new card')

            visit()
            for sort, reverse in [('price-asc', False), ('price-desc', True)]:
                page.locator('#catalog-sort').select_option(sort)
                visible = [by_id[id_].get('priceRub') for id_ in ids()]
                known = sorted([item['priceRub'] for item in rows if BUILD.price_known(item.get('priceRub'))], reverse=reverse)
                expected = (known + [None] * (len(rows) - len(known)))[:48]
                assert visible == expected, (sort, visible, expected)
                assert f'sort={sort}' in page.url
            report['checks'].append('global ascending/descending price sort crosses brands')

            sample = next(item for item in rows if BUILD.price_known(item.get('priceRub')))
            visit()
            page.locator('#catalog-brand').select_option(sample['brand'])
            page.locator('#catalog-kind').select_option(sample['productKind'])
            page.locator('#catalog-gender').select_option(sample.get('gender') or 'unknown')
            for id_ in ids():
                item = by_id[id_]
                assert item['brand'] == sample['brand'] and item['productKind'] == sample['productKind'] and (item.get('gender') or 'unknown') == (sample.get('gender') or 'unknown')
            assert ids()
            saved_url = page.url
            expected_ids = ids()
            page.reload(wait_until='networkidle')
            assert page.url == saved_url and ids() == expected_ids
            page.locator('#catalog-query').fill('___нет_такой_модели_qa___')
            page.locator('#catalog-empty').wait_for(state='visible')
            assert not ids()
            page.locator('#catalog-empty-reset').click()
            assert len(ids()) == min(48, len(rows)) and page.locator('#catalog-query').input_value() == ''
            report['checks'].append('combined filters, URL reload, empty result and reset')

            if any(item.get('priceRub') is None for item in rows):
                page.locator('#catalog-price').select_option('unknown')
                assert ids() and all(by_id[id_].get('priceRub') is None for id_ in ids())
                assert page.locator('.catalog-card .catalog-price span').count() == 0
                page.locator('#catalog-reset').click()
            report['checks'].append('unknown prices remain unknown with no fake USD')

            first_id = ids()[0]
            opener = page.locator('[data-product]').first
            opener.click()
            dialog = page.locator('#catalog-dialog')
            assert dialog.is_visible()
            assert page.locator('#catalog-title').inner_text() == by_id[first_id]['title']
            assert page.locator('#catalog-source').get_attribute('href') == by_id[first_id]['source']
            assert 'product=' in page.url
            assert page.locator('#catalog-detail-checked').inner_text()
            page.locator('#catalog-close').focus()
            page.keyboard.press('Shift+Tab')
            assert page.evaluate('document.getElementById("catalog-dialog").contains(document.activeElement)')
            page.keyboard.press('Tab')
            assert page.evaluate('document.activeElement.id') == 'catalog-close'
            page.keyboard.press('Escape')
            assert not dialog.is_visible()
            page.wait_for_function('!new URLSearchParams(location.search).has("product")')
            assert page.evaluate('document.activeElement.dataset.product') == first_id
            assert 'product=' not in page.url
            report['checks'].append('dialog title/source, keyboard wrap, Escape, focus restoration')

            last = rows[-1]
            visit('?' + urlencode({'product': last['id']}))
            assert page.locator('#catalog-dialog').is_visible()
            assert page.locator('#catalog-title').inner_text() == last['title']
            page.keyboard.press('Escape')
            report['checks'].append('product deep link opens even outside the first rendered page')

            page.set_viewport_size({'width': 390, 'height': 900})
            visit('?' + urlencode({'product': sample['id']}))
            assert page.evaluate('document.getElementById("catalog-dialog").scrollWidth <= document.getElementById("catalog-dialog").clientWidth + 1')
            wait_visible_images()
            page.screenshot(path=str(out / 'catalog-dialog-390.png'))
            page.keyboard.press('Escape')

            rate_route = '**/data/exchange-rate.js?*'
            context.route(rate_route, lambda route: route.fulfill(content_type='text/javascript', body='window.TONKO_EXCHANGE_RATE = {base:"USD",quote:"RUB",rubPerUsd:0,date:"2099-01-01",checkedAt:"2099-01-01T00:00:00Z"};'))
            visit()
            assert page.locator('.catalog-card .catalog-price span').count() == 0
            assert 'Курс USD пока недоступен' in page.locator('#catalog-rate').inner_text()
            assert page.locator('.catalog-card .catalog-price strong').count()
            context.unroute(rate_route)
            report['checks'].append('malformed/future exchange data leaves functioning RUB catalogue')

            data_route = '**/data/catalog.js?*'
            context.route(data_route, lambda route: route.fulfill(content_type='text/javascript', body='window.TONKO_CATALOG = null;'))
            page.goto(base + 'catalog.html', wait_until='networkidle')
            assert page.locator('.catalog-card').count() == min(48, len(rows))
            assert page.locator('#catalog-runtime-note').is_visible()
            assert page.locator('#catalog-tools').is_hidden()
            context.unroute(data_route)
            report['checks'].append('data loading failure retains useful SSR cards and seller links')

            no_js = browser.new_context(java_script_enabled=False, viewport={'width': 390, 'height': 900})
            static_page = no_js.new_page()
            static_page.goto(base + 'catalog.html', wait_until='domcontentloaded')
            assert static_page.locator('.catalog-card').count() == min(48, len(rows))
            assert static_page.locator('noscript').is_visible()
            report['checks'].append('no-JavaScript initial catalogue and factual subset explanation')
            no_js.close()
            assert not errors, errors
            if not fixture:
                report['integration'] = check_real_integration(context, base, rows, out)
            context.close()
            browser.close()
    finally:
        server.shutdown()
        if temporary:
            temporary.cleanup()
    report['checkedAt'] = datetime.now(timezone.utc).isoformat()
    (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', action='store_true', help='Use temporary synthetic QA-only records.')
    args = parser.parse_args()
    result = run(args.fixture)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
