"""Browser integration of archive prices and catalogue links using a temporary QA site."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from functools import partial
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from threading import Thread
from urllib.parse import urlencode, urlsplit, parse_qs

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'tights-guide'
RUNTIME = Path(r'C:\Users\Артур\Documents\CODEX_сайт_ТОНКО\.cache\pw-runtime')
if RUNTIME.is_dir():
    sys.path.insert(0, str(RUNTIME))
sys.path.insert(0, str(ROOT / 'scripts'))
from catalog_links import link_catalog

SPEC = importlib.util.spec_from_file_location('build_catalog', ROOT / 'scripts/build-catalog.py')
BUILD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD)


def create_site(folder):
    target = folder / 'tights-guide'
    (target / 'data').mkdir(parents=True)
    (folder / 'scripts').mkdir()
    for name in ['index.html', 'catalog.js', 'catalog.css', 'packaging.js', 'packaging.css']:
        shutil.copyfile(SITE / name, target / name)
    shutil.copyfile(ROOT / 'scripts/build-packaging.py', folder / 'scripts/build-packaging.py')
    all_packages = json.loads((SITE / 'data/packaging.json').read_text(encoding='utf-8'))
    packages, seen = [], set()
    for package in all_packages:
        if package['brand'] not in seen:
            packages.append(package)
            seen.add(package['brand'])
        if len(packages) == 7:
            break
    stories = json.loads((SITE / 'data/brand-stories.json').read_text(encoding='utf-8'))
    stories = {**stories, 'items': [story for story in stories['items'] if story['brand'] in seen]}
    assets = {package[key] for package in packages for key in ['image', 'thumbnail']}
    assets |= {story['photo'][key] for story in stories['items'] if story.get('photo') for key in ['src', 'thumb']}
    for asset in assets:
        (target / asset).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SITE / asset, target / asset)
    (target / 'assets/catalog').mkdir(parents=True)
    shutil.copyfile(SITE / packages[0]['image'], target / 'assets/catalog/qa-archive.webp')
    now = datetime.now(timezone.utc)
    dates = [now.isoformat(), now.isoformat(), (now - timedelta(hours=72)).isoformat(), None, '2026-02-30T12:00:00Z', now.isoformat()]
    rows = []
    for index, package in enumerate(packages[:6]):
        model = package['title'] if index < 5 else 'QA unrelated model'
        rows.append({'id': f'qa-archive-{index}', 'brand': package['brand'], 'model': model, 'title': package['brand'] + ' ' + model, 'productKind': package.get('productKind', 'колготки'), 'den': package.get('den'), 'gender': 'unknown', 'priceRub': None if index == 1 else 825.143 if index == 2 else 1000, 'priceFrom': index == 2, 'availability': 'out_of_stock' if index in (1, 2) else 'in_stock', 'checkedAt': dates[index], 'source': f'https://example.org/qa-price/{index}', 'sourceName': 'QA only', 'image': 'assets/catalog/qa-archive.webp', 'thumbnail': 'assets/catalog/qa-archive.webp', 'width': packages[0]['width'], 'height': packages[0]['height'], 'photos': [], 'categories': []})
    catalogue = {'version': 1, 'source': {'id': 'qa', 'name': 'QA only', 'url': 'https://example.org/'}, 'checkedAt': now.isoformat(), 'items': rows}
    links = link_catalog(packages, catalogue)
    assert len(links['matches']) == 5
    rate = {'version': 1, 'base': 'USD', 'quote': 'RUB', 'rubPerUsd': 82.5143, 'date': now.date().isoformat(), 'checkedAt': now.isoformat(), 'source': 'https://www.cbr.ru/currency_base/daily/', 'sourceName': 'Банк России'}
    for name, data in [('packaging.json', packages), ('brand-stories.json', stories), ('package-looks.json', {'version': 1, 'items': []}), ('catalog.json', catalogue), ('catalog-prices.json', links), ('exchange-rate.json', rate)]:
        (target / 'data' / name).write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    (target / 'data/catalog-prices.js').write_text(BUILD.script_data('TONKO_CATALOG_PRICES', links), encoding='utf-8')
    BUILD.build(target / 'data/catalog.json', target / 'data/exchange-rate.json', target, site=target)
    completed = subprocess.run([sys.executable, str(folder / 'scripts/build-packaging.py'), '--packaging-only'], capture_output=True, text=True, encoding='utf-8', env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})
    assert completed.returncode == 0, completed.stderr
    return target, packages, rows, links


def run():
    from playwright.sync_api import sync_playwright
    watched = [SITE / name for name in ['packaging.html', 'data/packaging.json', 'data/packaging.js']]
    before = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in watched}
    report = {'fixture': True, 'checks': [], 'errors': []}
    output = ROOT / 'qa/catalog18-ui-archive'
    output.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='catalog18-archive-') as temp:
        target, packages, rows, links = create_site(Path(temp))

        class Handler(SimpleHTTPRequestHandler):
            protocol_version = 'HTTP/1.1'

            def log_message(self, *args):
                pass

            def translate_path(self, path):
                relative = urlsplit(path).path.lstrip('/')
                local = (target / relative).resolve()
                return str(local) if local.is_relative_to(target.resolve()) and local.is_file() else super().translate_path(path)

        class Server(ThreadingHTTPServer):
            request_queue_size = 128
            daemon_threads = True

            def handle_error(self, request, address):
                if not isinstance(sys.exc_info()[1], (ConnectionAbortedError, ConnectionResetError, BrokenPipeError)):
                    super().handle_error(request, address)

        server = Server(('127.0.0.1', 0), partial(Handler, directory=str(SITE)))
        Thread(target=server.serve_forever, daemon=True).start()
        base = f'http://127.0.0.1:{server.server_port}/'
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(channel='chrome', headless=True)
                context = browser.new_context(viewport={'width': 1440, 'height': 1100}, reduced_motion='reduce')
                context.route('**/*', lambda route: route.continue_() if urlsplit(route.request.url).hostname == '127.0.0.1' else route.abort())
                baseline = context.new_page()
                baseline_errors = []
                baseline.on('pageerror', lambda error: baseline_errors.append(str(error)))
                baseline.goto(base + 'packaging.html', wait_until='networkidle')
                baseline.locator('.portal-nav a[href="brands.html"]').click()
                baseline.wait_for_load_state('networkidle')
                baseline.close()
                report['baselineBrowserMessages'] = baseline_errors
                page = context.new_page()
                phase = ['initial archive']
                page.on('pageerror', lambda error: report['errors'].append({'phase': phase[0], 'url': page.url, 'message': str(error), 'stack': error.stack}))
                page.goto(base + 'packaging.html', wait_until='networkidle')
                assert page.evaluate('typeof TONKO_CATALOG_HELPERS.priceText') == 'function'
                assert page.locator('.pack-retail-price').count() == 4
                fresh = page.locator(f'.pack-card:has([data-pack="{packages[0]["id"]}"]) .pack-retail-price')
                assert '≈ $12.12' in fresh.inner_text()
                assert '1\xa0000 ₽' in fresh.inner_text()
                assert 'требует обновления' not in fresh.inner_text()
                assert page.locator(f'.pack-card:has([data-pack="{packages[1]["id"]}"]) .pack-retail-price').count() == 0
                stale = page.locator(f'.pack-card:has([data-pack="{packages[2]["id"]}"]) .pack-retail-price')
                assert '≈ от $10.00' in stale.inner_text() and 'цена требует обновления' in stale.inner_text() and 'нет в наличии' in stale.inner_text()
                for index in (3, 4):
                    bad_date = page.locator(f'.pack-card:has([data-pack="{packages[index]["id"]}"]) .pack-retail-price').inner_text()
                    assert 'дата не указана' in bad_date and '1970' not in bad_date and '02.03.2026' not in bad_date
                report['checks'].append('archive cards: RUB, approximate USD, priceFrom, unknown price, 72-hour stale and invalid/null dates')

                for index, package in enumerate(packages[:5]):
                    phase[0] = f'archive product {index}'
                    page.goto(base + 'packaging.html?' + urlencode({'pack': package['id']}), wait_until='networkidle')
                    assert page.locator('#pack-dialog').is_visible()
                    retail = page.locator('#pack-retail')
                    assert retail.locator('a.pack-price-source').get_attribute('href') == rows[index]['source']
                    assert page.locator('#pack-source').get_attribute('href') == package['source']
                    product_link = retail.locator('a[href^="catalog.html"]').get_attribute('href')
                    assert parse_qs(urlsplit(product_link).query)['product'] == [rows[index]['id']]
                    if index == 1:
                        assert retail.locator('.pack-retail-price').count() == 0
                    if index == 0:
                        phase[0] = 'archive to catalogue link'
                        retail.locator('a[href^="catalog.html"]').click()
                        page.locator('#catalog-dialog').wait_for(state='visible')
                        page.wait_for_load_state('networkidle')
                        assert page.locator('#catalog-dialog').is_visible()
                        assert page.locator('#catalog-title').inner_text() == rows[index]['title']
                        assert page.locator('#catalog-source').get_attribute('href') == rows[index]['source']
                        assert page.locator('#catalog-package').get_attribute('href') == 'packaging.html?pack=' + package['id']
                report['checks'].append('archive image source and price seller source are separate; product and reverse archive deep links work')

                for index, key in [(5, 'brand'), (6, 'q')]:
                    phase[0] = 'archive unmatched fallback'
                    page.goto(base + 'packaging.html?' + urlencode({'pack': packages[index]['id']}), wait_until='networkidle')
                    retail = page.locator('#pack-retail')
                    assert retail.locator('.pack-retail-price').count() == 0
                    query = parse_qs(urlsplit(retail.locator('a').first.get_attribute('href')).query)
                    assert query[key] == [packages[index]['brand']]
                report['checks'].append('unmatched models never borrow prices; brand and search fallbacks are explicit')

                context.route('**/data/exchange-rate.js?*', lambda route: route.fulfill(content_type='text/javascript', body='window.TONKO_EXCHANGE_RATE = null;'))
                phase[0] = 'missing exchange rate'
                page.goto(base + 'packaging.html?' + urlencode({'pack': packages[0]['id']}), wait_until='networkidle')
                assert '1\xa0000 ₽' in page.locator('#pack-retail').inner_text()
                assert '≈ $' not in page.locator('#pack-retail').inner_text()
                context.unroute('**/data/exchange-rate.js?*')
                report['checks'].append('missing exchange rate preserves archive RUB price without USD')

                for width in (320, 390, 768, 1440):
                    phase[0] = f'archive viewport {width}'
                    page.set_viewport_size({'width': width, 'height': 1000})
                    page.goto(base + 'packaging.html?' + urlencode({'pack': packages[2]['id']}), wait_until='networkidle')
                    page.locator('#pack-retail').scroll_into_view_if_needed()
                    assert page.evaluate('document.getElementById("pack-dialog").scrollWidth <= document.getElementById("pack-dialog").clientWidth + 1')
                    page.evaluate('''async () => { await Promise.all([...document.images].filter(image=>{const r=image.getBoundingClientRect();return r.width&&r.height&&r.top<innerHeight&&r.bottom>0;}).map(image=>image.decode().catch(()=>{}))); }''')
                    page.screenshot(path=str(output / f'archive-price-{width}.png'))
                report['checks'].append('archive price details fit 320/390/768/1440 without overflow')
                context.close()
                browser.close()
        finally:
            server.shutdown()
    after = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in watched}
    assert before == after, 'Production archive data or HTML was modified by QA'
    report['checks'].append('production packaging HTML/JSON/JS hashes remained unchanged')
    native_transition_message = 'Transition was aborted because of invalid state. ViewTransition opt-in disabled'
    baseline_messages = report.get('baselineBrowserMessages', [])
    report['browserWarnings'] = [error for error in report['errors'] if error['message'] == native_transition_message and not error['stack'] and native_transition_message in baseline_messages]
    report['errors'] = [error for error in report['errors'] if error not in report['browserWarnings']]
    if report['browserWarnings']:
        report['checks'].append('native ViewTransition warning independently reproduced on existing packaging → brands navigation; no application stack')
    report['checkedAt'] = datetime.now(timezone.utc).isoformat()
    (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    assert not report['errors'], report['errors']


if __name__ == '__main__':
    run()
