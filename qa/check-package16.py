"""Browser regression: each package opens its own brand story, never gallery filler."""
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from threading import Thread
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
for runtime in (ROOT / '.cache/pw-runtime', Path('C:/Users/Артур/Documents/CODEX_сайт_ТОНКО/.cache/pw-runtime')):
    if runtime.is_dir():
        sys.path.insert(0, str(runtime))
        break
from playwright.sync_api import sync_playwright, expect

OUT = ROOT / '.cache/package16-ui'
OUT.mkdir(parents=True, exist_ok=True)
PACKS = json.loads((ROOT / 'tights-guide/data/packaging.json').read_text('utf-8'))
STORIES = json.loads((ROOT / 'tights-guide/data/brand-stories.json').read_text('utf-8'))['items']
LOOKS = json.loads((ROOT / 'tights-guide/data/package-looks.json').read_text('utf-8'))['items']
covered = {pid for item in LOOKS for pid in item['packageIds']}

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def copyfile(self, source, outputfile):
        try:
            super().copyfile(source, outputfile)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            pass  # A completed check navigates away while unrelated lazy images load.

server = None
base = os.environ.get('TONKO_TEST_URL')
if not base:
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(ROOT / 'tights-guide')))
    Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}/'
base = base.rstrip('/') + '/'
errors, requests, failed_requests, checked_brands = [], [], [], []
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='chrome', headless=True)
        context = browser.new_context(viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce')
        def route(request):
            address = request.request.url
            requests.append(address)
            request.continue_() if address.startswith(base) else request.abort()
        context.route('**/*', route)
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('requestfailed', lambda request: failed_requests.append({'url': request.url, 'error': request.failure}))
        for story in STORIES:
            package = next((row for row in PACKS if row['brand'] == story['brand']), None)
            if not package:
                continue
            page.goto(base + 'packaging.html?pack=' + package['id'], wait_until='domcontentloaded')
            expect(page.locator('#pack-dialog')).to_be_visible()
            section = page.locator('#pack-brand-story')
            expect(section).to_be_visible()
            expect(section).to_have_attribute('data-brand', package['brand'])
            expect(page.locator('#pack-brand-story-title')).to_have_text('История ' + story['brand'])
            assert page.locator('#pack-brand-story-text p').all_text_contents() == story['paragraphs'], story['brand']
            if story['photo']:
                assert page.locator('#pack-brand-photo').get_attribute('src') == story['photo']['src']
                page.locator('#pack-brand-photo').evaluate('(image)=>image.decode()')
            else:
                expect(page.locator('.pack-brand-figure')).to_be_hidden()
                assert page.locator('#pack-brand-photo').get_attribute('src') is None
            assert page.locator('#pack-brand-story-sources a').count() == len(story['sources'])
            if package['id'] not in covered:
                expect(page.locator('.pack-looks')).to_be_hidden()
                assert not page.locator('#pack-looks-grid img').count()
            checked_brands.append(story['brand'])
        assert set(checked_brands) == {row['brand'] for row in PACKS}

        # New brands retain their own catalogue and explicit product-type counts.
        for brand in ('Knittex', 'Marilyn', 'Mona', 'Veneziana'):
            group = [row for row in PACKS if row['brand'] == brand]
            page.goto(base + 'packaging.html?brand=' + brand, wait_until='networkidle')
            expect(page.locator('[data-brand-section]')).to_have_count(1)
            expect(page.locator('[data-brand-section]')).to_have_attribute('data-brand-section', brand)
            expect(page.locator('#pack-count')).to_contain_text('Найдено ' + str(len(group)))
            if any(row.get('productKind', 'колготки') != 'колготки' for row in group):
                for kind in ('колготки', 'чулки', 'гольфы', 'легинсы'):
                    count = sum(row.get('productKind', 'колготки') == kind for row in group)
                    if count:
                        expect(page.locator('.pack-kind-note')).to_contain_text(kind + ' — ' + str(count))
        stocking = next(row for row in PACKS if row.get('productKind') == 'чулки')
        page.goto(base + 'packaging.html?pack=' + stocking['id'], wait_until='networkidle')
        expect(page.locator('#pack-facts dd').first).to_have_text('чулки')

        # Existing exact model photographs remain attached to their own package IDs.
        for item in LOOKS:
            page.goto(base + 'packaging.html?pack=' + item['packageIds'][0], wait_until='domcontentloaded')
            try:
                expect(page.locator('.pack-looks')).to_be_visible()
            except AssertionError:
                raise AssertionError({'model': item['model'], 'package': item['packageIds'][0], 'errors': errors, 'failedScripts': [r for r in failed_requests if '.js' in r['url']][-10:], 'dialog': page.locator('#pack-dialog').get_attribute('open'), 'looks': page.locator('.pack-looks').get_attribute('hidden'), 'current': page.locator('#pack-title').text_content(), 'globals': page.evaluate('({rows:window.TONKO_PACKAGING?.length,looks:window.TONKO_PACKAGE_LOOKS?.items.length,stories:window.TONKO_BRAND_STORIES?.items.length,url:location.href,toolsHidden:document.querySelector(".pack-tools").hidden})')}) from None
            assert page.locator('#pack-looks-grid img').evaluate_all('images=>images.map(image=>image.getAttribute("src"))') == [photo['thumb'] for photo in item['photos']]

        wolford = next(row for row in PACKS if row['brand'] == 'Wolford' and row['id'] not in covered)
        viewports = []
        for width in (320, 390, 768, 1440):
            page.set_viewport_size({'width': width, 'height': 1000})
            page.goto(base + 'packaging.html?pack=' + wolford['id'], wait_until='networkidle')
            page.locator('#pack-brand-story-title').scroll_into_view_if_needed()
            page.locator('#pack-brand-photo').evaluate('(image)=>image.decode()')
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            assert page.locator('#pack-dialog').evaluate('dialog=>dialog.scrollWidth <= dialog.clientWidth + 1')
            page.screenshot(path=str(OUT / f'brand-story-{width}.png'))
            page.locator('#pack-brand-photo-open').click()
            expect(page.locator('#pack-photo-dialog')).to_be_visible()
            expect(page.locator('#pack-photo-match')).to_contain_text('Фотография бренда')
            expect(page.locator('.pack-photo-navigation')).to_be_hidden()
            page.locator('#pack-photo-full').evaluate('(image)=>image.decode()')
            page.keyboard.press('ArrowRight')
            assert page.locator('#pack-title').inner_text() == wolford['title']
            page.keyboard.press('Escape')
            expect(page.locator('#pack-photo-dialog')).to_be_hidden()
            expect(page.locator('#pack-dialog')).to_be_visible()
            assert page.evaluate('document.activeElement.id === "pack-brand-photo-open"')
            for _ in range(12):
                page.keyboard.press('Tab')
                assert page.evaluate('document.querySelector("#pack-dialog").contains(document.activeElement)'), {'width': width, 'tab': _, 'active': page.evaluate('document.activeElement.outerHTML.slice(0,300)'), 'controls': page.locator('#pack-dialog').evaluate('modal=>[...modal.querySelectorAll("button:not([disabled]),a[href],summary")].map(e=>({id:e.id,tag:e.tagName,rects:e.getClientRects().length,visibility:e.checkVisibility(),details:e.closest("details")?.open}))')}
            viewports.append({'width': width, 'overflow': False, 'brandPhotoZoom': True, 'focusRestored': True})

        # On the unfiltered archive, previous/next can cross a brand boundary.
        page.goto(base + 'packaging.html', wait_until='networkidle')
        page.locator('[data-pack]').first.click()
        first_brand = page.locator('#pack-brand-story').get_attribute('data-brand')
        first_image = page.locator('#pack-brand-photo').get_attribute('src')
        page.locator('#pack-previous').click()
        assert page.locator('#pack-brand-story').get_attribute('data-brand') != first_brand
        assert page.locator('#pack-brand-photo').get_attribute('src') != first_image
        page.keyboard.press('Escape')
        assert page.evaluate('document.activeElement.matches("[data-pack]")')

        # Switching from a one-photo brand viewer back to a model gallery restores arrows.
        exact = next(item for item in LOOKS if len(item['photos']) > 1)
        page.goto(base + 'packaging.html?pack=' + exact['packageIds'][0], wait_until='networkidle')
        page.locator('#pack-brand-photo-open').click()
        page.keyboard.press('Escape')
        page.locator('#pack-looks-grid button').first.click()
        expect(page.locator('.pack-photo-navigation')).to_be_visible()
        original_photo = page.locator('#pack-photo-full').get_attribute('src')
        page.keyboard.press('ArrowRight')
        assert page.locator('#pack-photo-full').get_attribute('src') != original_photo
        expect(page.locator('#pack-photo-match')).to_have_text('Фотография конкретной модели')
        assert not any('data/style-photos.json' in address for address in requests)
        assert not errors, errors
        browser.close()
    report = {'brands': checked_brands, 'exactModels': len(LOOKS), 'packageCount': len(PACKS), 'unrelatedGalleryRequests': 0, 'viewports': viewports, 'javascriptErrors': errors, 'url': base}
    (OUT / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
finally:
    if server:
        server.shutdown()
