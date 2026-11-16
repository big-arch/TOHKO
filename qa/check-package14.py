"""Focused browser QA for exact product photographs and honest fallback cards."""
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from threading import Thread
import json, sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.cache/pw-runtime'))
from playwright.sync_api import sync_playwright

OUT=ROOT/'qa/package14'
OUT.mkdir(exist_ok=True)
DATA=json.loads((ROOT/'tights-guide/data/package-looks.json').read_text(encoding='utf-8'))
PACKS=json.loads((ROOT/'tights-guide/data/packaging.json').read_text(encoding='utf-8'))
class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self,*args): pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT/'tights-guide')))
Thread(target=server.serve_forever,daemon=True).start()
base=f'http://127.0.0.1:{server.server_port}/'
errors=[];results=[]
try:
    with sync_playwright() as pw:
        browser=pw.chromium.launch(channel='msedge')
        page=browser.new_page(viewport={'width':1440,'height':1000})
        page.on('pageerror',lambda e:errors.append(str(e)))
        # Every reviewed entry resolves to only its own photographs.
        for item in DATA['items']:
            page.goto(base+'packaging.html?pack='+item['packageIds'][0],wait_until='domcontentloaded')
            page.wait_for_selector('#pack-dialog[open]')
            actual=page.locator('#pack-looks-grid img').evaluate_all('(images)=>images.map(im=>im.getAttribute("src"))')
            assert actual==[p['thumb'] for p in item['photos']],item['id']
            assert item['model'] in page.locator('#pack-looks-title').inner_text()
            for image in page.locator('#pack-looks-grid img').all():
                image.scroll_into_view_if_needed()
                page.wait_for_function('(im)=>im.complete&&im.naturalWidth>0',arg=image.element_handle())
        wolford=next(item for item in DATA['items'] if item['brand']=='Wolford')
        for width in (320,390,768,1440):
            page.set_viewport_size({'width':width,'height':900})
            page.goto(base+'packaging.html?pack='+wolford['packageIds'][0],wait_until='networkidle')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),width
            assert page.locator('#pack-dialog').evaluate('(d)=>d.scrollWidth<=d.clientWidth+1'),width
            title=page.locator('#pack-title').inner_text()
            page.locator('#pack-looks-title').scroll_into_view_if_needed()
            page.wait_for_function('[...document.querySelectorAll("#pack-looks-grid img")].slice(0,2).every(im=>im.complete&&im.naturalWidth>0)')
            page.locator('#pack-looks-grid img').evaluate_all('(images)=>Promise.all(images.slice(0,2).map(im=>im.decode()))')
            page.screenshot(path=str(OUT/f'looks-{width}.png'))
            trigger=page.locator('#pack-looks-grid button').first
            trigger.click()
            page.wait_for_function('document.querySelector("#pack-photo-full").naturalWidth>0')
            assert page.locator('#pack-photo-dialog').evaluate('(d)=>d.scrollWidth<=d.clientWidth+1'),width
            initial=page.locator('#pack-photo-full').get_attribute('src')
            page.keyboard.press('ArrowRight')
            page.wait_for_function('document.querySelector("#pack-photo-full").complete&&document.querySelector("#pack-photo-full").naturalWidth>0')
            page.locator('#pack-photo-full').evaluate('(im)=>im.decode()')
            assert page.locator('#pack-photo-full').get_attribute('src')!=initial
            assert page.locator('#pack-title').inner_text()==title,'Photo arrows changed package'
            page.screenshot(path=str(OUT/f'photo-{width}.png'))
            page.keyboard.press('Escape')
            assert page.locator('#pack-photo-dialog[open]').count()==0
            assert page.locator('#pack-dialog[open]').count()==1
            assert page.evaluate('document.activeElement.matches("[data-look-index]")'),'Photo focus was not restored'
            page.locator('#pack-zoom').click()
            assert page.locator('#pack-image-area').evaluate('(a)=>a.classList.contains("is-zoomed")')
            page.locator('#pack-zoom').click()
            for _ in range(12):
                page.keyboard.press('Tab')
                assert page.evaluate('document.querySelector("#pack-dialog").contains(document.activeElement)'),page.evaluate('({tag:document.activeElement.tagName,id:document.activeElement.id,html:document.activeElement.outerHTML.slice(0,180)})')
            page.keyboard.press('Escape')
            assert page.locator('#pack-dialog[open]').count()==0
            results.append({'width':width,'overflow':False,'photoArrow':True,'escapeLayers':True,'focusRestored':True,'zoom':True})
        covered={pid for item in DATA['items'] for pid in item['packageIds']}
        fallback=next(p for p in PACKS if p['id'] not in covered and p['den'] is not None)
        page.goto(base+'packaging.html?pack='+fallback['id'],wait_until='networkidle')
        assert 'Проверенных дополнительных фото' in page.locator('#pack-looks-note').inner_text()
        assert 'DEN' in page.locator('#pack-facts').inner_text()
        assert page.locator('#pack-styling').inner_text()
        if page.locator('#pack-looks-grid button').count():
            assert 'другая или неустановленная модель' in page.locator('#pack-looks-grid').inner_text()
            page.locator('#pack-looks-grid button').first.click()
            assert 'не подтверждённое фото' in page.locator('#pack-photo-match').inner_text()
            page.keyboard.press('Escape')
        page.screenshot(path=str(OUT/'fallback-desktop.png'))
        page.keyboard.press('Escape')
        # Opening from the grid returns to the invoking card, also with the new controls present.
        page.goto(base+'packaging.html?brand=Wolford',wait_until='networkidle')
        page.locator('[data-pack="'+wolford['packageIds'][0]+'"]').click()
        page.locator('#pack-looks-grid button').first.focus()
        page.keyboard.press('ArrowRight')
        assert page.locator('#pack-title').inner_text()!='Individual 20 Wolford'
        assert page.evaluate('document.querySelector("#pack-dialog").contains(document.activeElement)'),'Package navigation lost focus after removing a thumbnail'
        page.keyboard.press('Escape')
        assert page.evaluate('document.activeElement.matches("[data-pack]")')
        assert not errors,errors
        browser.close()
    report={'models':len(DATA['items']),'brands':len({x['brand'] for x in DATA['items']}),'photos':sum(len(x['photos']) for x in DATA['items']),'fallbackPackages':len(PACKS)-len(covered),'viewports':results,'pageErrors':errors}
    (OUT/'browser-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))
finally:
    server.shutdown()
