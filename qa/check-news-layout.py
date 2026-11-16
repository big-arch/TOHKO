"""News layout regression: large photos, readable copy and image-free fallbacks."""
import json, os
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = json.loads((ROOT/'tights-guide/data/news.json').read_text(encoding='utf-8'))
ARTICLES = {i['id']:i for i in SNAPSHOT['items'] if i.get('sections')}
class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args): pass

server = None
base = os.environ.get('TONKO_TEST_URL')
if not base:
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(ROOT/'tights-guide')))
    Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}/'
base = base.rstrip('/')+'/'
errors = []
sizes = []
with sync_playwright() as pw:
    browser = pw.chromium.launch(channel='msedge')
    page = browser.new_page(viewport={'width':1440,'height':1000})
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto(base, wait_until='networkidle')
    # This reproduced the 240px text column and blank area in Screenshot_29.
    item = {'id':'layout-regression','title':'Статья без фотографии','source':'ТОНКО',
            'publishedAt':'2026-11-16T00:00:00Z','language':'ru','url':'https://example.org/story',
            'summary':'Текст должен занимать удобную для чтения колонку.',
            'sections':[{'heading':'О колготках','paragraphs':['Текст статьи. '*40]}]}
    page.evaluate('(item)=>TonkoReader.open(item)', item)
    copy = page.locator('.news-reader .reader-copy')
    assert copy.bounding_box()['width'] >= 700, ('narrow copy without image', copy.bounding_box())
    assert page.locator('.news-reader .reader-visual').count() == 0
    # A broken remote image must never leave an empty sidebar or broken icon.
    page.route('**/missing-photo.jpg', lambda r: r.fulfill(status=404, body='Not found'))
    item['illustration'] = {'src':'assets/missing-photo.jpg','alt':'Недоступное фото'}
    page.evaluate('(item)=>TonkoReader.open(item)', item)
    page.wait_for_function('!document.querySelector(".news-reader .reader-visual")')
    assert copy.bounding_box()['width'] >= 700
    for width in (320,390,768,1440):
        page.set_viewport_size({'width':width,'height':1000})
        for ident, editorial in ARTICLES.items():
            page.goto(base+'?news='+ident, wait_until='networkidle')
            assert page.locator('.news-reader[open]').count() == 1
            copy = page.locator('.news-reader .reader-copy')
            photo = page.locator('.news-reader .reader-visual img')
            assert photo.count() == 1, (ident, 'missing editorial image')
            page.wait_for_function('document.querySelector(".news-reader .reader-visual img").naturalWidth>0')
            assert photo.get_attribute('src') == editorial['illustration']['src']
            box = copy.bounding_box()
            assert box['width'] >= min(700,width-(120 if width>760 else 80)), (width,ident,box)
            figure = photo.locator('..').bounding_box()
            assert box['y'] >= figure['y']+figure['height']-1, (ident,'copy must follow photo')
            image_box = photo.bounding_box()
            assert image_box['width'] >= min(550,width-80), (width,ident,'small photo',image_box)
            assert page.locator('.news-reader').evaluate('(d)=>d.scrollWidth<=d.clientWidth+1')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            if width == 1440:
                assert image_box['height'] >= 350, (ident,'small photo height')
                sizes.append({'id':ident,'width':round(image_box['width']),'height':round(image_box['height'])})
            if ident == '110baf802c1c037e' and width in (390,1440):
                photo.scroll_into_view_if_needed()
                page.screenshot(path=str(ROOT/f'qa/news12-{width}.png'))
                copy.scroll_into_view_if_needed()
                page.screenshot(path=str(ROOT/f'qa/news12-copy-{width}.png'))
        # Image-free articles stay readable at every breakpoint as well.
        item.pop('illustration',None)
        page.evaluate('(item)=>TonkoReader.open(item)',item)
        assert page.locator('.news-reader .reader-copy').bounding_box()['width'] >= min(700,width-(120 if width>760 else 80))
        page.keyboard.press('Escape')
        assert page.locator('.news-reader[open]').count() == 0
    # The no-JavaScript version uses the same photo-first layout.
    nojs = browser.new_context(java_script_enabled=False,viewport={'width':1440,'height':1000})
    fallback = nojs.new_page()
    fallback.goto(base+'news.html#story-110baf802c1c037e', wait_until='networkidle')
    article = fallback.locator('#story-110baf802c1c037e')
    photo = article.locator('.reader-visual img')
    photo.scroll_into_view_if_needed()
    photo.wait_for()
    assert photo.evaluate('(i)=>i.complete&&i.naturalWidth>0')
    assert article.locator('.reader-copy').bounding_box()['width'] >= 700
    assert article.locator('.reader-copy').bounding_box()['y'] > photo.bounding_box()['y']+photo.bounding_box()['height']
    assert article.locator('h3').count() == 3
    nojs.close()
    browser.close()
if server: server.shutdown()
assert not errors, errors
print(json.dumps({'status':'PASS','articles':len(ARTICLES),'viewports':[320,390,768,1440],
                  'desktopPhotos':sizes,'javascriptErrors':errors},ensure_ascii=False))
