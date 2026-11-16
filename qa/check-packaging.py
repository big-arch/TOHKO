"""Real-browser checks for brand grouping, filtering and the package viewer."""
from collections import Counter
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from threading import Thread
from urllib.parse import quote
import json, os
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
DATA=json.loads((ROOT/'tights-guide/data/packaging.json').read_text(encoding='utf-8'))
COUNTS=Counter(r['brand'] for r in DATA)
class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self,*args): pass
server=None
base=os.environ.get('TONKO_TEST_URL')
if not base:
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT/'tights-guide')))
    Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}/'
base=base.rstrip('/')+'/'
errors=[]
with sync_playwright() as pw:
    browser=pw.chromium.launch(channel='msedge')
    context=browser.new_context(viewport={'width':1440,'height':1100})
    page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(base+'packaging.html',wait_until='networkidle')
    assert page.evaluate('TONKO_PACKAGING.length')==len(DATA)
    assert page.locator('.pack-brand-section').count()==len(COUNTS)
    assert page.locator('.pack-card').count()==sum(min(n,4) for n in COUNTS.values())
    assert page.locator('#pack-brand-links a').count()==len(COUNTS)+1
    assert page.evaluate('''() => {
        const c=new Intl.Collator('ru',{sensitivity:'base',numeric:true});
        const brands=[...document.querySelectorAll('[data-brand-section]')].map(e=>e.dataset.brandSection);
        return brands.every((b,i)=>!i||c.compare(brands[i-1],b)<=0)&&[...document.querySelectorAll('[data-brand-section]')].every(section=>[...section.querySelectorAll('[data-pack]')].every(a=>TONKO_PACKAGING.find(r=>r.id===a.dataset.pack).brand===section.dataset.brandSection));
    }''')
    page.screenshot(path=str(ROOT/'qa/pack11-desktop.png'))
    # Expanding a section never loads another brand; keyboard focus follows new content.
    group=page.locator('[data-brand-section="Conte"]')
    group.locator('[data-more-brand]').click()
    assert group.locator('.pack-card').count()==16
    assert page.evaluate('document.activeElement.matches(".pack-open")')
    # Every brand can be reached via its own URL, with matching cards and counts.
    for brand in COUNTS:
        page.locator('#pack-brand').select_option(brand)
        assert page.locator('.pack-brand-section').count()==1
        assert page.locator('.pack-brand-heading h2').inner_text()==brand
        assert page.locator('.pack-card').count()==min(COUNTS[brand],36)
        assert page.locator('#pack-brand-links [aria-current="true"]').get_attribute('data-brand')==brand
    page.locator('#pack-brand-links [data-brand="Giulia"]').click()
    assert page.locator('#pack-brand').input_value()=='Giulia'
    page.reload(wait_until='networkidle')
    assert page.locator('#pack-brand').input_value()=='Giulia'
    page.locator('#pack-search').fill('Smart Box')
    assert page.locator('.pack-card').count()==6
    page.locator('#pack-den').select_option('thin')
    assert page.locator('.pack-card').count()==3
    first=page.locator('.pack-open').first
    first.click();assert page.locator('#pack-dialog[open]').count()==1
    page.wait_for_function('document.querySelector("#pack-full").naturalWidth>0')
    width=page.locator('#pack-full').bounding_box()['width']
    page.locator('#pack-zoom').click()
    assert page.locator('#pack-full').bounding_box()['width']>=width*1.9
    title=page.locator('#pack-title').inner_text();page.keyboard.press('ArrowRight')
    assert page.locator('#pack-title').inner_text()!=title
    page.keyboard.press('Escape')
    assert page.evaluate('document.activeElement.matches(".pack-open")')
    page.locator('#pack-reset').click()
    page.locator('#pack-search').fill('НетТакойМодели')
    assert page.locator('.pack-card').count()==0
    assert 'Ничего не найдено' in page.locator('#pack-count').inner_text()
    # Deep links also work for rows beyond the preview and with stale filters.
    target=next(r for r in DATA if r['brand']=='Giulia' and 'Tracery' in r['title'])
    page.goto(base+'packaging.html?brand=Conte&q=no-match&pack='+target['id'],wait_until='networkidle')
    assert page.locator('#pack-dialog[open]').count()==1
    assert page.locator('#pack-title').inner_text()==target['title']
    assert page.locator('#pack-brand').input_value()=='Giulia'
    page.keyboard.press('Escape')
    for width in [320,390,768,1440]:
        page.set_viewport_size({'width':width,'height':900})
        page.goto(base+'packaging.html?brand=Giulia',wait_until='networkidle')
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),width
        for im in page.locator('.pack-card img').all():
            im.scroll_into_view_if_needed()
            page.wait_for_function('(img)=>img.complete&&img.naturalWidth>0',arg=im.element_handle())
        if width==390:
            page.locator('#package-archive').evaluate('(el)=>el.scrollIntoView({block:"start"})')
            page.screenshot(path=str(ROOT/'qa/pack11-mobile.png'))
        page.locator('.pack-open').first.click()
        assert page.locator('#pack-dialog').evaluate('(d)=>d.scrollWidth<=d.clientWidth+1')
        page.keyboard.press('Escape')
    nojs=browser.new_context(java_script_enabled=False)
    fallback=nojs.new_page();fallback.goto(base+'packaging.html',wait_until='domcontentloaded')
    assert fallback.locator('.pack-card').count()==len(DATA)
    assert fallback.locator('.pack-brand-section').count()==len(COUNTS)
    assert not fallback.locator('.pack-tools').is_visible()
    assert not errors,errors
    browser.close()
if server:server.shutdown()
print(json.dumps({'status':'PASS','images':len(DATA),'brands':len(COUNTS),'viewports':[320,390,768,1440],'javascriptErrors':errors},ensure_ascii=False))
