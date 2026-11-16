"""Real-browser publication gate, complete archive and winter-photo smoke test."""
import copy,json
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'qa/news13report';OUT.mkdir(exist_ok=True)
news=json.loads((ROOT/'tights-guide/data/news.json').read_text(encoding='utf-8'))
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(ROOT/'tights-guide')))
Thread(target=server.serve_forever,daemon=True).start()
base=f'http://127.0.0.1:{server.server_port}/'
errors=[];results=[]
with sync_playwright() as pw:
    browser=pw.chromium.launch(channel='msedge')
    page=browser.new_page(viewport={'width':1440,'height':1000})
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(base,wait_until='domcontentloaded')
    assert page.locator('[data-news-id]').count()==6
    while page.locator('#news-more').is_visible():page.locator('#news-more').click()
    assert page.locator('[data-news-id]').count()==len(news['items'])
    assert 'Короткая новость' not in page.locator('#news-list').inner_text()
    # Every existing deep link has a substantive body, not just a headline.
    for item in news['items']:
        page.evaluate('(i)=>TonkoReader.open(i)',item)
        assert page.locator('.news-reader[open] .reader-copy section').count()==len(item['sections'])
        assert len(page.locator('.news-reader .reader-copy').inner_text())>300,item['id']
        assert page.locator('.news-reader .reader-source').first.get_attribute('href')==(item.get('publisherUrl') or item['url'])
        assert item.get('illustration'),item['id']
        photo=page.locator('.news-reader .reader-visual img')
        photo.scroll_into_view_if_needed()
        page.wait_for_function('document.querySelector(".news-reader .reader-visual img").naturalWidth>0')
        assert photo.get_attribute('src').startswith('assets/news/'),item['id']
        assert len(page.locator('.news-reader figcaption').inner_text())>40,item['id']
    for width in (390,1440):
        page.set_viewport_size({'width':width,'height':1000})
        for ident in ('ee8ae4a2a6c7f547','d97ca36124a1dd82'):
            page.goto(base+'?news='+ident,wait_until='domcontentloaded')
            page.locator('.news-reader[open]').wait_for()
            assert page.locator('.news-reader').evaluate('(d)=>d.scrollWidth<=d.clientWidth+1')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            if ident=='ee8ae4a2a6c7f547':
                photo=page.locator('.news-reader .reader-visual img')
                page.wait_for_function('document.querySelector(".news-reader .reader-visual img").naturalWidth>0')
                assert photo.get_attribute('src')=='assets/news/winter-leggings-coat-boots.webp'
                assert 'мороза' in page.locator('.news-reader figcaption').inner_text()
                photo.scroll_into_view_if_needed()
            else:
                assert '800 тысяч' in page.locator('.news-reader .reader-copy').inner_text()
                assert page.locator('.news-reader a[href*="acs.org"]').count()==1
                page.locator('.news-reader .reader-copy').scroll_into_view_if_needed()
            page.screenshot(path=str(OUT/f'{ident}-{width}.png'))
    page.keyboard.press('Escape')
    # Discovery + failure fixtures must stay in the queue with no Read action.
    fixture=copy.deepcopy(news)
    for ident,state in (('pending-fixture','pending'),('failed-fixture','failed')):
        fixture['items'].insert(0,{'id':ident,'title':'Заголовок без готового материала '+ident,
            'url':'https://bracatus.com/unavailable','sourceId':'bracatus','source':'Bracatus','language':'ru',
            'publishedAt':'2026-11-16T00:00:00Z','publication':{'status':state,'reason':'source_unavailable' if state=='failed' else 'awaiting_source','nextAttemptAt':'2026-11-17T00:00:00Z'}})
    page.route('**/data/news.json?*',lambda route:route.fulfill(status=200,content_type='application/json',body=json.dumps(fixture)))
    page.locator('#news-refresh').click()
    page.wait_for_function('document.querySelector("#news-queue").textContent.includes("Требуют повторной проверки: 1")')
    assert page.locator('[data-news-id="pending-fixture"],[data-news-id="failed-fixture"]').count()==0
    page.locator('.news-about summary').click()
    assert 'повторная попытка' in page.locator('#news-queue').inner_text()
    nojs=browser.new_context(java_script_enabled=False,viewport={'width':1440,'height':1000})
    fallback=nojs.new_page();fallback.goto(base+'news.html#story-d97ca36124a1dd82',wait_until='domcontentloaded')
    assert fallback.locator('article.news-fallback').count()==len(news['items'])
    assert fallback.locator('article.news-fallback .reader-visual img').count()==len(news['items'])
    assert '800 тысяч' in fallback.locator('#story-d97ca36124a1dd82').inner_text()
    assert 'заголовок' not in fallback.locator('#story-d97ca36124a1dd82 .reader-excerpt').inner_text().lower()
    browser.close()
server.shutdown()
assert not errors,errors
report={'status':'PASS','articles':len(news['items']),'allDeepLinksHaveBody':True,'pendingFailedNotPublished':True,
        'imagesLoaded':len(news['items']),'allImagesLocal':True,'winterPhotoVerified':True,'noJavaScriptArchive':True,'viewports':[390,1440],'javascriptErrors':errors}
(OUT/'browser-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
